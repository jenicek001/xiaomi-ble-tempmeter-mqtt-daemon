# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for Xiaomi Mijia Bluetooth Daemon
# Optimized for ARM64 (Raspberry Pi 5) and AMD64 architectures
# Based on Docker best practices for Python applications

# === Stage 1: Builder Stage ===
# Use specific Python version with slim variant for smaller image
FROM python:3.11-slim-bookworm AS builder

# Set build-time environment variables
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Install build dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Install Python dependencies with caching
# Using bind mount for requirements.txt (best practice)
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# === Stage 2: Runtime Stage ===
FROM python:3.11-slim-bookworm AS final

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    MIJIA_LOG_LEVEL=INFO \
    MIJIA_MQTT_BROKER_HOST=localhost \
    MIJIA_MQTT_BROKER_PORT=1883 \
    MIJIA_BLUETOOTH_ADAPTER=0

# Install runtime dependencies for Bluetooth in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    libglib2.0-0 \
    dbus \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user with specific UID for consistency
# Note: User will run as root in container due to Bluetooth hardware requirements
# The privileged mode and host network make this necessary
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    mijia \
    && mkdir -p /app /config \
    && chown -R mijia:mijia /app /config

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=mijia:mijia src/ /app/src/
COPY --chown=mijia:mijia config/config.yaml.example /config/config.yaml.example

# Ensure __init__.py exists
RUN touch /app/src/__init__.py && chown mijia:mijia /app/src/__init__.py

# Switch to non-root user
# Note: In production with host network + privileged, container may override this
USER mijia

# Health check that actually verifies the daemon is running
# Uses pgrep to check if the main process exists
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python.*src.main" > /dev/null || exit 1

# Expose port for optional health check endpoint
EXPOSE 8082

# Use exec form for CMD to avoid shell and properly handle signals
# Cannot use shell variable substitution in exec form, so hardcoded
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--config", "/config/config.yaml", "--log-level", "INFO"]
