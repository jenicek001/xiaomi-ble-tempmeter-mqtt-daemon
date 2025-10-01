# RSSI Signal Strength Interpretation - Proposal

## Background

Based on research of Bluetooth Low Energy (BLE) RSSI standards and industry best practices, this document proposes a human-readable interpretation system for RSSI (Received Signal Strength Indicator) values in our Xiaomi BLE thermometer daemon.

## Research Summary

RSSI is measured in dBm (decibel-milliwatts) and represents the power level of a received Bluetooth signal:
- **Values are negative** - closer to 0 means stronger signal
- **Typical BLE range**: -26 dBm (few inches) to -100 dBm (40-50m distance)
- **Broadcasting power**: Xiaomi sensors typically use 2-4 dBm transmission power

### Industry Standards (Sources: Ruijie Networks, MetaGeek, mokoblue)

| RSSI Range (dBm) | Quality Level | Description |
|------------------|---------------|-------------|
| > -30 | Too Strong | Device too close, may cause signal saturation/distortion |
| -30 to -67 | Excellent | High data rates, optimal performance, no issues expected |
| -67 to -70 | Good | Reliable for most applications (VoIP, streaming, gaming) |
| -70 to -80 | Fair | Usable but may experience some interference or reduced rates |
| -80 to -90 | Weak | Minimal reliability, packet loss likely, poor performance |
| < -90 | Very Weak | At edge of receivability, dropped connections likely |

## Proposed Implementation

### Option 1: Conservative Ranges (Recommended for Indoor Use)

Optimized for indoor environments with typical interference (walls, furniture, other devices):

```python
def interpret_rssi(rssi: Optional[int]) -> str:
    """
    Interpret RSSI value into human-readable signal strength.
    Optimized for indoor Bluetooth Low Energy applications.
    
    Args:
        rssi: RSSI value in dBm (negative integer)
        
    Returns:
        Human-readable signal strength description
    """
    if rssi is None:
        return "unknown"
    
    if rssi >= -50:
        return "excellent"
    elif rssi >= -60:
        return "good"
    elif rssi >= -70:
        return "fair"
    elif rssi >= -80:
        return "weak"
    else:
        return "very weak"
```

**Rationale**: 
- Indoor BLE typically sees -50 to -90 dBm range
- Conservative thresholds account for obstacles and interference
- Aligns with Home Assistant sensor placement (usually < 10m from receiver)

### Option 2: Standard Ranges (Industry Baseline)

Based on general wireless networking standards:

```python
def interpret_rssi(rssi: Optional[int]) -> str:
    """
    Interpret RSSI value using industry-standard ranges.
    
    Args:
        rssi: RSSI value in dBm (negative integer)
        
    Returns:
        Human-readable signal strength description
    """
    if rssi is None:
        return "unknown"
    
    if rssi >= -67:
        return "excellent"
    elif rssi >= -70:
        return "good"
    elif rssi >= -80:
        return "fair"
    elif rssi >= -90:
        return "weak"
    else:
        return "very weak"
```

### Option 3: Extended Range with Distance Estimates

Provides additional context about approximate distance:

```python
def interpret_rssi_extended(rssi: Optional[int]) -> tuple[str, str]:
    """
    Interpret RSSI with quality level and approximate distance.
    
    Args:
        rssi: RSSI value in dBm (negative integer)
        
    Returns:
        Tuple of (quality_level, distance_estimate)
    """
    if rssi is None:
        return ("unknown", "unknown")
    
    if rssi >= -50:
        return ("excellent", "< 2m")
    elif rssi >= -60:
        return ("good", "2-5m")
    elif rssi >= -70:
        return ("fair", "5-10m")
    elif rssi >= -80:
        return ("weak", "10-20m")
    elif rssi >= -90:
        return ("very weak", "20-40m")
    else:
        return ("critical", "> 40m")
```

## Recommendation

**Use Option 1 (Conservative Ranges)** for the following reasons:

1. **Indoor Focus**: Our use case is indoor home/office monitoring, typically 3-15m range
2. **Practical Thresholds**: -50 dBm threshold for "excellent" is realistic for indoor BLE
3. **User Expectations**: Aligns with what users see in practice with Xiaomi sensors
4. **Actionable Feedback**: Clear distinction between good placement and problematic placement

## Integration Points

### 1. Update `bluetooth_manager.py` Constants

Add the interpretation function:

```python
def interpret_rssi(rssi: Optional[int]) -> str:
    """Interpret RSSI value into human-readable signal strength."""
    if rssi is None:
        return "unknown"
    if rssi >= -50:
        return "excellent"
    elif rssi >= -60:
        return "good"
    elif rssi >= -70:
        return "fair"
    elif rssi >= -80:
        return "weak"
    else:
        return "very weak"
```

### 2. Include in MQTT Messages

The `signal` field already exists in `SensorData` - ensure it uses this interpretation:

```python
@dataclass
class SensorData:
    temperature: float
    humidity: float
    battery: int
    last_seen: datetime
    rssi: Optional[int] = None
    
    @property
    def signal(self) -> str:
        """Human-readable signal strength interpretation."""
        return interpret_rssi(self.rssi)
```

### 3. Update Discovery Logging

Enhance device discovery messages with signal quality:

```python
logger.info(
    f"Found Xiaomi device: {device.address} "
    f"(RSSI: {rssi} dBm, Signal: {interpret_rssi(rssi)})"
)
```

### 4. Add to Home Assistant Discovery

Include RSSI as a diagnostic sensor:

```json
{
  "name": "Living Room Signal Strength",
  "state_topic": "mijiableht/4C65A8DB9944/state",
  "value_template": "{{ value_json.signal }}",
  "icon": "mdi:signal",
  "entity_category": "diagnostic"
}
```

## Testing Recommendations

1. **Baseline Testing**: Place sensor at various distances (1m, 3m, 5m, 10m) and record RSSI
2. **Obstacle Testing**: Test with walls, furniture between sensor and receiver
3. **Threshold Validation**: Verify thresholds match practical signal quality experience
4. **Edge Case**: Test at maximum range where signal becomes unreliable

## Future Enhancements

1. **Adaptive Thresholds**: Learn optimal thresholds based on environment
2. **Signal Trend Analysis**: Track RSSI over time to detect degradation
3. **Placement Recommendations**: Suggest better sensor placement if signal is weak
4. **Alert Integration**: Notify when signal quality drops below acceptable threshold

## References

- Ruijie Networks: "What is a good RSSI Signal Strength"
- mokoblue: "Understanding the Measures of Bluetooth RSSI"
- MetaGeek: "Understanding RSSI Levels"
- Bluetooth.com: "Distance and RSSI"
- Industry research shows typical BLE range: -26 dBm (close) to -100 dBm (50m)
