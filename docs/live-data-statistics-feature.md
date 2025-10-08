# Live Data Reporting with Statistics Feature

**Issue**: #2  
**Pull Request**: #3  
**Branch**: `feature/live-data-statistics`  
**Status**: Implemented, awaiting testing

## Overview

This feature implements comprehensive statistics tracking and cache invalidation to ensure only live, fresh data is reported via MQTT. It addresses the concern that recipients (like Grafana) might consider outdated sensor values as valid if they don't validate the `last_seen` timestamp.

## Problem Statement

The original implementation had these limitations:
1. Cached values were retained between MQTT publishes
2. No validation mechanism for data freshness
3. No visibility into sensor fluctuations between publish intervals
4. Single point-in-time readings didn't reflect data quality

## Solution

### 1. Statistics Tracking

Track min/max/avg/count for each sensor value type between MQTT publishes:
- **Temperature**: Min, Max, Average, Count
- **Humidity**: Min, Max, Average, Count  
- **Battery**: Min, Max, Average, Count
- **RSSI**: Min, Max, Average, Count

**Implementation**: New `ValueStatistics` dataclass in `sensor_cache.py`

```python
@dataclass
class ValueStatistics:
    count: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sum_value: float = 0.0
    
    @property
    def avg_value(self) -> Optional[float]:
        return self.sum_value / self.count if self.count > 0 else None
```

### 2. Cache Invalidation

After each MQTT publish:
- Reset all statistics counters (count, min, max, sum)
- Keep most recent sensor values for threshold detection
- Ensure next publish contains only fresh data

**Implementation**: Updated `mark_published()` method in `DeviceRecord`

### 3. Extended MQTT Message Format

Original message:
```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-09-26T10:30:45+02:00",
  "rssi": -65,
  "signal": "good",
  "message_type": "periodic"
}
```

New message with statistics:
```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "battery": 78,
  "last_seen": "2025-09-26T10:30:45+02:00",
  "rssi": -65,
  "signal": "good",
  "message_type": "periodic",
  "friendly_name": "Living Room",
  "temperature_count": 25,
  "temperature_min": 23.2,
  "temperature_max": 23.7,
  "temperature_avg": 23.45,
  "humidity_count": 25,
  "humidity_min": 44.8,
  "humidity_max": 45.6,
  "humidity_avg": 45.15,
  "battery_count": 5,
  "battery_min": 78,
  "battery_max": 78,
  "battery_avg": 78.0,
  "rssi_count": 25,
  "rssi_min": -68,
  "rssi_max": -62,
  "rssi_avg": -65.2
}
```

### 4. Home Assistant Discovery

Added 8 new sensor entities per device:
- `temperature_min` - Minimum temperature in period
- `temperature_max` - Maximum temperature in period
- `temperature_avg` - Average temperature in period
- `humidity_min` - Minimum humidity in period
- `humidity_max` - Maximum humidity in period
- `humidity_avg` - Average humidity in period
- `temperature_count` - Number of temperature readings
- `humidity_count` - Number of humidity readings

Total: **11 sensors per device** (3 primary + 8 statistics)

## Technical Changes

### Files Modified

1. **src/sensor_cache.py**
   - Added `ValueStatistics` class for tracking statistics
   - Updated `DeviceRecord` with statistics fields
   - Modified `update_partial_data()` to track statistics
   - Enhanced `mark_published()` to reset statistics
   - Added `get_statistics()` method
   - Updated `create_complete_sensor_data()` to include statistics

2. **src/bluetooth_manager.py**
   - Extended `SensorData` dataclass with `statistics` field
   - Updated `to_dict()` to include statistical fields in JSON

3. **src/mqtt_publisher.py**
   - Added discovery configs for 8 new statistic sensors
   - Updated `_setup_discovery()` with new sensor definitions
   - Modified `remove_device_discovery()` to clean up statistic sensors
   - Made `device_class` optional for statistic sensors

4. **README.md**
   - Documented new MQTT message format with examples
   - Added explanation of statistics feature
   - Updated Home Assistant discovery section
   - Added RSSI signal interpretation guide

## Benefits

### 1. Data Quality Assurance
- **Count field** shows how many readings were collected
- Helps identify sensor communication issues
- Provides confidence in data reliability

### 2. Fluctuation Detection
- **Min/Max values** reveal sensor stability
- Detect temperature/humidity spikes or drops
- Better understanding of environmental changes

### 3. Fresh Data Guarantee
- Cache invalidation prevents stale data
- Recipients can trust published values are current
- Reduces risk of acting on outdated readings

### 4. Backward Compatibility
- Existing fields remain unchanged
- Statistics are additive, not replacing
- Consumers can ignore statistics if not needed

## Usage Examples

### Grafana Dashboard

With statistics, you can create more informative visualizations:

```sql
-- Temperature with min/max bands
SELECT 
  time,
  temperature,
  temperature_min,
  temperature_max
FROM sensor_data
```

### Home Assistant Automation

```yaml
automation:
  - alias: "Alert on temperature spike"
    trigger:
      platform: mqtt
      topic: "mijiableht/A4C138123456/state"
    condition:
      condition: template
      value_template: >
        {{ (trigger.payload_json.temperature_max - 
            trigger.payload_json.temperature_min) > 2.0 }}
    action:
      service: notify.mobile_app
      data:
        message: "Large temperature fluctuation detected!"
```

### Node-RED Flow

```javascript
// Check data quality
if (msg.payload.temperature_count < 10) {
    node.warn("Low reading count - sensor may be losing connection");
}

// Detect anomalies
const range = msg.payload.temperature_max - msg.payload.temperature_min;
if (range > 3.0) {
    node.warn("Unusual temperature fluctuation: " + range + "°C");
}
```

## Configuration

No configuration changes required. Statistics are automatically collected and published.

**Default behavior**:
- Statistics collected between MQTT publishes (default: 5 minutes)
- Automatic cache invalidation after each publish
- All statistics included in every MQTT message

## Testing

### Syntax Validation
✅ All Python files compile without errors

### Unit Testing
⚠️ Real device testing pending (requires physical Xiaomi sensors)

### Integration Testing Plan
1. Deploy daemon with real sensors
2. Monitor MQTT messages for 30 minutes
3. Verify statistics are correctly calculated
4. Confirm cache invalidation after each publish
5. Check Home Assistant sensor creation

## Performance Impact

- **Memory**: Minimal (~200 bytes per device for statistics)
- **CPU**: Negligible (simple arithmetic operations)
- **MQTT Payload**: Increased by ~200-300 bytes per message
- **Network**: Slightly larger messages, same frequency

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Statistics**
   - Allow disabling statistics per sensor type
   - Configurable retention/reset intervals

2. **Additional Metrics**
   - Standard deviation calculation
   - Median value tracking
   - Outlier detection

3. **Historical Statistics**
   - Track statistics over longer periods
   - Persist statistics to database
   - Trend analysis

4. **Alerting**
   - Built-in anomaly detection
   - Threshold-based alerts
   - Pattern recognition

## Migration Guide

No migration required. The feature is additive and backward compatible:

1. Update to latest code
2. Restart daemon
3. Statistics automatically start collecting
4. New Home Assistant entities appear automatically

Existing consumers can continue using original fields without modification.

## Troubleshooting

### Statistics Not Appearing

**Check MQTT messages**:
```bash
mosquitto_sub -h <broker> -t "mijiableht/+/state" -v
```

Expected output should include `temperature_count`, `temperature_min`, etc.

### Home Assistant Entities Not Created

1. Check MQTT discovery prefix matches HA configuration
2. Verify MQTT integration is enabled in HA
3. Check HA logs for discovery errors
4. Manually trigger discovery by restarting daemon

### Incorrect Statistics

1. Verify sensor is sending data regularly
2. Check daemon logs for parsing errors
3. Confirm publish interval is set correctly
4. Monitor cache invalidation in debug logs

## References

- Issue: https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/issues/2
- Pull Request: https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/pull/3
- Commit: 23a5870

## Authors

- Implementation: GitHub Copilot
- Review: Pending
- Testing: Pending
