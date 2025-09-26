# Step 3: MQTT Publisher Component - Implementation Documentation

## Overview

This document details the implementation of the MQTT publisher component for the Xiaomi Mijia BLE daemon. The MQTT publisher handles communication with MQTT brokers and implements Home Assistant MQTT Discovery protocol for automatic sensor entity creation.

## Implementation Status: ✅ COMPLETED

### Key Components

#### 1. MQTTConfig Dataclass

- **Purpose**: Configuration management for MQTT connections
- **Features**:
  - Broker connection settings (host, port, authentication)
  - Client configuration (ID, keepalive, QoS)
  - Home Assistant discovery prefix customization

#### 2. MQTTPublisher Class  

- **Purpose**: Core MQTT publishing functionality
- **Features**:
  - Async connection management with paho-mqtt
  - Home Assistant MQTT Discovery support
  - Single JSON message per device (consolidated approach)
  - Automatic discovery setup and cleanup
  - Connection status monitoring and stats

### MQTT Topic Structure

Following the improved single-message approach:

```JSON
# State topic (single JSON message with all sensor data)
mijiableht/{device_id}/state
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-01-14T10:30:45Z"
}

# Discovery topics (Home Assistant auto-configuration)
homeassistant/sensor/mijiableht_{device_id}_temperature/config
homeassistant/sensor/mijiableht_{device_id}_humidity/config  
homeassistant/sensor/mijiableht_{device_id}_battery/config
```

### Home Assistant Discovery Configuration

Each sensor creates a discovery configuration with:

- **Device Information**: Manufacturer, model, identifiers
- **Value Templates**: JSON path extraction from state topic
- **Device Classes**: Proper HA sensor classification
- **Availability**: Based on last_seen timestamp
- **Expiration**: 15-minute timeout for stale data

### Key Methods

#### `async start()`

- Establishes MQTT broker connection
- Configures authentication if provided
- Sets up event callbacks for connection status
- Starts background network loop

#### `async publish_sensor_data(device_id, data)`

- Ensures Home Assistant discovery is configured
- Publishes sensor data as single JSON message
- Returns success/failure status
- Handles connection errors gracefully

#### `async _setup_discovery(device_id)`

- One-time setup per device for HA discovery
- Creates temperature, humidity, and battery sensors
- Configures proper value templates and device classes
- Tracks discovered devices to avoid duplicate setup

#### `async remove_device_discovery(device_id)`

- Removes Home Assistant discovery configuration
- Publishes empty payloads to discovery topics
- Cleans up internal tracking

### Integration with Main Daemon

The MQTT publisher integrates seamlessly with the main daemon:

1. **Initialization**: Creates MQTTConfig from configuration and starts publisher
2. **Data Publishing**: Converts MAC addresses to device IDs and publishes sensor data
3. **Cleanup**: Graceful shutdown with connection cleanup

### Error Handling

- Connection retry logic with exponential backoff
- Graceful handling of publish failures
- Comprehensive logging for troubleshooting
- Status monitoring and statistics

### Testing

Comprehensive test suite includes:

- **Unit Tests**: All methods and error conditions
- **Integration Tests**: Complete publish flow simulation
- **Mock Testing**: Isolated testing without MQTT broker
- **Manual Testing**: Real MQTT broker integration script

### Configuration Example

```python
mqtt_config = MQTTConfig(
    broker_host="mqtt.home.local",
    broker_port=1883,
    username="homeassistant",
    password="secret123",
    client_id="mijia-ble-daemon",
    qos=0,
    retain=True,
    discovery_prefix="homeassistant"
)
```

### Files Created/Modified

- ✅ `src/mqtt_publisher.py` - Complete MQTT publisher implementation
- ✅ `tests/test_mqtt_publisher.py` - Comprehensive test suite
- ✅ `src/main.py` - Integration with main daemon
- ✅ `src/constants.py` - Updated MQTT configuration and topics
- ✅ `test_mqtt.py` - Manual testing script

### Performance Characteristics

- **Single JSON Message**: More efficient than separate topics
- **Discovery Caching**: One-time setup per device reduces MQTT traffic
- **Async Operations**: Non-blocking MQTT operations
- **Memory Efficient**: Minimal state tracking

### Next Steps

With Step 3 completed, the daemon now has:

- ✅ BLE communication (Step 2)
- ✅ MQTT publishing with HA discovery (Step 3)

Ready to proceed with:

- Step 4: Configuration management system
- Step 5: Enhanced daemon orchestration
- Step 6: Docker containerization

The MQTT publisher provides a solid foundation for Home Assistant integration while maintaining flexibility for other MQTT use cases.
