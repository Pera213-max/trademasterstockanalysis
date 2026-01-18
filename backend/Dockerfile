# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder to home directory
COPY --from=builder /root/.local /home/appuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Create non-root user FIRST
RUN useradd -m -u 1000 appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Fix permissions for .local
RUN chown -R appuser:appuser /home/appuser/.local

# Create writable cache dir for yfinance
RUN mkdir -p /home/appuser/.cache/py-yfinance && \
    chown -R appuser:appuser /home/appuser/.cache

# Ensure entrypoint is executable
RUN chmod +x /app/docker-entrypoint.sh

# yfinance cache location (use /tmp to avoid permission issues)
ENV XDG_CACHE_HOME=/tmp
ENV YFINANCE_CACHE_DIR=/tmp/py-yfinance

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with Gunicorn (production-ready)
# Note: FastAPI app is in main.py (not app/main.py)
# Use socket_app to enable Socket.IO over ASGI.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "python -m gunicorn main:socket_app --workers ${WEB_CONCURRENCY:-4} --worker-class uvicorn.workers.UvicornWorker --timeout ${GUNICORN_TIMEOUT:-7200} --keep-alive ${GUNICORN_KEEPALIVE:-5} --max-requests ${GUNICORN_MAX_REQUESTS:-1000} --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-200} --bind 0.0.0.0:8000"]
