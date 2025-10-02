#!/usr/bin/env python3
"""
Test script for MQTT Publisher functionality.
Tests connection, publishing, and Home Assistant discovery.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mqtt_publisher import MQTTPublisher, MQTTConfig
from bluetooth_manager import SensorData


async def test_mqtt_connection():
    """Test basic MQTT connection."""
    print("🔗 Testing MQTT connection...")
    
    config = MQTTConfig(
        broker_host="localhost",
        broker_port=1883,
        client_id="mqtt-test-client"
    )
    
    publisher = MQTTPublisher(config)
    
    try:
        await publisher.start()
        
        if publisher.is_connected:
            print("✅ MQTT connection successful!")
            return publisher
        else:
            print("❌ MQTT connection failed!")
            return None
            
    except Exception as e:
        print(f"❌ MQTT connection error: {e}")
        return None


async def test_sensor_data_publishing(publisher: MQTTPublisher):
    """Test publishing sensor data."""
    print("\n📤 Testing sensor data publishing...")
    
    # Create mock sensor data
    test_data = SensorData(
        temperature=23.5,
        humidity=45.2,
        battery=78,
        last_seen=datetime.now()
    )
    
    test_device_id = "A4C138AAAAAA"  # Mock MAC without colons
    
    try:
        success = await publisher.publish_sensor_data(test_device_id, test_data)
        
        if success:
            print("✅ Sensor data published successfully!")
            print(f"   Device ID: {test_device_id}")
            print(f"   Data: {test_data.to_dict()}")
        else:
            print("❌ Failed to publish sensor data!")
            
    except Exception as e:
        print(f"❌ Publishing error: {e}")


async def test_home_assistant_discovery(publisher: MQTTPublisher):
    """Test Home Assistant discovery setup."""
    print("\n🏠 Testing Home Assistant discovery...")
    
    test_device_id = "A4C138AAAAAA"
    
    try:
        # This will be called automatically by publish_sensor_data
        # but we can test it directly here
        await publisher._setup_discovery(test_device_id)
        print("✅ Home Assistant discovery configured!")
        
    except Exception as e:
        print(f"❌ Discovery setup error: {e}")


async def test_mqtt_stats(publisher: MQTTPublisher):
    """Test getting publisher statistics."""
    print("\n📊 Testing MQTT statistics...")
    
    try:
        stats = publisher.get_stats()
        print("✅ Publisher statistics:")
        print(f"   Connected: {stats['connected']}")
        print(f"   Broker: {stats['broker']}")
        print(f"   Discovered devices: {stats['discovered_devices']}")
        print(f"   Device list: {stats['device_list']}")
        
    except Exception as e:
        print(f"❌ Stats error: {e}")


async def main():
    """Run all MQTT tests."""
    print("🧪 MQTT Publisher Test Suite")
    print("=" * 40)
    
    # Test 1: Connection
    publisher = await test_mqtt_connection()
    if not publisher:
        print("\n❌ Cannot continue tests without MQTT connection")
        return
    
    # Test 2: Publishing sensor data
    await test_sensor_data_publishing(publisher)
    
    # Test 3: Home Assistant discovery
    await test_home_assistant_discovery(publisher)
    
    # Test 4: Statistics
    await test_mqtt_stats(publisher)
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    await publisher.stop()
    print("✅ Test cleanup complete!")
    
    print("\n🎉 MQTT Publisher tests completed!")


if __name__ == "__main__":
    asyncio.run(main())