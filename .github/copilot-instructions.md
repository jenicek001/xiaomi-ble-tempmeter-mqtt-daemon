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
Prefer using `uvx` for ad‑hoc / development runs to avoid polluting the global Python environment.

To run the daemon with dependencies from the current project:

```bash
# Run with DEBUG logging
uvx --from . python -m src.main --log-level DEBUG

# Run with INFO logging (recommended for normal operation)
uvx --from . python -m src.main --log-level INFO
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
  "last_seen": "2025-09-27T09:28:01.921805+02:00", # TZ-aware local time
  "rssi": -70,
  "signal": "strong", # Signal strength (RSSI) interpretation
  "friendly_name": "Living Room", # (Optional) User-friendly name for the device if optionally defined in configuration
  "message_type": "periodic" # or "threshold-based" - periodic updates are sent at regular intervals regardless if values has changed
}
```

## Device Protocol
- **Handle 0x0038**: Enable notifications (temp/humidity/battery)
- **Handle 0x0046**: Device config (LYWSD03MMC only)
- **Data**: MiBeacon advertisements → temp(2), humidity(2), battery(1)
- **Battery**: Direct percentage value from MiBeacon packet (no voltage estimation)

## RSSI Implementation
- **Discovery**: RSSI captured during BLE advertisement scanning using callback-based approach
- **Caching**: Last known RSSI values stored in `_rssi_cache` dictionary per MAC address
- **Updates**: RSSI refreshed during device discovery (currently only at daemon startup)
- **Integration**: Cached RSSI included in SensorData objects and MQTT messages
- **Fallback**: Multiple methods attempted for RSSI retrieval from BLE backends
- **Interpretation**: RSSI values automatically converted to human-readable signal strength:
  - `excellent`: >= -50 dBm (< 2m, optimal)
  - `good`: -50 to -60 dBm (2-5m, reliable)
  - `fair`: -60 to -70 dBm (5-10m, acceptable)
  - `weak`: -70 to -80 dBm (10-20m, may have issues)
  - `very weak`: < -80 dBm (> 20m, poor connection)
  - `unknown`: RSSI not available

## Code Style
- Use type hints
- Implement proper error handling with exponential backoff
- Clean up resources in finally blocks
- Structure logging with context

## Coding Guidelines
- Follow PEP 8 for Python code style
- Use descriptive variable and function names
- Write unit tests for new features and bug fixes
- Keep functions small and focused on a single task

## Coding Agent
- Always use **context7** MCP server to get up-to-date documentation for any used libraries / packages / dependencies
- Use **brave-search** MCP server to search the Internet and forums for relevant information and experience
- Use **fetch** MCP server to access specific URLs
