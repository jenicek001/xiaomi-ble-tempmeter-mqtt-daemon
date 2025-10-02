# Xiaomi Mijia Bluetooth Low Energy Temperature & Humidity Sensor to MQTT Daemon

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)

A standalone Linux daemon for Xiaomi Mijia Bluetooth thermometers that publishes sensor data to MQTT brokers with Home Assistant discovery support.

**No Home Assistant Required** • **Docker Ready** • **Raspberry Pi Optimized**

## Features

* **Standalone Operation**: No Home Assistant dependency required
* **MQTT Publishing**: Real-time sensor data to any MQTT broker  
* **Home Assistant Integration**: Automatic MQTT Discovery support
* **Docker Ready**: Easy deployment with Docker Compose  
* **Raspberry Pi Optimized**: Efficient operation on ARM hardware  
* **Multi-Device Support**: Handle multiple thermometers simultaneously
* **Auto-Discovery**: Automatically find and configure new devices  
* **Robust Error Handling**: Connection retry logic and graceful recovery
* **Comprehensive Monitoring**: Health checks and optional Prometheus metrics

## Supported Devices

| Device | Model | Features |
|--------|-------|----------|
| ![LYWSD03MMC](pictures/LYWSD03MMC.jpg) | **LYWSD03MMC**<br>Mijia BLE Temperature Hygrometer 2 | Temperature, Humidity, Battery |
| ![LYWSDCGQ/01ZM](pictures/LYWSDCGQ01ZM.jpg) | **LYWSDCGQ/01ZM**<br>Original Mijia BLE Temperature Hygrometer | Temperature, Humidity, Battery |

## Requirements

* **Operating System**: Linux (Raspberry Pi OS recommended)
* **Python**: 3.9 or higher
* **Bluetooth**: Bluetooth 4.0+ adapter  
* **MQTT Broker**: Any MQTT 3.1.1 compatible broker (Mosquitto recommended)
* **Docker** (optional): For containerized deployment

### Tested Platforms

* ✅ Raspberry Pi 3 Model B+
* ✅ Raspberry Pi 4 Model B
* ✅ Raspberry Pi Zero 2 W
* ✅ Ubuntu 20.04+ on x86_64
* ✅ Debian 11+ on ARM64

## Installing Docker on Raspberry Pi

If you don't have Docker installed yet, follow these steps to install Docker Engine and Docker Compose on Raspberry Pi OS:

```bash
# 1. Update system packages
sudo apt-get update

# 2. Install prerequisites
sudo apt-get install -y ca-certificates curl

# 3. Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 4. Add Docker repository to apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Update apt package index
sudo apt-get update

# 6. Install Docker Engine and Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. Verify installation
sudo docker --version
docker compose version

# 8. (Optional) Add your user to docker group to run without sudo
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
```

**Verify Docker is running:**
```bash
sudo systemctl status docker
```

If Docker is not running, start it with:
```bash
sudo systemctl start docker
sudo systemctl enable docker  # Enable auto-start on boot
```

## Quick Start

### Method 1: Docker Compose (Recommended)

**Prerequisites:**
- Existing MQTT broker running (Mosquitto, Home Assistant built-in broker, etc.)
- MQTT broker accessible from the Raspberry Pi/host
- Docker and Docker Compose installed
- **Note**: First run will build the Docker image locally (takes 2-3 minutes on Raspberry Pi)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon.git
   cd xiaomi-ble-tempmeter-mqtt-daemon
   ```

2. **Configure the daemon**:
   ```bash
   # Copy configuration templates
   cp config/config.yaml.example config/config.yaml
   cp .env.example .env
   
   # Edit with your MQTT broker address and credentials
   nano .env
   nano config/config.yaml
   ```

3. **Build and start the daemon**:
   ```bash
   # First run will automatically build the Docker image
   # This takes 2-3 minutes on Raspberry Pi, subsequent starts are instant
   docker compose up -d
   ```

4. **Monitor logs**:
   ```bash
   docker compose logs -f mijia-daemon
   ```

### Method 2: Manual Installation

1. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip bluetooth bluez
   ```

2. **Install Python packages**:
   ```bash
   # Using uvx (recommended)
   uvx --from bleak --with pydantic --with paho-mqtt --with PyYAML --with python-dotenv python -m src.main

   # Or install globally
   pip3 install bleak pydantic paho-mqtt PyYAML python-dotenv
   ```

3. **Configure and run**:
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit configuration with your settings
   python3 -m src.main --config config/config.yaml
   ```

## Configuration

The daemon supports multiple configuration methods:

### Basic Configuration (config.yaml)

```yaml
# Bluetooth configuration
bluetooth:
  adapter: 0                    # Bluetooth adapter number
  connection_timeout: 15        # Connection timeout in seconds
  retry_attempts: 3            # Number of retry attempts

# MQTT broker configuration  
mqtt:
  broker_host: "localhost"      # MQTT broker hostname/IP
  broker_port: 1883            # MQTT broker port
  username: "homeassistant"    # MQTT username
  password: "your-password"    # MQTT password
  client_id: "mijia-daemon"    # MQTT client ID
  discovery_prefix: "homeassistant"  # Home Assistant discovery prefix

# Device configuration
devices:
  auto_discovery: true          # Enable automatic device discovery
  poll_interval: 300           # Poll every 5 minutes
  
  # Static device configuration (replace with your actual MACs)
  static_devices:
    - mac: "4C:65:A8:DC:84:01"  # Your sensor MAC address
      name: "Living Room"       # Friendly name
      mode: "LYWSDCGQ"         # Device mode
      enabled: true            # Enable/disable device
```

### Environment Variables

Create a `.env` file or set environment variables:

```bash
MIJIA_MQTT_BROKER_HOST=192.168.1.100
MIJIA_MQTT_USERNAME=homeassistant
MIJIA_MQTT_PASSWORD=secretpassword
MIJIA_DEVICES_AUTO_DISCOVERY=true
MIJIA_LOG_LEVEL=INFO
```

## MQTT Topics and Data Format

### Data Topics

The daemon publishes sensor data as JSON to a single topic per device:

```
mijiableht/{device_id}/state      # JSON with all sensor data
```

**Example JSON message:**
```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-09-26T10:30:45Z"
}
```

### Home Assistant Discovery

Automatic discovery messages are published to:

```
homeassistant/sensor/mijiableht_{device_id}_temperature/config
homeassistant/sensor/mijiableht_{device_id}_humidity/config  
homeassistant/sensor/mijiableht_{device_id}_battery/config
```

## Troubleshooting

### Common Issues

**❌ Connection Failed / Device Not Responding**
1. **First, activate the sensor** (press and hold button on bottom)
2. Check if device is discovered: `sudo hcitool lescan`
3. Restart Bluetooth service: `sudo systemctl restart bluetooth`

**❌ Bluetooth Permission Denied**
```bash
sudo usermod -a -G bluetooth $USER
# Logout and login again
```

**❌ MQTT Connection Failed**
```bash
# Test MQTT connection
mosquitto_pub -h <broker> -u <username> -P <password> -t test -m "hello"
```

**❌ Discovery Not Working**
```bash
# Check Bluetooth adapter
hciconfig
sudo hciconfig hci0 up

# Scan manually
sudo bluetoothctl
scan on
```

### Debug Mode

Run with debug logging for detailed troubleshooting:

```bash
python3 -m src.main --log-level DEBUG
```

### Testing Individual Sensors

Use the test script to verify sensor connectivity:

```bash
# Test GATT connection
uvx --from bleak --with pydantic python test_gatt.py
```

## Docker Deployment

### Image Build Process

The Docker image is **built locally** from source on first run. There is no pre-built image to pull from a registry.

**Build Details:**
- **First run**: `docker compose up` automatically builds the image (2-3 minutes on Raspberry Pi)
- **Subsequent runs**: Uses cached image (starts in seconds)
- **Rebuilding**: Use `docker compose build --no-cache` to rebuild from scratch
- **Architecture**: Multi-stage build optimized for both ARM64 and AMD64

### Basic docker-compose.yml

```yaml
services:
  mijia-daemon:
    build:
      context: .
      dockerfile: Dockerfile
    image: mijia-bluetooth-daemon:latest
    container_name: mijia-daemon
    restart: unless-stopped
    network_mode: host        # Required for BLE scanning
    user: root                # Required for Bluetooth access
    
    env_file:
      - .env
    
    environment:
      - MIJIA_LOG_LEVEL=${MIJIA_LOG_LEVEL:-INFO}
      - MIJIA_BLUETOOTH_ADAPTER=${MIJIA_BLUETOOTH_ADAPTER:-0}
      - TZ=${TZ:-Europe/Prague}
      
    volumes:
      - ./config/config.yaml:/config/config.yaml:ro
      - /var/run/dbus:/var/run/dbus:ro
      - ./logs:/app/logs
```

### Manual Build

To build the image manually before running:

```bash
# Build image
docker compose build

# Or rebuild without cache
docker compose build --no-cache

# Then start
docker compose up -d
```

### Makefile Commands

The project includes a Makefile for common Docker operations:

```bash
make docker-build         # Build Docker image
make docker-run           # Start daemon
make docker-stop          # Stop daemon
make docker-restart       # Restart daemon
make docker-logs          # View logs
make docker-shell         # Open shell in container
make docker-health        # Check health status
make docker-rebuild       # Rebuild from scratch
make docker-clean         # Remove images and containers
```

## Monitoring

### Health Check

The daemon provides a health check endpoint:

```bash
curl http://localhost:8082/health
```

### Logs

Monitor daemon logs:

```bash
# Docker
docker-compose logs -f mijia-daemon

# Manual installation  
journalctl -f -u mijia-daemon
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon.git
cd xiaomi-ble-tempmeter-mqtt-daemon

# Install development dependencies
make install-dev

# Run tests
make test

# Run daemon in development mode
make run-dev
```

## Attribution

This project is derived from the excellent [mitemp_bt2](https://github.com/leonxi/mitemp_bt2) Home Assistant integration by [@leonxi](https://github.com/leonxi), adapted for standalone operation. See [ATTRIBUTION.md](./ATTRIBUTION.md) for detailed attribution information.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

* **Issues**: [GitHub Issues](https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/issues)
* **Documentation**: [Project Wiki](https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/wiki)
* **Original Project**: [mitemp_bt2](https://github.com/leonxi/mitemp_bt2)

## Acknowledgments

* [@leonxi](https://github.com/leonxi) for the original Home Assistant integration
* The Home Assistant community for BLE protocol documentation  
* Contributors to the bleak and paho-mqtt Python libraries