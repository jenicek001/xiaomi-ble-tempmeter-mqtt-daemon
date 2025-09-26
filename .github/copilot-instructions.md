# GitHub Copilot Instructions

## Project Overview
Standalone Python daemon for Xiaomi Mijia BLE thermometers. Reads sensor data via Bluetooth and publishes to MQTT with Home Assistant discovery.

## Key Libraries
- **bleak**: Async BLE communication
- **paho-mqtt**: MQTT client
- **pydantic**: Configuration validation
- **asyncio**: Async patterns throughout
- **python-dotenv**: Load environment variables from .env

## Running Ephemerally With uvx
Prefer using `uvx` for ad‑hoc / development runs to avoid polluting the global Python environment. Two common patterns:

```
uvx --from bleak --with paho-mqtt --with pydantic --with pyyaml --with python-dotenv python -m src.main --log-level DEBUG
```

Or, to honor the pinned versions in `requirements.txt` while still being ephemeral:

```
uvx --script requirements.txt python -m src.main
```

Guidelines:
- Add any new persistent dependency to `requirements.txt`; keep dev/test extras in `requirements-dev.txt`.
- Use `uvx` for local testing / CI one‑shot executions. For deployment (container, service unit) install from `requirements.txt` inside the isolated environment (virtualenv/container layer), not system‑wide.
- Do NOT `pip install` globally on the host; always rely on ephemeral or virtual environments.

When editing automation (Makefile, CI), prefer a target that shells out through `uvx` so contributors only need the `uv` binary plus build tools.

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
  "voltage": 1.2,
  "last_seen": "2025-09-26T10:30:45Z",
  "rssi": -70,
  "signal": "strong"
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