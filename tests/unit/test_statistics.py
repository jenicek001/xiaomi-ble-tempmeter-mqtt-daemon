#!/usr/bin/env python3
"""Unit tests for statistics tracking feature."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.sensor_cache import ValueStatistics, DeviceRecord, SensorCache
from src.bluetooth_manager import SensorData
from datetime import datetime, timezone


def test_value_statistics():
    """Test ValueStatistics class."""
    print("\n=== Testing ValueStatistics ===")
    
    stats = ValueStatistics()
    
    # Add some values
    stats.add_value(23.5)
    stats.add_value(23.7)
    stats.add_value(23.2)
    stats.add_value(23.9)
    stats.add_value(23.4)
    
    print(f"Count: {stats.count} (expected: 5)")
    print(f"Min: {stats.min_value} (expected: 23.2)")
    print(f"Max: {stats.max_value} (expected: 23.9)")
    print(f"Avg: {stats.avg_value:.2f} (expected: 23.54)")
    
    assert stats.count == 5
    assert stats.min_value == 23.2
    assert stats.max_value == 23.9
    assert abs(stats.avg_value - 23.54) < 0.01
    
    # Test reset
    stats.reset()
    print(f"\nAfter reset:")
    print(f"Count: {stats.count} (expected: 0)")
    print(f"Min: {stats.min_value} (expected: None)")
    
    assert stats.count == 0
    assert stats.min_value is None
    
    print("✅ ValueStatistics tests passed!")


def test_device_record_statistics():
    """Test DeviceRecord statistics tracking."""
    print("\n=== Testing DeviceRecord Statistics ===")
    
    device = DeviceRecord(mac_address="AA:BB:CC:DD:EE:FF")
    
    # Simulate multiple sensor readings
    readings = [
        {'temperature': 23.5, 'humidity': 45.0, 'battery': 78},
        {'temperature': 23.7, 'humidity': 45.5, 'battery': 78},
        {'temperature': 23.2, 'humidity': 44.8, 'battery': 78},
        {'temperature': 23.9, 'humidity': 45.8, 'battery': 78},
        {'temperature': 23.4, 'humidity': 45.2, 'battery': 77},
    ]
    
    for reading in readings:
        device.update_partial_data(reading, rssi=-65)
    
    print(f"Temperature stats:")
    print(f"  Count: {device.temperature_stats.count}")
    print(f"  Min: {device.temperature_stats.min_value}")
    print(f"  Max: {device.temperature_stats.max_value}")
    print(f"  Avg: {device.temperature_stats.avg_value:.2f}")
    
    assert device.temperature_stats.count == 5
    assert device.temperature_stats.min_value == 23.2
    assert device.temperature_stats.max_value == 23.9
    
    print(f"\nHumidity stats:")
    print(f"  Count: {device.humidity_stats.count}")
    print(f"  Min: {device.humidity_stats.min_value}")
    print(f"  Max: {device.humidity_stats.max_value}")
    
    assert device.humidity_stats.count == 5
    assert device.humidity_stats.min_value == 44.8
    assert device.humidity_stats.max_value == 45.8
    
    # Get statistics
    stats = device.get_statistics()
    print(f"\nStatistics dict:")
    print(f"  Temperature: {stats['temperature']}")
    print(f"  Humidity: {stats['humidity']}")
    
    print("✅ DeviceRecord statistics tests passed!")


def test_cache_invalidation():
    """Test cache invalidation after publish."""
    print("\n=== Testing Cache Invalidation ===")
    
    device = DeviceRecord(mac_address="AA:BB:CC:DD:EE:FF")
    
    # Add some readings
    device.update_partial_data({'temperature': 23.5, 'humidity': 45.0, 'battery': 78}, rssi=-65)
    device.update_partial_data({'temperature': 23.7, 'humidity': 45.5, 'battery': 78}, rssi=-67)
    device.update_partial_data({'temperature': 23.2, 'humidity': 44.8, 'battery': 78}, rssi=-63)
    
    print(f"Before publish:")
    print(f"  Temperature count: {device.temperature_stats.count}")
    print(f"  Humidity count: {device.humidity_stats.count}")
    print(f"  RSSI count: {device.rssi_stats.count}")
    
    assert device.temperature_stats.count == 3
    assert device.humidity_stats.count == 3
    assert device.rssi_stats.count == 3
    
    # Mark as published (should invalidate cache)
    device.mark_published()
    
    print(f"\nAfter publish (cache invalidated):")
    print(f"  Temperature count: {device.temperature_stats.count}")
    print(f"  Humidity count: {device.humidity_stats.count}")
    print(f"  RSSI count: {device.rssi_stats.count}")
    
    assert device.temperature_stats.count == 0
    assert device.humidity_stats.count == 0
    assert device.rssi_stats.count == 0
    
    # But cached values should remain for threshold detection
    print(f"\nCached values (kept for threshold detection):")
    print(f"  Temperature: {device.cached_temperature}")
    print(f"  Humidity: {device.cached_humidity}")
    print(f"  Battery: {device.cached_battery}")
    
    assert device.cached_temperature == 23.2
    assert device.cached_humidity == 44.8
    assert device.cached_battery == 78
    
    print("✅ Cache invalidation tests passed!")


def test_sensor_data_with_statistics():
    """Test SensorData with statistics in JSON."""
    print("\n=== Testing SensorData with Statistics ===")
    
    # Create statistics
    stats = {
        'temperature': {'count': 10, 'min': 22.5, 'max': 23.8, 'avg': 23.2},
        'humidity': {'count': 10, 'min': 44.0, 'max': 46.5, 'avg': 45.1},
        'battery': {'count': 2, 'min': 77, 'max': 78, 'avg': 77.5},
        'rssi': {'count': 10, 'min': -70, 'max': -60, 'avg': -65.5}
    }
    
    # Create sensor data
    sensor_data = SensorData(
        temperature=23.5,
        humidity=45.2,
        battery=78,
        last_seen=datetime.now(tz=timezone.utc).astimezone(),
        rssi=-65,
        statistics=stats
    )
    
    # Convert to dict
    data_dict = sensor_data.to_dict(friendly_name="Test Room", message_type="periodic")
    
    print(f"JSON output (formatted):")
    import json
    print(json.dumps(data_dict, indent=2))
    
    # Verify statistics are in output
    assert 'temperature_count' in data_dict
    assert 'temperature_min' in data_dict
    assert 'temperature_max' in data_dict
    assert 'temperature_avg' in data_dict
    
    assert data_dict['temperature_count'] == 10
    assert data_dict['temperature_min'] == 22.5
    assert data_dict['temperature_max'] == 23.8
    assert data_dict['temperature_avg'] == 23.2
    
    assert 'humidity_count' in data_dict
    assert 'rssi_avg' in data_dict
    
    print("✅ SensorData with statistics tests passed!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Statistics Feature Unit Tests")
    print("=" * 60)
    
    try:
        test_value_statistics()
        test_device_record_statistics()
        test_cache_invalidation()
        test_sensor_data_with_statistics()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
