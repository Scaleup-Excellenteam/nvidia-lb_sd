"""Reverse-proxy utilities for the Load Balancer.

Provides a streaming forwarder that proxies client requests to a selected
backend and streams the upstream response back to the client.
"""
from __future__ import annotations
from typing import Dict, Mapping
import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

# RFC 9110 hop-by-hop headers (must not be forwarded)
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}

def _strip_hop_headers(headers: Mapping[str, str]) -> Dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}

def _add_forwarded(req: Request, headers: Dict[str, str]) -> Dict[str, str]:
    client_ip = req.client.host if req.client else "unknown"
    prior = headers.get("x-forwarded-for")
    headers["x-forwarded-for"] = f"{prior}, {client_ip}" if prior else client_ip
    headers.setdefault("x-forwarded-proto", req.url.scheme)
    headers.setdefault("x-forwarded-host", req.headers.get("host", ""))
    if "x-forwarded-port" not in headers:
        port = req.url.port or (443 if req.url.scheme == "https" else 80)
        headers["x-forwarded-port"] = str(port)
    return headers

async def forward(req: Request, upstream_base: str, subpath: str, *, timeout_s: float = 30.0) -> Response:
    """Forward `req` to `{upstream_base}/{subpath}` and stream the response back."""
    base = upstream_base[:-1] if upstream_base.endswith("/") else upstream_base
    path = subpath if subpath.startswith("/") else f"/{subpath}"
    target_url = f"{base}{path}"

    headers = _strip_hop_headers(dict(req.headers))
    headers = _add_forwarded(req, headers)
    body = await req.body()

    client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_s), follow_redirects=False)
    upstream_request = client.build_request(
        req.method, target_url, params=req.query_params, headers=headers, content=body
    )
    upstream_response = await client.send(upstream_request, stream=True)

    resp_headers = _strip_hop_headers(dict(upstream_response.headers))

    async def iter_upstream():
        try:
            async for chunk in upstream_response.aiter_bytes():
                yield chunk
        finally:
            await upstream_response.aclose()
            await client.aclose()

    return StreamingResponse(iter_upstream(), status_code=upstream_response.status_code, headers=resp_headers)
