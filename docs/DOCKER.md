# Docker Deployment Guide

This guide explains how to run the Xiaomi Mijia Bluetooth Daemon in a Docker container, following Docker and Docker Compose best practices.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Building the Image](#building-the-image)
- [Running with Docker Compose](#running-with-docker-compose)
- [Running with Docker CLI](#running-with-docker-cli)
- [Configuration](#configuration)
- [Bluetooth Access](#bluetooth-access)
- [Troubleshooting](#troubleshooting)
- [Multi-Architecture Support](#multi-architecture-support)
- [Best Practices](#best-practices)

## Prerequisites

### Required
- Docker Engine 20.10 or later
- Docker Compose 2.0 or later (optional, but recommended)
- Bluetooth adapter (built-in or USB)
- Linux host with Bluetooth support (BlueZ)
- `.env` file with your MQTT credentials (see `.env.example`)

### Recommended
- Raspberry Pi 3/4/5 or similar ARM64 device
- Or AMD64 Linux system with Bluetooth

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon.git
cd xiaomi-ble-tempmeter-mqtt-daemon
```

### 2. Prepare Configuration
```bash
# Copy example config
cp config/config.yaml.example config/config.yaml
cp .env.example .env

# Edit with your settings
nano config/config.yaml
nano .env  # IMPORTANT: Add your MQTT credentials here!
```

**Critical:** Update at minimum:
- `.env` - MQTT broker credentials (NEVER commit this file!)
- `config.yaml` - Device MAC addresses and friendly names

### 3. Run with Docker Compose
```bash
# Using the main docker-compose.yml (host network mode by default)
docker compose up -d
```

**Note:** Ensure your MQTT broker (Mosquitto, Home Assistant, etc.) is already running and accessible from the Raspberry Pi. Configure the broker address and credentials in your `.env` file.

### 4. Check Logs
```bash
docker compose logs -f mijia-daemon
```

## Building the Image

### Build for Current Architecture
```bash
docker build -t mijia-bluetooth-daemon:latest .
```

### Build for Specific Architecture
```bash
# For ARM64 (Raspberry Pi)
docker buildx build --platform linux/arm64 -t mijia-bluetooth-daemon:arm64 .

# For AMD64
docker buildx build --platform linux/amd64 -t mijia-bluetooth-daemon:amd64 .

# Multi-arch build
docker buildx build --platform linux/amd64,linux/arm64 -t mijia-bluetooth-daemon:latest .
```

## Running with Docker Compose

### Option 1: Host Network Mode (Recommended)

## Running with Docker Compose

### Default Configuration (Recommended)

The main `docker-compose.yml` uses **host network mode** by default for optimal Bluetooth compatibility on Linux.

```bash
# Start the daemon
docker compose up -d
```

**Prerequisites:**
- ✅ Existing MQTT broker running (Mosquitto, Home Assistant, etc.)
- ✅ `.env` file configured with your MQTT broker address and credentials
- ✅ Bluetooth adapter available on the host

**Key Features:**
- ✅ Host network mode (no `privileged` needed!)
- ✅ Credentials from `.env` file (never hardcoded)
- ✅ Modern Compose format (no `version` field)

### Legacy Configuration

For backward compatibility, `docker-compose.host-network.yml` is available but essentially identical to the main file.

```bash
docker compose -f docker-compose.host-network.yml up -d
```

### Managing the Container

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs (follow mode)
docker compose logs -f mijia-daemon

# Restart
docker compose restart mijia-daemon

# Update and restart
docker compose pull
docker compose up -d

# Remove volumes too
docker compose down -v
```

## Running with Docker CLI

### Recommended: Using .env File

```bash
docker run -d \
  --name mijia-daemon \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/config/config.yaml:/config/config.yaml:ro \
  -v /var/run/dbus:/var/run/dbus:ro \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  mijia-bluetooth-daemon:latest
```

**Note:** With `--network host`, `--privileged` is NOT required!

### Without .env File (Not Recommended)

```bash
docker run -d \
  --name mijia-daemon \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/config/config.yaml:/config/config.yaml:ro \
  -v /var/run/dbus:/var/run/dbus:ro \
  -e MIJIA_LOG_LEVEL=INFO \
  -e MIJIA_MQTT_BROKER_HOST=your-mqtt-host \
  -e MIJIA_MQTT_BROKER_PORT=1883 \
  -e MIJIA_MQTT_USERNAME=your-username \
  -e MIJIA_MQTT_PASSWORD=your-password \
  -e MIJIA_BLUETOOTH_ADAPTER=0 \
  mijia-bluetooth-daemon:latest
```

⚠️ **Security Warning:** Never hardcode credentials in scripts! Use `.env` file or environment variables from secure storage.

### Managing with Docker CLI

```bash
# View logs (follow mode)
docker logs -f mijia-daemon

# Stop
docker stop mijia-daemon

# Start
docker start mijia-daemon

# Restart
docker restart mijia-daemon

# Remove
docker rm -f mijia-daemon

# Execute shell inside container
docker exec -it mijia-daemon /bin/bash

# Check health status
docker inspect --format='{{.State.Health.Status}}' mijia-daemon
```

## Configuration

### Configuration Priority (highest to lowest)
1. Environment variables (most flexible for Docker)
2. Config file (`config/config.yaml`)
3. Default values in code

### Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MIJIA_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MIJIA_MQTT_BROKER_HOST` | `localhost` | MQTT broker hostname/IP |
| `MIJIA_MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MIJIA_MQTT_USERNAME` | - | MQTT username (optional) |
| `MIJIA_MQTT_PASSWORD` | - | MQTT password (optional) |
| `MIJIA_MQTT_CLIENT_ID` | `mijiableht-daemon` | MQTT client identifier |
| `MIJIA_MQTT_PUBLISH_INTERVAL` | `300` | Periodic publish interval (seconds) |
| `MIJIA_BLUETOOTH_ADAPTER` | `0` | Bluetooth adapter number |
| `MIJIA_TEMPERATURE_THRESHOLD` | `0.2` | Temperature change threshold (°C) |
| `MIJIA_HUMIDITY_THRESHOLD` | `1.0` | Humidity change threshold (%) |
| `MIJIA_DEVICES_AUTO_DISCOVERY` | `true` | Enable automatic device discovery |

### Using .env File

```bash
# Copy example
cp .env.example .env

# Edit your values
nano .env

# Run with env file
docker-compose --env-file .env up -d
```

### Config File vs Environment Variables

- **Config file**: Better for device-specific settings (MAC addresses, friendly names)
- **Environment variables**: Better for deployment-specific settings (MQTT credentials, log level)
- Both can be used together - environment variables override config file

## Bluetooth Access

### Requirements

The container needs access to the host's Bluetooth stack. This requires:

1. **Privileged mode**: `--privileged` or `privileged: true`
2. **Host network**: `--network host` (recommended)
3. **D-Bus access**: `-v /var/run/dbus:/var/run/dbus:ro`

### Why Privileged Mode?

Bluetooth Low Energy (BLE) scanning requires:
- Access to `/dev/bus/usb` (for USB Bluetooth adapters)
- CAP_NET_RAW and CAP_NET_ADMIN capabilities
- Direct hardware access

### Security Considerations

- Privileged containers have elevated permissions
- Use only on trusted networks
- Consider running on dedicated IoT VLAN
- Keep Docker and host system updated

### Alternative: Specific Capabilities (More Secure)

Instead of `--privileged`, you can use specific capabilities:

```bash
docker run -d \
  --name mijia-daemon \
  --network host \
  --cap-add=NET_RAW \
  --cap-add=NET_ADMIN \
  --cap-add=SYS_ADMIN \
  -v /var/run/dbus:/var/run/dbus:ro \
  -v /dev/bus/usb:/dev/bus/usb \
  mijia-bluetooth-daemon:latest
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs mijia-daemon

# Common issues:
# 1. Bluetooth not available
# 2. D-Bus socket not accessible
# 3. Config file missing or invalid
```

### No Devices Discovered

```bash
# Verify Bluetooth is working on host
hciconfig
sudo hcitool lescan

# Check container has Bluetooth access
docker exec mijia-daemon hciconfig

# Check logs for discovery
docker logs -f mijia-daemon | grep -i discover
```

### MQTT Connection Failed

```bash
# Test MQTT from host
mosquitto_pub -h localhost -t test -m "hello"

# Check network mode
docker inspect mijia-daemon | grep -i network

# Verify MQTT credentials in logs
docker logs mijia-daemon | grep -i mqtt
```

### Permission Denied Errors

```bash
# Check D-Bus permissions
ls -l /var/run/dbus/

# Ensure privileged mode
docker inspect mijia-daemon | grep -i privileged

# Check user in container
docker exec mijia-daemon id
```

### High CPU Usage

```bash
# Check for continuous scanning issues
docker stats mijia-daemon

# Review logs for errors
docker logs mijia-daemon | grep -i error

# Consider increasing scan timeout in config
```

### Container Keeps Restarting

```bash
# Check exit code and logs
docker ps -a
docker logs mijia-daemon

# Common causes:
# 1. Config validation error
# 2. MQTT broker unreachable
# 3. Bluetooth adapter not found
```

## Multi-Architecture Support

### Build for Multiple Architectures

```bash
# Setup buildx (one-time)
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Build and push multi-arch image
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  --tag yourusername/mijia-daemon:latest \
  --push \
  .
```

### Supported Architectures
- **linux/amd64**: x86_64 systems
- **linux/arm64**: Raspberry Pi 3/4/5 (64-bit)
- **linux/arm/v7**: Raspberry Pi 2/3 (32-bit)

## Health Checks

The container includes a built-in health check:

```bash
# Check health status
docker ps
# Look for "healthy" or "unhealthy" in STATUS column

# View health check logs
docker inspect mijia-daemon | jq '.[0].State.Health'
```

## Best Practices

### 1. Use Host Network Mode
- Simplifies Bluetooth access
- Avoids NAT issues
- Recommended for production

### 2. Mount Config as Read-Only
```yaml
volumes:
  - ./config/config.yaml:/config/config.yaml:ro
```

### 3. Use Environment Variables for Secrets
```yaml
environment:
  - MIJIA_MQTT_PASSWORD=${MQTT_PASSWORD}
```

### 4. Enable Restart Policy
```yaml
restart: unless-stopped
```

### 5. Configure Log Rotation
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 6. Monitor Container Health
```bash
# Set up monitoring
docker events --filter 'event=health_status'
```

## Integration with Home Assistant

### Using Docker on Same Host as Home Assistant

```yaml
environment:
  - MIJIA_MQTT_BROKER_HOST=localhost  # or Home Assistant IP
  - MIJIA_MQTT_DISCOVERY_PREFIX=homeassistant
```

### Using Docker with Home Assistant Container

```yaml
# Add to same Docker network
networks:
  - homeassistant

networks:
  homeassistant:
    external: true
```

## Updating the Container

```bash
# Pull latest image
docker-compose pull

# Recreate container with new image
docker-compose up -d

# Or with Docker CLI
docker pull mijia-bluetooth-daemon:latest
docker stop mijia-daemon
docker rm mijia-daemon
# Run command again with new image
```

## Backup and Restore

### Backup Configuration
```bash
# Backup config
cp config/config.yaml config/config.yaml.backup

# Backup entire directory
tar -czf mijia-daemon-backup.tar.gz config/ docker-compose.yml .env
```

### Restore
```bash
# Restore from backup
tar -xzf mijia-daemon-backup.tar.gz
docker-compose up -d
```

## Performance Tuning

### Resource Limits
```yaml
services:
  mijia-daemon:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Optimize for Raspberry Pi
```yaml
environment:
  - PYTHONOPTIMIZE=2  # Enable optimizations
  - PYTHONUNBUFFERED=1  # Better logging (already set)
```

## Best Practices

### Security
1. ✅ **Never commit credentials**: Use `.env` file and add it to `.gitignore`
2. ✅ **Use read-only volumes**: Mount config files with `:ro` flag
3. ✅ **Non-root user**: Dockerfile uses non-root user (mijia:10001)
4. ⚠️ **Host network mode**: Required for Bluetooth but bypasses network isolation
5. ✅ **No privileged mode**: Not needed with host network mode

### Docker Image
1. ✅ **Multi-stage builds**: Reduces final image size (~150MB vs 1GB+)
2. ✅ **Specific base image tags**: `python:3.11-slim-bookworm` (no `latest`)
3. ✅ **Layer caching**: Requirements installed before copying source code
4. ✅ **No cache for pip**: `--no-cache-dir` flag reduces image size
5. ✅ **Clean up apt lists**: `rm -rf /var/lib/apt/lists/*` after installs

### Docker Compose
1. ✅ **No version field**: Modern Compose doesn't require it
2. ✅ **Use profiles**: Optional services enabled with `--profile` flag
3. ✅ **Named volumes**: For persistent data (MQTT broker logs, etc.)
4. ✅ **Structured logging**: JSON with max size and rotation
5. ✅ **Health checks**: Monitor daemon process health

### Development vs Production
```bash
# Development: Build and run with live logs
docker compose up --build

# Production: Detached with restart policy
docker compose up -d --restart unless-stopped
```

**Important:** Always ensure your MQTT broker is running and reachable before starting the daemon. Test connectivity with:
```bash
# Test MQTT broker connection
mosquitto_pub -h YOUR_BROKER_IP -p 1883 -u USERNAME -P PASSWORD -t test -m "hello"
```

### Monitoring
```bash
# Check container health
docker compose ps
docker inspect --format='{{.State.Health.Status}}' mijia-daemon

# Resource usage
docker stats mijia-daemon

# Logs with timestamps
docker compose logs -f --timestamps mijia-daemon

# Export logs for analysis
docker compose logs --no-color > daemon-logs.txt
```

### Regular Maintenance
```bash
# Update base images
docker compose pull
docker compose up -d

# Clean up old images
docker image prune -a

# Check disk usage
docker system df
```

## Support and Contributing

- **Issues**: https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/issues
- **Documentation**: https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon
- **Discussions**: GitHub Discussions

## License

See LICENSE file in the repository.
