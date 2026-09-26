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

# Install Python dependencies, then drop the packaging tools: the app does not need them at runtime,
# and the base image's bundled copies carry known CVEs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn && \
    pip uninstall -y pip setuptools wheel

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
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:%s/sources' % os.environ['PORT'], timeout=4)"]

EXPOSE 5001

# Run with Gunicorn WSGI server
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5001", "--workers", "4", "--threads", "2", "--timeout", "120"]
