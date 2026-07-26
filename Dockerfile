# Dockerfile for IT Risk Manager Agent
# Multi-stage build for smaller final image

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories with correct permissions
RUN mkdir -p /app/data/raw/eba /app/data/raw/mas /app/data/processed /app/logs && \
    chown -R appuser:appuser /app/data /app/logs

# Set environment variables (each on separate line to avoid syntax errors)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV OLLAMA_HOST=http://ollama:11434
ENV OLLAMA_MODEL=mistral
ENV LOG_LEVEL=INFO
ENV LOG_ROTATION="1 day"
ENV LOG_RETENTION="7 days"
ENV DEFAULT_DELAY=1.0
ENV DATA_DIR=/app/data
ENV RAW_DATA_DIR=/app/data/raw
ENV PROCESSED_DIR=/app/data/processed
ENV LOGS_DIR=/app/logs
ENV DB_PATH=/app/data/processed/regulatory_updates.db

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; conn = sqlite3.connect('data/processed/regulatory_updates.db'); conn.close()" || exit 1

# Default command (Streamlit)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
