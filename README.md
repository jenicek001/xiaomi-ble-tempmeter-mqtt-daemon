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

## 🚨 Important: Sensor Setup Instructions

⚠️ **CRITICAL SETUP STEP**: Before the daemon can connect to your Xiaomi sensors, you must activate them:

### For LYWSD03MMC and LYWSDCGQ/01ZM Sensors:

1. **Locate the bluetooth button** on the bottom side of the sensor
2. **Press and hold the button for 3-5 seconds** until the display blinks or changes
3. The sensor will now actively broadcast and accept connections for several minutes
4. **Start the daemon within this activation window**
5. **Repeat this process if the sensor becomes unresponsive**

**Important Notes:**
- Sensors automatically enter power-saving mode after ~15-30 minutes of inactivity
- If you experience connection timeouts, try reactivating the sensor
- Some sensors may require multiple button presses to activate properly
- The display should blink or show a connection indicator when activated

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

## Quick Start

### Method 1: Docker Compose (Recommended)

**Prerequisites:**
- Existing MQTT broker running (Mosquitto, Home Assistant built-in broker, etc.)
- MQTT broker accessible from the Raspberry Pi/host
- Docker and Docker Compose installed

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

3. **Start the daemon**:
   ```bash
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

### Basic docker-compose.yml

```yaml
version: '3.8'
services:
  mijia-daemon:
    build: .
    container_name: mijia-daemon
    restart: unless-stopped
    privileged: true          # Required for Bluetooth access
    network_mode: host        # Required for BLE scanning
    
    environment:
      - MIJIA_MQTT_BROKER_HOST=192.168.1.100
      - MIJIA_MQTT_USERNAME=homeassistant
      - MIJIA_MQTT_PASSWORD=your-password
      - MIJIA_LOG_LEVEL=INFO
      
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
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