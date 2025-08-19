# Load Balancer image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
# If you already have a requirements.txt for LB, keep this path as-is
COPY load-balancer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only the LB service code
COPY load-balancer /app

EXPOSE 6000
# SERVICE_DISCOVERY_URL is provided by Compose at runtime
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
