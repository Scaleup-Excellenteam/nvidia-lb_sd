# tests/test_lb_connectivity.py
import os
import sys
import time
import socket
import threading
import importlib.util
from contextlib import closing

import anyio
import pytest
import httpx
import uvicorn
from fastapi import FastAPI

# --- helpers ---------------------------------------------------------------

def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

class _BgServer:
    """Run a uvicorn server in a background thread; stop with should_exit=True."""
    def __init__(self, app, host: str, port: int):
        self.config = uvicorn.Config(app, host=host, port=port, log_level="error")
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self):
        self.thread.start()
        # Wait until port is accepting connections
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with socket.create_connection((self.config.host, self.config.port), timeout=0.25):
                    return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("Server failed to start")

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=3)

def _load_app_module(alias: str, path: str):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None:
        raise ImportError(f"Could not load spec for module {alias} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod

# --- mock service-provider (the real “backend”) ---------------------------

def _make_provider_app() -> FastAPI:
    app = FastAPI()
    @app.get("/health")
    async def health():
        return {"status": "OK"}
    @app.get("/echo")
    async def echo(x: str = ""):
        return {"echo": x, "provider": "mock"}
    return app

# --- tests ----------------------------------------------------------------

@pytest.mark.anyio
async def test_load_balancer_proxies_to_provider(tmp_path):
    repo_root = tmp_path.parent.parent if (tmp_path.parent / "load-balancer").exists() else None
    # If running from repo root: adjust to actual paths
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    lb_path = os.path.join(root, "load-balancer", "app", "main.py")
    sd_path = os.path.join(root, "service-discovery", "app", "main.py")

    assert os.path.exists(lb_path), f"not found: {lb_path}"
    assert os.path.exists(sd_path), f"not found: {sd_path}"

    # 1) Start Service-Discovery on a free port
    sd_port = _free_port()
    sd_mod = _load_app_module("sd_app_main", sd_path)
    sd_server = _BgServer(sd_mod.app, "127.0.0.1", sd_port)
    sd_server.start()

    try:
        # 2) Start a mock provider (backend) on a free port
        backend_port = _free_port()
        provider_app = _make_provider_app()
        provider_server = _BgServer(provider_app, "127.0.0.1", backend_port)
        provider_server.start()

        try:
            # 3) Register the provider in Service-Discovery under image_id "test-app"
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "provider-1",
                    "image_id": "test-app",
                    "host": "127.0.0.1",
                    "port": backend_port,
                    "status": "UP"
                }
                r = await client.post(f"http://127.0.0.1:{sd_port}/registry/endpoints", json=payload)
                r.raise_for_status()

            # 4) Point LB settings at our SD instance BEFORE importing LB
            os.environ["SERVICE_DISCOVERY_URL"] = f"http://127.0.0.1:{sd_port}"

            # 5) Load the LB FastAPI app and call it via ASGI transport
            lb_mod = _load_app_module("lb_app_main", lb_path)
            lb_app = lb_mod.app

            transport = httpx.ASGITransport(app=lb_app, root_path="")
            async with httpx.AsyncClient(transport=transport, base_url="http://lb.local") as client:
                # Call LB -> SD -> provider: /registry/{image_id}/echo?x=42
                resp = await client.get("/registry/test-app/echo", params={"x": "42"})
                assert resp.status_code == 200
                assert resp.headers.get("content-type", "").startswith("application/json")
                data = resp.json()
                assert data == {"echo": "42", "provider": "mock"}

            # 6) Negative case: mark provider DOWN => LB should return 503
            async with httpx.AsyncClient() as client:
                await client.put(f"http://127.0.0.1:{sd_port}/registry/endpoints/provider-1/status",
                                 params={"status": "DOWN"})
            async with httpx.AsyncClient(transport=transport, base_url="http://lb.local") as client:
                resp2 = await client.get("/registry/test-app/echo", params={"x": "nope"})
                assert resp2.status_code == 503

        finally:
            provider_server.stop()
    finally:
        sd_server.stop()
