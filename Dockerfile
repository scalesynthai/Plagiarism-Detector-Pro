# ==============================================================================
# Plagiarism Detector Pro - Production Dockerfile
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source code
COPY . .

# Ensure storage directories exist and have proper permissions, and keep seed sources for volume initialization
RUN cp -r /app/sources /app/default_sources && \
    mkdir -p /app/sources && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/sources || exit 1

EXPOSE 5001

# Run with Gunicorn WSGI server
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5001", "--workers", "4", "--threads", "2", "--timeout", "120"]
