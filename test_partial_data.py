#!/usr/bin/env python3
"""
Test script for partial data accumulation in hybrid daemon.

Validates that incomplete MiBeacon packets are properly cached
and only complete sensor readings are published.
"""

import asyncio
import sys
from pathlib import Path
import logging
from unittest.mock import AsyncMock, MagicMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sensor_cache import SensorCache, DeviceRecord
from bluetooth_manager import SensorData
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_device_record_partial_updates():
    """Test DeviceRecord partial data accumulation."""
    print("🧪 Testing DeviceRecord partial data accumulation...")
    
    device = DeviceRecord(mac_address="4C:65:A8:DB:99:44")
    
    # Test 1: Incomplete data should not allow publishing
    device.update_partial_data({'temperature': 23.5})
    assert not device.is_data_complete(), "Should not be complete with only temperature"
    assert not device.should_publish_immediately(), "Should not publish incomplete data"
    
    # Test 2: Add humidity, still incomplete without battery
    device.update_partial_data({'humidity': 45.2})
    assert not device.is_data_complete(), "Should not be complete without battery"
    assert not device.should_publish_immediately(), "Should not publish without battery"
    
    # Test 3: Add battery - now complete and should publish (first reading)
    device.update_partial_data({'battery': 78})
    assert device.is_data_complete(), "Should be complete with all three fields"
    assert device.should_publish_immediately(), "Should publish first complete reading"
    
    # Test 4: Mark as published, small change should not trigger immediate publish
    device.mark_published()
    device.update_partial_data({'temperature': 23.6})  # 0.1°C change
    assert not device.should_publish_immediately(temperature_threshold=0.2), "Small change should not trigger immediate publish"
    
    # Test 5: Large change should trigger immediate publish
    device.update_partial_data({'temperature': 24.0})  # 0.4°C change from published 23.5°C
    assert device.should_publish_immediately(temperature_threshold=0.2), "Large change should trigger immediate publish"
    
    print("✅ DeviceRecord tests passed")


def test_sensor_cache_partial_updates():
    """Test SensorCache with partial MiBeacon updates."""
    print("🧪 Testing SensorCache partial data handling...")
    
    config = {
        'temperature_threshold': 0.2,
        'humidity_threshold': 1.0,
        'publish_interval': 300,
        'static_devices': [
            {'mac': '4C:65:A8:DB:99:44', 'friendly_name': 'Living Room'}
        ]
    }
    
    cache = SensorCache(config)
    mac = "4C:65:A8:DB:99:44"
    
    # Test 1: Temperature-only packet should not trigger publishing
    immediate, periodic = cache.update_partial_sensor_data(mac, {'temperature': 23.5}, rssi=-70)
    assert not immediate, "Temperature-only should not trigger immediate publish"
    assert not periodic, "Incomplete data should not trigger periodic publish"
    
    # Test 2: Humidity packet should not trigger publishing yet
    immediate, periodic = cache.update_partial_sensor_data(mac, {'humidity': 45.2}, rssi=-68)
    assert not immediate, "Still incomplete without battery"
    assert not periodic, "Still incomplete without battery"
    
    # Test 3: Battery packet should now trigger immediate publish (first complete reading)
    immediate, periodic = cache.update_partial_sensor_data(mac, {'battery': 78}, rssi=-72)
    assert immediate, "First complete reading should trigger immediate publish"
    
    # Simulate publishing
    cache.mark_device_published(mac)
    
    # Test 4: Small temperature change should not trigger immediate publish
    immediate, periodic = cache.update_partial_sensor_data(mac, {'temperature': 23.6}, rssi=-71)
    assert not immediate, "Small change should not trigger immediate publish"
    
    # Test 5: Large humidity change should trigger immediate publish
    immediate, periodic = cache.update_partial_sensor_data(mac, {'humidity': 47.0}, rssi=-69)
    assert immediate, "Large humidity change should trigger immediate publish"
    
    print("✅ SensorCache tests passed")


async def test_realistic_mibeacon_sequence():
    """Test realistic MiBeacon packet sequence."""
    print("🧪 Testing realistic MiBeacon packet sequence...")
    
    config = {
        'temperature_threshold': 0.3,
        'humidity_threshold': 2.0,
        'publish_interval': 60,
        'static_devices': []
    }
    
    cache = SensorCache(config)
    mac = "4C:65:A8:D5:67:40"
    
    # Simulate real MiBeacon packet sequence
    packets = [
        {'temperature': 23.3},                    # Temperature-only packet
        {'humidity': 43.5},                       # Humidity-only packet  
        {'temperature': 23.4, 'humidity': 43.6}, # Combined packet
        {'battery': 55},                          # Battery-only packet
    ]
    
    publish_events = []
    
    for i, packet in enumerate(packets):
        immediate, periodic = cache.update_partial_sensor_data(mac, packet, rssi=-80+i)
        
        if immediate:
            publish_events.append(f"Packet {i+1}: {packet}")
            cache.mark_device_published(mac)
            
        device = cache.devices.get(mac.upper())
        logger.info(f"Packet {i+1}: {packet}")
        logger.info(f"  Complete: {device.is_data_complete() if device else False}")
        logger.info(f"  Immediate: {immediate}")
        
    # Should only publish once when battery data completes the dataset
    assert len(publish_events) == 1, f"Expected 1 publish event, got {len(publish_events)}: {publish_events}"
    assert "battery" in publish_events[0], "Should publish when battery completes the data"
    
    print("✅ Realistic MiBeacon sequence test passed")


def test_device_summary():
    """Test device summary with partial data."""
    print("🧪 Testing device summary...")
    
    config = {'temperature_threshold': 0.2, 'humidity_threshold': 1.0, 'publish_interval': 300, 'static_devices': []}
    cache = SensorCache(config)
    
    mac = "4C:65:A8:DC:84:01"
    cache.update_partial_sensor_data(mac, {'temperature': 22.8}, rssi=-75)
    cache.update_partial_sensor_data(mac, {'humidity': 38.9})
    
    summary = cache.get_device_summary()
    device_summary = summary[mac.upper()]
    
    assert not device_summary['is_complete'], "Should not be complete without battery"
    assert device_summary['cached_temperature'] == 22.8, "Should cache temperature"
    assert device_summary['cached_humidity'] == 38.9, "Should cache humidity"
    assert device_summary['cached_battery'] is None, "Battery should be None"
    assert not device_summary['has_published_once'], "Should not have published yet"
    
    # Complete the data
    cache.update_partial_sensor_data(mac, {'battery': 82})
    summary = cache.get_device_summary()
    device_summary = summary[mac.upper()]
    
    assert device_summary['is_complete'], "Should be complete with all fields"
    assert device_summary['cached_battery'] == 82, "Should cache battery"
    
    print("✅ Device summary test passed")


async def main():
    """Run all partial data tests."""
    print("🚀 Testing partial data accumulation system...\n")
    
    try:
        test_device_record_partial_updates()
        print()
        
        test_sensor_cache_partial_updates()
        print()
        
        await test_realistic_mibeacon_sequence()
        print()
        
        test_device_summary()
        print()
        
        print("✅ All partial data tests passed!")
        print("\n📝 Key improvements:")
        print("  - No invalid/incomplete sensor readings will be published")
        print("  - MiBeacon packets are accumulated until complete dataset is available")  
        print("  - First publication only happens when temperature + humidity + battery are all cached")
        print("  - Threshold-based publishing only works with complete data")
        print("  - Partial updates are logged but don't trigger MQTT messages")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)