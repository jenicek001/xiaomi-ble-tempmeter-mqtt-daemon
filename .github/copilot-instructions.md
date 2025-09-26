# GitHub Copilot Instructions

## Project Overview
Standalone Python daemon for Xiaomi Mijia BLE thermometers. Reads sensor data via Bluetooth and publishes to MQTT with Home Assistant discovery.

## Key Libraries
- **bleak**: Async BLE communication
- **paho-mqtt**: MQTT client
- **pydantic**: Configuration validation
- **asyncio**: Async patterns throughout

## Core Patterns

### Always use async/await
```python
async with BleakClient(mac_address) as client:
    await client.start_notify(handle, callback)
```

### Configuration with Pydantic
```python
class Config(BaseSettings):
    mqtt_broker: str
    poll_interval: int = 300
    
    class Config:
        env_prefix = "MIJIA_"
```

### MQTT Topics
```
mijiableht/{device_id}/state                         # Single JSON message with all sensor data
homeassistant/sensor/mijiableht_{device_id}_temp/config    # Discovery for temperature
homeassistant/sensor/mijiableht_{device_id}_humidity/config # Discovery for humidity  
homeassistant/sensor/mijiableht_{device_id}_battery/config  # Discovery for battery
```

### JSON Message Format
```json
{
  "temperature": 23.5,
  "humidity": 45.2, 
  "battery": 78,
  "last_seen": "2025-09-26T10:30:45Z"
}
```

## Device Protocol
- **Handle 0x0038**: Enable notifications (temp/humidity/battery)
- **Handle 0x0046**: Device config (LYWSD03MMC only) 
- **Data**: 5 bytes → temp(2), humidity(1), battery(2)
- **Battery calc**: `min(int(round((voltage - 2.1), 2) * 100), 100)`

## Code Style
- Use type hints
- Implement proper error handling with exponential backoff
- Clean up resources in finally blocks
- Structure logging with context