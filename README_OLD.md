# Xiaomi Mijia Bluetooth Daemon

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

## Important: Sensor Setup Instructions

⚠️ **CRITICAL SETUP STEP**: Before the daemon can connect to your Xiaomi sensors, you must activate them:

### For LYWSD03MMC and LYWSDCGQ/01ZM Sensors:

1. **Locate the bluetooth button** on the bottom side of the sensor
2. **Press and hold the button for 3-5 seconds** until the display blinks
3. The sensor will now actively broadcast and accept connections
4. **Repeat this process if the sensor becomes unresponsive**

**Note**: Sensors go into power-saving mode and may need reactivation if they haven't been connected to for a while. If you're experiencing connection issues, try pressing the button again.



* **Standalone Operation**: No Home Assistant dependency required## Requirements

* **MQTT Publishing**: Real-time sensor data to any MQTT broker  

* **Home Assistant Integration**: Automatic MQTT Discovery support* Supported & tested on HassOS 4.13 (HassOS Release-4 build 13 (Stable))

* **Docker Ready**: Easy deployment with Docker Compose  * Warning: HassOS 4.14 has BLE bugs need fix, BLE devices can not be connected.

* **Raspberry Pi Optimized**: Efficient operation on ARM hardware  * Other versions need to be tested

* **Multi-Device Support**: Handle multiple thermometers simultaneously* Hardware need bluetooth adapter and be actived, tested on Raspberry PI 3 Model B

* **Auto-Discovery**: Automatically find and configure new devices  * Other hardwares need to be tested

* **Robust Error Handling**: Connection retry logic and graceful recovery

* **Comprehensive Monitoring**: Health checks and optional Prometheus metrics## Supported devices



## Supported Devices| Name                   | Model                  | Model no. |

| ---------------------- | ---------------------- | --------- |

| Device | Model | Features || Xiaomi Mijia BLE Temperature Hygrometer  |  | LYWSDCGQ/01ZM |

|--------|-------|----------|| Xiaomi Mijia BLE Temperature Hygrometer 2  |  | LYWSD03MMC  |

| ![LYWSD03MMC](pictures/LYWSD03MMC.jpg) | **LYWSD03MMC**<br>Mijia BLE Temperature Hygrometer 2 | Temperature, Humidity, Battery |

| ![LYWSDCGQ/01ZM](pictures/LYWSDCGQ01ZM.jpg) | **LYWSDCGQ/01ZM**<br>Original Mijia BLE Temperature Hygrometer | Temperature, Humidity, Battery |## Features



## Requirements### Mijia BLE Temperature Hygrometer (LYWSDCGQ/01ZM)



* **Operating System**: Linux (Raspberry Pi OS recommended)- Attributes

* **Python**: 3.9 or higher    - `temperature`

* **Bluetooth**: Bluetooth 4.0+ adapter  - `humidity`

* **MQTT Broker**: Any MQTT 3.1.1 compatible broker  - `battery`

* **Docker** (optional): For containerized deployment

### Mijia BLE Temperature Hygrometer 2 (LYWSD03MMC)

### Tested Platforms

- Attributes

* Raspberry Pi 3 Model B+  - `temperature`

* Raspberry Pi 4 Model B    - `humidity`

* Raspberry Pi Zero 2 W  - `battery`

* Ubuntu 20.04+ on x86_64

* Debian 11+ on ARM64## Install



## Quick StartYou can install this custom component by adding this repository ([https://github.com/leonxi/mitemp_bt2](https://github.com/leonxi/mitemp_bt2/)) to [HACS](https://hacs.xyz/) in the settings menu of HACS first. You will find the custom component in the integration menu afterwards, look for 'Xiaomi Mijia BLE Temperature Hygrometer 2 Integration'. Alternatively, you can install it manually by copying the custom_component folder to your Home Assistant configuration folder.



### Docker Compose (Recommended)

## Setup (_Optional_)

1. **Clone the repository**:

   ```bashFrom v0.2.0-dev releases, it will auto discovery without any configuration.

   git clone https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon.git

   cd xiaomi-ble-tempmeter-mqtt-daemon```yaml

   ```# configuration.yaml



2. **Configure the daemon**:sensor:

   ```bash  - platform: mitemp_bt2

   cp config/config.yaml.example config/config.yaml    mac: 'A4:C1:38:AA:AA:AA'

   # Edit config.yaml with your MQTT broker settings    mode: 'LYWSD03MMC'

   ```    name: book room

    period: 60

3. **Start the daemon**:  - platform: mitemp_bt2

   ```bash    mac: 'A4:C1:38:FF:FF:FF'

   docker-compose up -d    mode: 'LYWSD03MMC'

   ```    name: living room

    period: 60

4. **Monitor logs**:```

   ```bash

   docker-compose logs -f mijia-daemonConfiguration variables:

   ```- **mac** (*Required*): The MAC of your device.

- **mode** (*Optional*): The mode of your device. Default LYWSD03MMC

### Manual Installation- **name** (*Optional*): The name of your device.

- **period** (*Optional*): The scan period of your device. Default 300 seconds.

1. **Install dependencies**:

   ```bash## Panel Sample

   sudo apt update

   sudo apt install python3 python3-pip bluetooth bluez  ![LYWSD03MMC_PANEL_SHOW](/pictures/sample_panel_1.png)

   pip3 install -r requirements.txt

   ```## Todo



2. **Configure and run**:- Integration Options

   ```bash  - (_**Supported**_) Add auto discovery option, to control enable or disable discovery

   cp config/config.yaml.example config/config.yaml  - (_**Supported**_) Add period option, to control period of fetching devices' data, default period is 15 minutes. Avoid frequent access to Bluetooth devices, resulting in high power consumption of them.

   # Edit configuration- Known issues

   python3 src/main.py --config config/config.yaml  - (_**Fixed**_) When installation, discoverred devices can not be displayed, and set their own areas.

   ```  - (_**Fixed**_) In devices list, area or name can not be modified.



## Configuration[releases-shield]: https://img.shields.io/github/release/leonxi/mitemp_bt2.svg

[releases]: https://github.com/leonxi/mitemp_bt2/releases

The daemon supports multiple configuration methods with the following precedence:

1. **Environment Variables** (highest priority)
2. **Configuration File** (YAML)  
3. **Default Values** (lowest priority)

### Basic MQTT Configuration

```yaml
mqtt:
  broker: "192.168.1.100"          # Your MQTT broker IP
  port: 1883                       # MQTT port
  username: "homeassistant"        # MQTT username
  password: "your-password"        # MQTT password
  base_topic: "mijiableht"         # Base topic for sensor data

devices:
  auto_discovery: true             # Automatically find devices
  poll_interval: 300               # Poll every 5 minutes
```

### Environment Variables

```bash
# .env file
MQTT_BROKER=192.168.1.100
MQTT_USERNAME=homeassistant
MQTT_PASSWORD=secretpassword
DEVICES_AUTO_DISCOVERY=true
LOG_LEVEL=INFO
```

See [config/config.yaml.example](config/config.yaml.example) for complete configuration options.

## MQTT Topics

The daemon publishes sensor data as JSON to a single topic per device:

```
mijiableht/{device_id}/state      # JSON with temperature, humidity, battery, last_seen
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

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon.git
cd xiaomi-ble-tempmeter-mqtt-daemon

# Install development dependencies
make install-dev

# Run tests
make test

# Format code
make format

# Run daemon in development mode
make run-dev
```

### Project Structure

```
src/
├── main.py              # Main daemon entry point
├── bluetooth_manager.py # BLE communication
├── device_manager.py    # Device management  
├── mqtt_publisher.py    # MQTT client
├── config_manager.py    # Configuration handling
└── utils/               # Utility functions

config/                  # Configuration files
docker/                  # Docker configuration  
tests/                   # Test suite
docs/                    # Documentation
```

## Docker Deployment

### Basic Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  mijia-daemon:
    image: mijia-bluetooth-daemon:latest
    container_name: mijia-daemon
    restart: unless-stopped
    privileged: true          # Required for Bluetooth access
    network_mode: host        # Required for BLE scanning
    
    environment:
      - MQTT_BROKER=192.168.1.100
      - MQTT_USERNAME=homeassistant
      - LOG_LEVEL=INFO
      
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
```

### Production Deployment

For production deployments with secrets management:

```yaml
services:
  mijia-daemon:
    secrets:
      - mqtt_password
    environment:
      - MQTT_PASSWORD_FILE=/run/secrets/mqtt_password
```

## Monitoring and Health Checks

### Health Check Endpoint

The daemon provides a health check endpoint on port 8082 by default:

```bash
curl http://localhost:8082/health
```

### Prometheus Metrics (Optional)

Enable Prometheus metrics export:

```yaml
monitoring:
  enabled: true
  port: 8080
```

Metrics available at `http://localhost:8080/metrics`

## Troubleshooting

### Common Issues

**Bluetooth Permission Denied**
```bash
sudo usermod -a -G bluetooth $USER
sudo systemctl restart bluetooth
```

**Device Not Found**
```bash
# Scan for devices manually
sudo hcitool lescan

# Check Bluetooth status
sudo systemctl status bluetooth
```

**MQTT Connection Failed**
```bash
# Test MQTT connection
mosquitto_pub -h <broker> -t test -m "hello"
```

### Debug Mode

Run with debug logging:

```bash
python3 src/main.py --log-level DEBUG
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The original work is also MIT licensed - see [LICENSE-ORIGINAL](LICENSE-ORIGINAL) for the original license.

## Support

* **Issues**: [GitHub Issues](https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/issues)
* **Documentation**: [Project Wiki](https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/wiki)
* **Original Project**: [mitemp_bt2](https://github.com/leonxi/mitemp_bt2)

## Acknowledgments

* [@leonxi](https://github.com/leonxi) for the original Home Assistant integration
* The Home Assistant community for BLE protocol documentation
* Contributors to the bleak and paho-mqtt Python libraries