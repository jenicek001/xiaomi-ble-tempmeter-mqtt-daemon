# Xiaomi Mijia BLE Thermometer Linux Daemon - Migration Planning

## Overview

This document outlines the migration plan to transform the existing Home Assistant integration for Xiaomi Mijia Bluetooth thermometers into a standalone Linux daemon running on Raspberry Pi. The daemon will communicate directly with BLE thermometers using native OS drivers and publish measurements to MQTT.

## Current Implementation Analysis

### Repository Structure
The current repository is a Home Assistant custom component with the following key components:

```
custom_components/mitemp_bt2/
├── __init__.py          # Main integration setup and hub management
├── sensor.py            # BLE scanner singleton and sensor entities
├── common.py            # Device discovery and management
├── const.py             # Constants and configuration
├── config_flow.py       # Configuration UI flow
├── manifest.json        # Integration metadata
└── strings.json         # Localization strings
```

### Supported Devices
- **LYWSD03MMC**: Mijia BLE Temperature Hygrometer 2
- **LYWSDCGQ/01ZM**: Original Mijia BLE Temperature Hygrometer

### Current BLE Communication Protocol

#### Library Dependencies
- **bluepy**: Python wrapper for BlueZ (Linux Bluetooth stack)
- Version requirement: `bluepy>=1.1.0`

#### BLE Protocol Details
1. **Connection**: Direct BLE connection to device MAC address
2. **Notification Setup**: 
   - Handle `0x0038`: Enable temperature, humidity, and battery notifications
   - Handle `0x0046`: Device-specific configuration (LYWSD03MMC mode)
3. **Data Format** (5 bytes):
   - Bytes 0-1: Temperature (signed 16-bit, divide by 100)
   - Byte 2: Humidity (8-bit)
   - Bytes 3-4: Battery voltage (16-bit, divide by 1000)
4. **Battery Calculation**: `min(int(round((voltage - 2.1), 2) * 100), 100)%`

#### Device Discovery
- Uses BLE scanning to find devices by "Complete Local Name"
- Filters devices based on known mode names: `["LYWSD03MMC", "LYWSDCGQ/01ZM"]`

## Migration Architecture

### 1. Core Daemon Components

#### A. Bluetooth Manager (`bluetooth_manager.py`)
```python
class BluetoothManager:
    # Handles BLE scanning, device connection, and data reading
    # Replaces SingletonBLEScanner functionality
    # Uses async/await pattern with bleak library
```

#### B. Device Manager (`device_manager.py`)
```python
class DeviceManager:
    # Manages known devices, auto-discovery, and device state
    # Maintains device registry and configuration
    # Handles device reconnection and error recovery
```

#### C. MQTT Publisher (`mqtt_publisher.py`)
```python
class MQTTPublisher:
    # Publishes sensor data to MQTT broker
    # Handles MQTT connection, reconnection, and message formatting
    # Supports Home Assistant MQTT Discovery protocol
```

#### D. Configuration Manager (`config_manager.py`)
```python
class ConfigManager:
    # Loads and validates configuration from YAML/JSON
    # Supports environment variables and Docker secrets
    # Handles configuration reloading
```

#### E. Main Daemon (`main.py`)
```python
class MijiaTemperatureDaemon:
    # Main orchestrator that coordinates all components
    # Handles graceful shutdown, logging, and health checks
```

### 2. Daemon Features

#### Core Functionality
- **Auto-discovery**: Scan for and automatically add new Xiaomi thermometers
- **Data Collection**: Periodic reading from configured devices
- **MQTT Publishing**: Publish temperature, humidity, and battery data
- **Error Handling**: Robust retry logic and error recovery
- **Logging**: Comprehensive logging with configurable levels
- **Health Monitoring**: Built-in health checks and status reporting

#### Advanced Features
- **Home Assistant Integration**: MQTT Discovery support for seamless HA integration
- **Multiple MQTT Topics**: Configurable topic structure
- **Data Validation**: Sensor data validation and filtering
- **Configurable Intervals**: Per-device or global polling intervals
- **Prometheus Metrics**: Optional metrics export for monitoring
- **Web Dashboard**: Simple web interface for status monitoring

### 3. Configuration Management (Best Practices)

#### Configuration Hierarchy
Following the [12-Factor App](https://12factor.net/config) methodology, the daemon supports multiple configuration sources in order of precedence:

1. **Environment Variables** (highest priority)
2. **`.env` file** (for local development)
3. **Configuration files** (YAML/JSON)
4. **Default values** (lowest priority)

#### A. Environment Variables (.env file)
```bash
# .env file for local development
# Production: Set these as container environment variables

# MQTT Configuration
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_USERNAME=homeassistant
MQTT_PASSWORD=secretpassword
MQTT_CLIENT_ID=mijia-daemon
MQTT_BASE_TOPIC=mijia
MQTT_DISCOVERY_PREFIX=homeassistant
MQTT_RETAIN=true
MQTT_QOS=1

# Bluetooth Configuration
BLUETOOTH_ADAPTER=0
BLUETOOTH_SCAN_INTERVAL=300
BLUETOOTH_CONNECTION_TIMEOUT=10
BLUETOOTH_RETRY_ATTEMPTS=3

# Device Configuration
DEVICES_AUTO_DISCOVERY=true
DEVICES_POLL_INTERVAL=300

# Static Devices (comma-separated for environment variables)
STATIC_DEVICES_MACS="A4:C1:38:AA:AA:AA,A4:C1:38:BB:BB:BB"
STATIC_DEVICES_NAMES="Living Room,Bedroom"
STATIC_DEVICES_MODES="LYWSD03MMC,LYWSD03MMC"
STATIC_DEVICES_INTERVALS="180,300"

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE=/var/log/mijia-daemon.log

# Optional Features
MONITORING_ENABLED=false
MONITORING_PORT=8080
WEB_DASHBOARD_ENABLED=false
WEB_DASHBOARD_PORT=8081
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8082
```

#### B. Configuration File (config.yaml)
```yaml
# config.yaml - Structured configuration for complex setups
bluetooth:
  adapter: ${BLUETOOTH_ADAPTER:-0}
  scan_interval: ${BLUETOOTH_SCAN_INTERVAL:-300}
  connection_timeout: ${BLUETOOTH_CONNECTION_TIMEOUT:-10}
  retry_attempts: ${BLUETOOTH_RETRY_ATTEMPTS:-3}

mqtt:
  broker: ${MQTT_BROKER:-"localhost"}
  port: ${MQTT_PORT:-1883}
  username: ${MQTT_USERNAME:-""}
  password: ${MQTT_PASSWORD:-""}
  client_id: ${MQTT_CLIENT_ID:-"mijia-daemon"}
  
  # Topic configuration
  base_topic: ${MQTT_BASE_TOPIC:-"mijia"}
  discovery_prefix: ${MQTT_DISCOVERY_PREFIX:-"homeassistant"}
  
  # Payload settings
  retain: ${MQTT_RETAIN:-true}
  qos: ${MQTT_QOS:-1}

devices:
  auto_discovery: ${DEVICES_AUTO_DISCOVERY:-true}
  poll_interval: ${DEVICES_POLL_INTERVAL:-300}
  
  # Static device configuration
  static_devices:
    - mac: "A4:C1:38:AA:AA:AA"
      name: "Living Room"
      mode: "LYWSD03MMC"
      poll_interval: 180
      enabled: true
    - mac: "A4:C1:38:BB:BB:BB"
      name: "Bedroom"
      mode: "LYWSD03MMC" 
      poll_interval: 300
      enabled: true
    - mac: "A4:C1:38:CC:CC:CC"
      name: "Kitchen"
      mode: "LYWSDCGQ/01ZM"
      poll_interval: 240
      enabled: false  # Temporarily disabled

logging:
  level: ${LOG_LEVEL:-"INFO"}
  format: ${LOG_FORMAT:-"%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
  file: ${LOG_FILE:-""}  # Empty means stdout only

# Optional features
monitoring:
  enabled: ${MONITORING_ENABLED:-false}
  port: ${MONITORING_PORT:-8080}
  
web_dashboard:
  enabled: ${WEB_DASHBOARD_ENABLED:-false}
  port: ${WEB_DASHBOARD_PORT:-8081}
  
health_check:
  enabled: ${HEALTH_CHECK_ENABLED:-true}
  port: ${HEALTH_CHECK_PORT:-8082}
```

#### C. Configuration Loading Strategy
```python
# config_manager.py - Configuration loading implementation
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/config.yaml"
        self.config = self._load_configuration()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from multiple sources with precedence"""
        
        # 1. Load .env file (if exists)
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # 2. Load YAML configuration file
        config = {}
        if Path(self.config_file).exists():
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
        
        # 3. Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        # 4. Validate configuration
        self._validate_configuration(config)
        
        return config
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides with proper type conversion"""
        # Implementation details...
        
    def _validate_configuration(self, config: Dict):
        """Validate configuration against schema"""
        # JSON Schema validation implementation...
```

#### D. Docker Configuration Examples

**docker-compose.yml with environment variables:**
```yaml
version: '3.8'

services:
  mijia-daemon:
    build: .
    container_name: mijia-bluetooth-daemon
    restart: unless-stopped
    privileged: true
    network_mode: host
    
    environment:
      # MQTT Configuration
      - MQTT_BROKER=192.168.1.100
      - MQTT_USERNAME=homeassistant
      - MQTT_PASSWORD=${MQTT_PASSWORD}  # From host environment
      - MQTT_BASE_TOPIC=sensors/mijia
      
      # Device Configuration
      - DEVICES_AUTO_DISCOVERY=true
      - DEVICES_POLL_INTERVAL=180
      
      # Known device MAC addresses
      - STATIC_DEVICES_MACS=A4:C1:38:AA:AA:AA,A4:C1:38:BB:BB:BB
      - STATIC_DEVICES_NAMES=Living Room,Bedroom
      
      # Logging
      - LOG_LEVEL=INFO
      
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./.env:/app/.env:ro  # Optional: mount .env file
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Production secrets management:**
```yaml
# docker-compose.prod.yml
secrets:
  mqtt_password:
    file: ./secrets/mqtt_password.txt
  mqtt_username:
    file: ./secrets/mqtt_username.txt

services:
  mijia-daemon:
    secrets:
      - mqtt_password
      - mqtt_username
    environment:
      - MQTT_PASSWORD_FILE=/run/secrets/mqtt_password
      - MQTT_USERNAME_FILE=/run/secrets/mqtt_username
```

## Repository Management and Forking Strategy

### Creating the New Repository

#### Option 1: Fork with Proper Attribution (Recommended)
1. **Fork the Original Repository**
   ```bash
   # On GitHub: Click "Fork" button on https://github.com/leonxi/mitemp_bt2
   # This creates: https://github.com/yourusername/mijia-bluetooth-daemon
   ```

2. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/mijia-bluetooth-daemon.git
   cd mijia-bluetooth-daemon
   
   # Add upstream remote to track original repo
   git remote add upstream https://github.com/leonxi/mitemp_bt2.git
   
   # Verify remotes
   git remote -v
   # origin    https://github.com/yourusername/mijia-bluetooth-daemon.git (fetch)
   # origin    https://github.com/yourusername/mijia-bluetooth-daemon.git (push)
   # upstream  https://github.com/leonxi/mitemp_bt2.git (fetch)
   # upstream  https://github.com/leonxi/mitemp_bt2.git (push)
   ```

3. **Create Development Branch**
   ```bash
   git checkout -b daemon-migration
   git push -u origin daemon-migration
   ```

#### Option 2: New Repository with Attribution
If a complete restructure is preferred:

1. **Create New Repository**
   ```bash
   # On GitHub: Create new repository "mijia-bluetooth-daemon"
   git clone https://github.com/yourusername/mijia-bluetooth-daemon.git
   cd mijia-bluetooth-daemon
   ```

2. **Add Original as Subtree/Submodule**
   ```bash
   # Option A: Subtree (includes history)
   git subtree add --prefix=original-integration \
     https://github.com/leonxi/mitemp_bt2.git main --squash
   
   # Option B: Submodule (references original)
   git submodule add https://github.com/leonxi/mitemp_bt2.git original-integration
   ```

### License and Attribution Management

#### Update README.md with Proper Attribution
```markdown
# Mijia Bluetooth Daemon

A standalone Linux daemon for Xiaomi Mijia Bluetooth thermometers, derived from the excellent Home Assistant integration.

## Attribution and License

This project is based on the [mitemp_bt2](https://github.com/leonxi/mitemp_bt2) Home Assistant integration by [@leonxi](https://github.com/leonxi).

### Original Project
- **Repository**: https://github.com/leonxi/mitemp_bt2
- **Author**: [@leonxi](https://github.com/leonxi)
- **License**: [Check original repository](https://github.com/leonxi/mitemp_bt2/blob/main/LICENSE)
- **Description**: Home Assistant custom component for Xiaomi Mijia BLE Temperature Hygrometer

### Changes and Adaptations
This daemon extends the original work by:
- Converting from Home Assistant integration to standalone daemon
- Adding MQTT publishing capabilities
- Implementing Docker containerization
- Adding comprehensive configuration management
- Enhancing error handling and monitoring

### License Compliance
This project respects the original license terms. Please refer to:
- Original license: [LICENSE-ORIGINAL](./LICENSE-ORIGINAL)
- Modifications license: [LICENSE](./LICENSE)
```

#### License File Structure
```
LICENSE-ORIGINAL          # Copy of original project's license
LICENSE                   # License for your modifications
ATTRIBUTION.md            # Detailed attribution information
```

#### ATTRIBUTION.md Template
```markdown
# Attribution and Acknowledgments

## Primary Attribution

This project is derived from the **mitemp_bt2** Home Assistant integration.

**Original Work:**
- Repository: https://github.com/leonxi/mitemp_bt2
- Author: [@leonxi](https://github.com/leonxi)
- License: [Original License Type]
- Original Description: Home Assistant custom component for Xiaomi Mijia BLE Temperature Hygrometer

## Key Contributions from Original Work

The following components and concepts are directly derived from or inspired by the original work:

### Core BLE Communication Protocol
- Bluetooth device discovery methods (`common.py`)
- BLE characteristic handles and data parsing (`sensor.py`)
- Device type detection and mode handling (`const.py`)

### Device Support
- LYWSD03MMC protocol implementation
- LYWSDCGQ/01ZM protocol implementation  
- Battery level calculation algorithm
- Temperature and humidity data parsing

### Configuration Structure
- Device configuration schema
- Polling interval management
- Multi-device support architecture

## Modifications and Enhancements

### New Components (Original Work)
- MQTT client integration
- Docker containerization
- Standalone daemon architecture
- Configuration management system
- Web dashboard and monitoring
- Health check endpoints

### Modified Components
- Bluetooth manager (adapted from SingletonBLEScanner)
- Device manager (extended from original device handling)
- Configuration system (expanded from original config flow)

## Dependencies Attribution

### From Original Project
- bluepy: Bluetooth Low Energy library
- Device protocol specifications and implementation

### New Dependencies
- bleak: Modern async BLE library
- paho-mqtt: MQTT client library
- PyYAML: Configuration file parsing
- aiohttp: Web server components

## Compliance and Usage

This derivative work:
1. Maintains all original copyright notices
2. Clearly identifies modifications and additions
3. Provides proper attribution to original authors
4. Complies with original license terms
5. Does not claim ownership of original work

## Contributing

When contributing to this project:
1. Respect the original work's attribution
2. Clearly mark new contributions
3. Maintain license compliance
4. Update this attribution file when adding significant original work

## Contact

For questions about attribution or licensing:
- Original work: Contact [@leonxi](https://github.com/leonxi)
- This derivative: [Your contact information]
```

### Ongoing Maintenance Strategy

#### Staying Updated with Original
```bash
# Fetch updates from original repository
git fetch upstream

# Review changes in original
git log HEAD..upstream/main --oneline

# Selectively merge relevant updates
git checkout daemon-migration
git cherry-pick <relevant-commits>

# Or merge entire upstream changes
git merge upstream/main
```

#### Contributing Back to Original
```bash
# Create bug fixes or improvements that benefit original project
git checkout -b fix-bluetooth-issue
# Make changes...
git commit -m "Fix: Bluetooth connection stability issue"

# Push to your fork
git push origin fix-bluetooth-issue

# Create PR to original repository
# On GitHub: Create Pull Request from your fork to leonxi/mitemp_bt2
```

### Communication with Original Author

#### Initial Contact Template
```
Subject: Fork/Derivative Work Notification - Mijia Bluetooth Daemon

Hello @leonxi,

I hope this message finds you well. I wanted to reach out regarding your excellent mitemp_bt2 Home Assistant integration.

I'm working on a derivative project that adapts your integration into a standalone Linux daemon for Raspberry Pi deployments. The daemon will:
- Use your BLE communication protocols and device support
- Add MQTT publishing capabilities  
- Provide Docker containerization
- Maintain full attribution to your original work

I want to ensure I'm handling the attribution and licensing correctly:
1. I've forked your repository and maintained all original license/copyright notices
2. Created comprehensive attribution documentation
3. Clearly marked all modifications and additions
4. Will contribute relevant bug fixes back to your project

Repository: [Your fork URL]
Planning Document: [Link to PLANNING.md]

Would you prefer any specific attribution format or have any concerns about this derivative work?

I'm also happy to contribute any improvements back to your original project if they would be beneficial.

Thank you for the excellent foundation work!

Best regards,
[Your Name]
```

## Implementation Steps

### Phase 1: Core Daemon Development

#### Step 1.1: Setup Project Structure
```
mijia-bluetooth-daemon/
├── src/
│   ├── __init__.py
│   ├── main.py              # Main daemon entry point
│   ├── bluetooth_manager.py # BLE communication
│   ├── device_manager.py    # Device management
│   ├── mqtt_publisher.py    # MQTT client
│   ├── config_manager.py    # Configuration handling
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # Logging setup
│       └── health.py        # Health check utilities
├── config/
│   ├── config.yaml          # Default configuration
│   ├── config.schema.json   # JSON Schema for validation
│   ├── .env.example         # Environment variables template
│   └── devices.yaml.example # Device configuration examples
├── docker/
│   ├── Dockerfile           # Container definition
│   ├── docker-compose.yml   # Compose configuration
│   └── entrypoint.sh        # Container entrypoint
├── tests/
│   ├── __init__.py
│   ├── test_bluetooth.py
│   ├── test_mqtt.py
│   └── test_config.py
├── docs/
│   ├── README.md
│   ├── CONFIGURATION.md
│   └── DEPLOYMENT.md
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── setup.py                # Package setup
├── Makefile                # Build automation
├── .vscode/
│   ├── settings.json       # VS Code workspace settings
│   ├── launch.json         # Debug configurations
│   └── tasks.json          # Build/test tasks
├── .copilot-instructions.md # GitHub Copilot development guidelines
├── .mcp-config.json        # MCP server configuration for Context7
└── .github/
    └── workflows/
        └── ci.yml          # CI/CD pipeline
```

#### Step 1.2: Implement Core Components

**Dependencies Selection:**
- **bleak**: Modern async BLE library (replacement for bluepy)
- **paho-mqtt**: MQTT client library
- **PyYAML**: Configuration file parsing
- **asyncio**: Async/await support
- **aiohttp**: Web dashboard and health checks
- **prometheus_client**: Metrics export (optional)

**Key Implementation Notes:**
- Replace `bluepy` with `bleak` for better async support and cross-platform compatibility
- Implement proper async/await patterns throughout
- Use structured logging with JSON format option
- Implement graceful shutdown handling (SIGTERM, SIGINT)
- Add configuration validation using JSON Schema

#### Step 1.3: BLE Protocol Migration
```python
# bluetooth_manager.py - Key implementation points

import asyncio
from bleak import BleakClient, BleakScanner
from typing import Optional, Dict, List

class BluetoothManager:
    async def connect_device(self, mac: str) -> Optional[BleakClient]:
        """Connect to BLE device with retry logic"""
        
    async def read_sensor_data(self, client: BleakClient, mode: str) -> Dict:
        """Read temperature, humidity, and battery data"""
        # Handle 0x0038: Enable notifications
        # Handle 0x0046: Device-specific config (LYWSD03MMC)
        # Parse 5-byte data format
        
    async def discover_devices(self) -> List[Dict]:
        """Scan for Xiaomi thermometers"""
        # Filter by device names: LYWSD03MMC, LYWSDCGQ/01ZM
```

#### Step 1.4: MQTT Integration
```python
# mqtt_publisher.py - Key implementation points

import paho.mqtt.client as mqtt
from typing import Dict, Optional

class MQTTPublisher:
    def publish_sensor_data(self, device_id: str, data: Dict):
        """Publish sensor readings to MQTT"""
        # Topics: mijia/{device_id}/temperature
        #         mijia/{device_id}/humidity  
        #         mijia/{device_id}/battery
        
    def publish_homeassistant_discovery(self, device: Dict):
        """Publish Home Assistant MQTT Discovery messages"""
        # Auto-discovery for seamless HA integration
```

### Phase 2: Docker Containerization

#### Step 2.1: Dockerfile Design
```dockerfile
# Multi-stage build for smaller production image
FROM python:3.11-slim as builder
# Build stage...

FROM python:3.11-slim as runtime
# Runtime stage with minimal dependencies
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app
WORKDIR /app

# Non-root user for security
USER daemon

EXPOSE 8080 8081 8082
ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["python", "-m", "src.main"]
```

#### Step 2.2: Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  mijia-daemon:
    build: .
    container_name: mijia-bluetooth-daemon
    restart: unless-stopped
    
    # Bluetooth access
    privileged: true
    network_mode: host
    
    # Alternative: specific device access
    # devices:
    #   - /dev/bus/usb:/dev/bus/usb
    #   - /var/run/dbus:/var/run/dbus
    
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      
    environment:
      - LOG_LEVEL=INFO
      - CONFIG_FILE=/app/config/config.yaml
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mqtt-broker
    restart: unless-stopped
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
```

#### Step 2.3: Raspberry Pi Optimization
```dockerfile
# ARM64 optimized Dockerfile
FROM arm64v8/python:3.11-slim

# Raspberry Pi specific bluetooth setup
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    libbluetooth-dev \
    pi-bluetooth \
    && systemctl enable bluetooth \
    && rm -rf /var/lib/apt/lists/*

# Enable Bluetooth without pairing
RUN echo "class 0x000100" >> /etc/bluetooth/main.conf
RUN echo "DiscoverableTimeout = 0" >> /etc/bluetooth/main.conf
```

### Phase 3: Advanced Features

#### Step 3.1: Home Assistant Integration
- MQTT Discovery protocol implementation
- Automatic device creation in Home Assistant
- Device class configuration (temperature, humidity, battery)
- Proper entity naming and unique IDs

#### Step 3.2: Monitoring and Observability
- Prometheus metrics export
- Health check endpoints
- Status dashboard with device states
- Connection status monitoring
- Error rate tracking

#### Step 3.3: Production Enhancements
- Configuration file validation
- Graceful configuration reloading
- Log rotation
- Systemd service file
- Backup/restore functionality

## Deployment Strategy

### Prerequisites

#### Raspberry Pi Setup
1. **Operating System**: Raspberry Pi OS (64-bit recommended)
2. **Bluetooth**: Ensure Bluetooth is enabled and working
3. **Docker**: Install Docker and Docker Compose
4. **Permissions**: Add user to `docker` and `bluetooth` groups

#### System Configuration
```bash
# Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Add user to required groups
sudo usermod -a -G docker $USER
sudo usermod -a -G bluetooth $USER

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo pip3 install docker-compose
```

### Deployment Options

#### Option 1: Docker Compose (Recommended)
```bash
# Clone repository
git clone https://github.com/username/mijia-bluetooth-daemon
cd mijia-bluetooth-daemon

# Configure
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your settings

# Deploy
docker-compose up -d

# Monitor
docker-compose logs -f mijia-daemon
```

#### Option 2: Docker Run
```bash
docker run -d \
  --name mijia-daemon \
  --privileged \
  --network host \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  -e LOG_LEVEL=INFO \
  mijia-bluetooth-daemon:latest
```

#### Option 3: Systemd Service
```bash
# Install Python package
pip3 install mijia-bluetooth-daemon

# Create systemd service
sudo cp scripts/mijia-daemon.service /etc/systemd/system/
sudo systemctl enable mijia-daemon
sudo systemctl start mijia-daemon
```

### Configuration Management

#### Environment Variables
```bash
# Override configuration via environment
export MQTT_BROKER="192.168.1.100"
export MQTT_USERNAME="homeassistant"
export MQTT_PASSWORD="secret"
export LOG_LEVEL="DEBUG"
export POLL_INTERVAL="180"
```

#### Docker Secrets (Production)
```yaml
# docker-compose.yml
secrets:
  mqtt_password:
    file: ./secrets/mqtt_password.txt
    
services:
  mijia-daemon:
    secrets:
      - mqtt_password
    environment:
      - MQTT_PASSWORD_FILE=/run/secrets/mqtt_password
```

## Testing Strategy

### Unit Tests
- Bluetooth manager functionality
- MQTT publisher operations
- Configuration parsing and validation
- Device discovery and management

### Integration Tests
- End-to-end BLE communication
- MQTT message publishing
- Configuration reloading
- Error handling and recovery

### Hardware Testing
- Multiple Raspberry Pi models (3B+, 4B, Zero 2W)
- Different Bluetooth adapters
- Network connectivity scenarios
- Power management testing

### Load Testing
- Multiple device handling (10+ thermometers)
- High-frequency polling scenarios
- MQTT broker stress testing
- Memory usage profiling

## Security Considerations

### Container Security
- Run as non-root user
- Minimal base image
- Regular security updates
- Secrets management

### Network Security
- MQTT authentication
- TLS encryption for MQTT
- Network isolation
- Firewall configuration

### Device Security
- BLE security considerations
- Device authentication (if supported)
- Data validation and sanitization
- Rate limiting

## Performance Optimization

### Bluetooth Performance
- Connection pooling
- Efficient scanning strategies
- Retry logic optimization
- Battery-friendly polling intervals

### Resource Usage
- Memory-efficient data structures
- CPU usage optimization
- Disk I/O minimization
- Network bandwidth optimization

### Scalability
- Horizontal scaling support
- Load balancing considerations
- Database backend (optional)
- Clustering support

## Migration Checklist

### Pre-Migration
- [ ] Analyze current Home Assistant setup
- [ ] Document existing device configurations
- [ ] Test Bluetooth connectivity on target hardware
- [ ] Setup MQTT broker
- [ ] Prepare Docker environment

### Development Phase
- [ ] Implement core daemon components
- [ ] Create Docker configuration
- [ ] Setup testing framework
- [ ] Implement configuration management
- [ ] Add logging and monitoring

### Testing Phase
- [ ] Unit test all components
- [ ] Integration testing with real devices
- [ ] Performance testing
- [ ] Security testing
- [ ] Documentation validation

### Deployment Phase
- [ ] Production configuration
- [ ] Monitoring setup
- [ ] Backup strategy
- [ ] Rollback procedures
- [ ] User documentation

### Post-Deployment
- [ ] Monitor system performance
- [ ] Collect user feedback
- [ ] Optimize based on real-world usage
- [ ] Plan feature enhancements
- [ ] Maintain security updates

## IDE and Coding Agent Integration

### GitHub Copilot and MCP Server Instructions

To ensure the best development experience when working on this project, the following instructions should be added to the final repository for IDE coding agents (GitHub Copilot, Cursor, etc.):

#### Repository-Level Instructions (.copilot-instructions.md)

```markdown
# GitHub Copilot Instructions for Mijia Bluetooth Daemon

## Project Context
This is a standalone Linux daemon for Xiaomi Mijia Bluetooth thermometers that:
- Communicates with BLE devices using Python's `bleak` library
- Publishes sensor data to MQTT brokers
- Runs in Docker containers on Raspberry Pi
- Supports Home Assistant MQTT Discovery protocol

## Development Guidelines

### Documentation and Learning Resources
When implementing features or solving problems, use the following MCP (Model Context Protocol) servers to get up-to-date documentation:

#### Context7 MCP Server Usage
```bash
# Always fetch current documentation for key libraries
mcp_context7_get-library-docs --library="bleak" --topic="bluetooth low energy async"
mcp_context7_get-library-docs --library="paho-mqtt" --topic="mqtt client python"
mcp_context7_get-library-docs --library="docker" --topic="bluetooth device access"
mcp_context7_get-library-docs --library="asyncio" --topic="async programming patterns"
mcp_context7_get-library-docs --library="pydantic" --topic="configuration validation"
```

#### Key Libraries to Reference via Context7
1. **bleak**: For Bluetooth Low Energy communication
   - Topic areas: device scanning, characteristic notification, connection management
2. **paho-mqtt**: For MQTT client functionality  
   - Topic areas: connection handling, message publishing, reconnection logic
3. **asyncio**: For asynchronous programming patterns
   - Topic areas: event loops, coroutines, exception handling
4. **docker**: For containerization best practices
   - Topic areas: bluetooth device access, privileged containers, health checks
5. **pydantic**: For configuration validation and management
   - Topic areas: settings management, environment variable parsing
6. **prometheus_client**: For metrics and monitoring
   - Topic areas: counter metrics, gauge metrics, histogram metrics

### Code Implementation Patterns

#### Bluetooth Device Communication
When implementing BLE functionality:
- Always use async/await patterns with `bleak`
- Implement proper retry logic for connection failures
- Handle device disconnections gracefully
- Use notification callbacks for real-time data

#### MQTT Publishing
When implementing MQTT features:
- Follow Home Assistant MQTT Discovery specification
- Implement connection keepalive and reconnection
- Use appropriate QoS levels for different message types
- Structure topics hierarchically (e.g., `mijia/{device_id}/{sensor_type}`)

#### Configuration Management
When working with configuration:
- Support environment variable overrides
- Use Pydantic for validation and type safety
- Implement configuration reloading without restart
- Provide clear validation error messages

#### Error Handling and Logging
- Use structured logging with JSON format option
- Implement exponential backoff for retries
- Provide detailed error context for debugging
- Use health checks for monitoring daemon status

### Architecture Patterns
- Follow dependency injection patterns for testability
- Use factory patterns for device creation
- Implement observer patterns for device state changes  
- Use async context managers for resource management

### Testing Guidelines
- Mock Bluetooth devices for unit tests
- Use pytest-asyncio for async test support
- Implement integration tests with test containers
- Validate MQTT message formats and schemas

### Performance Considerations
- Batch MQTT messages when possible
- Use connection pooling for Bluetooth devices
- Implement proper resource cleanup
- Monitor memory usage with long-running processes

## MCP Integration Examples

### Getting Library Documentation
```python
# Before implementing MQTT features, fetch current docs:
# Use Context7 MCP to get paho-mqtt documentation
# Focus on: connection management, message publishing, error handling

# Before implementing BLE scanning, fetch current docs:
# Use Context7 MCP to get bleak documentation  
# Focus on: device discovery, notification handling, connection stability
```

### Staying Current with Best Practices
```python
# When adding new features, always check:
# 1. Latest library versions and breaking changes
# 2. Current security best practices
# 3. Performance optimization techniques
# 4. Docker and containerization updates

# Use Context7 MCP regularly to:
# - Validate implementation approaches
# - Check for deprecated patterns
# - Learn about new features and capabilities
# - Understand common pitfalls and solutions
```
```

#### VS Code Workspace Settings (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  
  "copilot.enable": {
    "*": true,
    "yaml": true,
    "dockerfile": true,
    "python": true
  },
  
  "github.copilot.advanced": {
    "debug.overrideEngine": "copilot-chat",
    "debug.useNodeDebugger": true
  },
  
  "files.associations": {
    "*.yaml": "yaml",
    "Dockerfile*": "dockerfile",
    ".env*": "properties"
  },
  
  "yaml.schemas": {
    "./config/config.schema.json": ["config/*.yaml", "config.yaml"]
  }
}
```

#### Development Environment Setup Instructions

```markdown
# Developer Setup with MCP Integration

## Prerequisites
1. Install VS Code with GitHub Copilot extension
2. Setup Context7 MCP server access
3. Configure Python environment with development dependencies

## MCP Server Configuration
Add to your VS Code or IDE settings to enable Context7 MCP:

```json
{
  "mcp.servers": {
    "context7": {
      "command": "npx",
      "args": ["@context7/mcp-server"],
      "env": {
        "CONTEXT7_API_KEY": "${env:CONTEXT7_API_KEY}"
      }
    }
  }
}
```

## Development Workflow
1. Before starting work on any component, use Context7 to fetch relevant documentation
2. Use GitHub Copilot for code generation with proper context
3. Validate implementations against current best practices
4. Test with real hardware when possible
5. Update documentation as you implement features

## Common MCP Queries for This Project
- "bleak bluetooth low energy connection patterns python"
- "paho mqtt client reconnection handling python" 
- "docker bluetooth device access raspberry pi"
- "asyncio error handling best practices"
- "home assistant mqtt discovery specification"
- "prometheus metrics python daemon monitoring"
```

## Future Enhancements

### Short-term (1-3 months)
- Web-based configuration interface
- Mobile app integration
- Additional sensor support
- Advanced alerting system

### Medium-term (3-6 months)
- Machine learning integration
- Predictive analytics
- Cloud backup
- Multi-tenant support

### Long-term (6+ months)
- Support for other BLE sensors
- Mesh networking support
- Edge computing capabilities
- Commercial licensing options

## Conclusion

This migration plan provides a comprehensive roadmap for transforming the existing Home Assistant integration into a robust, standalone Linux daemon. The containerized approach ensures easy deployment and maintenance, while the modular architecture allows for future enhancements and scalability.

Key benefits of this migration:
- **Independence**: No Home Assistant dependency
- **Performance**: Optimized for direct hardware access
- **Flexibility**: Configurable polling intervals and MQTT topics  
- **Reliability**: Robust error handling and recovery
- **Maintainability**: Clean, modular codebase
- **Scalability**: Support for multiple devices and deployment scenarios

The phased implementation approach allows for iterative development and testing, ensuring a smooth transition from the current Home Assistant integration to the new standalone daemon.