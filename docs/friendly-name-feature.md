# Friendly Name Feature

## Overview
The daemon now supports optional friendly names for devices configured in `config.yaml`. When a friendly name is set, it will be included in all MQTT messages published for that device.

## Configuration

### YAML Configuration
Add friendly names to your static devices in `config/config.yaml`:

```yaml
devices:
  auto_discovery: true
  static_devices:
    - mac: "4C:65:A8:DC:84:01"
      friendly_name: "Living Room"
    - mac: "4C:65:A8:DB:99:44"
      friendly_name: "Bedroom"
    - mac: "4C:65:A8:D5:67:40"
      # friendly_name is optional - device will work without it
```

### Notes
- The `mac` field is required for each device
- The `friendly_name` field is optional
- Friendly names can contain any UTF-8 characters (including non-ASCII)
- Devices without friendly names will work normally (friendly_name field won't appear in MQTT messages)

## MQTT Message Format

### Without Friendly Name
```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-10-01T21:30:00+02:00",
  "rssi": -70,
  "signal": "fair",
  "message_type": "periodic"
}
```

### With Friendly Name
```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-10-01T21:30:00+02:00",
  "rssi": -70,
  "signal": "fair",
  "message_type": "periodic",
  "friendly_name": "Living Room"
}
```

## Message Types

The `message_type` field indicates why the message was published:
- **`periodic`**: Regular interval-based update (configured via `mqtt.publish_interval`)
- **`threshold-based`**: Immediate update triggered by significant sensor value change (configured via `thresholds.temperature` and `thresholds.humidity`)

## Implementation Details

### Modified Components

1. **config_manager.py**
   - Added `StaticDeviceModel` with `mac` (required) and `friendly_name` (optional) fields
   - Updated `DevicesConfigModel` to use typed list of `StaticDeviceModel`

2. **bluetooth_manager.py**
   - Updated `SensorData.to_dict()` to accept optional `friendly_name` and `message_type` parameters
   - Friendly name is only included in output if provided

3. **sensor_cache.py**
   - Already supported friendly names via `DeviceRecord.friendly_name`
   - Updated `_load_friendly_names()` to handle both dict and Pydantic model objects

4. **mqtt_publisher.py**
   - Updated `publish_sensor_data_with_name()` to use new `SensorData.to_dict()` signature
   - Passes `friendly_name` and `reason` (message type) to the sensor data

5. **main.py**
   - Updated `_handle_sensor_data()` to retrieve friendly name from device cache
   - Passes friendly name to MQTT publisher when publishing data
   - Converts `StaticDeviceModel` instances to dicts for backward compatibility

## Use Cases

### Home Assistant
Friendly names make it easier to identify devices in automations and UI:

```yaml
automation:
  - alias: "Alert if bedroom too cold"
    trigger:
      - platform: mqtt
        topic: "mijiableht/4C65A8DB9944/state"
    condition:
      - condition: template
        value_template: "{{ trigger.payload_json.friendly_name == 'Bedroom' and trigger.payload_json.temperature < 18 }}"
    action:
      - service: notify.mobile_app
        data:
          message: "Bedroom temperature is {{ trigger.payload_json.temperature }}°C"
```

### Custom MQTT Consumers
Any consumer can easily identify devices by their friendly name without maintaining a separate MAC-to-name mapping:

```python
import json
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    name = data.get('friendly_name', 'Unknown')
    temp = data['temperature']
    print(f"{name}: {temp}°C")
```

## Testing

Run the included test script to verify the functionality:

```bash
uvx --from . python test_friendly_name.py
```

This will:
1. Load and validate the configuration
2. Verify friendly names are properly loaded into the sensor cache
3. Test the `SensorData.to_dict()` method with and without friendly names
4. Confirm message_type field is correctly set

## Backward Compatibility

- Devices without configured friendly names work exactly as before
- The `friendly_name` field is only added to MQTT messages when configured
- Existing MQTT consumers will continue to work (they can ignore the new field)
- Configuration files without `friendly_name` fields are still valid
