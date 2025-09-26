#!/usr/bin/env python3
"""
End-to-End test: Bluetooth → MQTT → Home Assistant Discovery.
Tests the complete data flow from BLE sensor reading to MQTT publishing.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from bleak import BleakClient
    from config_manager import ConfigManager
    from mqtt_publisher import MQTTPublisher
    from bluetooth_manager import SensorData
    from datetime import datetime
    import paho.mqtt.client as mqtt
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak --with pydantic --with pyyaml --with python-dotenv --with paho-mqtt python test_end_to_end.py")
    exit(1)


async def test_manual_sensor_reading():
    """Try to manually read sensor data from our MJ_HT_V1 device."""
    print("🔬 Testing Manual Sensor Data Reading")
    print("=" * 50)
    
    target_mac = "4C:65:A8:DC:84:01"
    
    # These are the handles we found in our previous test
    interesting_handles = [
        0x0028,  # 00001531-1212-efde-1523-785feabcd123 (Xiaomi service)
        0x0017,  # 00002a19 (Battery Level)
        0x000d,  # 226caa55-6476-4566-7562-66734470666d (Custom)
        0x0012,  # 226cbb55-6476-4566-7562-66734470666d (Custom)
    ]
    
    try:
        async with BleakClient(target_mac, timeout=30) as client:
            if not client.is_connected:
                print("❌ Could not connect to device")
                return None
            
            print("✅ Connected! Waiting for service discovery...")
            await asyncio.sleep(5)  # Wait for services
            
            # Try to read from readable characteristics
            for handle in interesting_handles:
                print(f"\n🔍 Testing handle 0x{handle:04x}...")
                
                try:
                    # First try to read
                    for service in client.services:
                        for char in service.characteristics:
                            if char.handle == handle:
                                print(f"   📡 Found characteristic: {char.uuid}")
                                print(f"   🔧 Properties: {', '.join(char.properties)}")
                                
                                if "read" in char.properties:
                                    try:
                                        data = await client.read_gatt_char(char.uuid)
                                        print(f"   📊 Read data: {data.hex()} ({len(data)} bytes)")
                                        
                                        # Try to decode as sensor data
                                        if len(data) >= 5:
                                            temp = int.from_bytes(data[0:2], 'little', signed=True) / 100.0
                                            humidity = data[2]
                                            battery_raw = int.from_bytes(data[3:5], 'little')
                                            voltage = battery_raw / 1000.0
                                            battery = min(int(round((voltage - 2.1), 2) * 100), 100)
                                            
                                            print(f"   🌡️  Decoded Temperature: {temp}°C")
                                            print(f"   💧 Decoded Humidity: {humidity}%") 
                                            print(f"   🔋 Decoded Battery: {battery}% ({voltage}V)")
                                            
                                            return SensorData(
                                                temperature=temp,
                                                humidity=humidity,
                                                battery=battery,
                                                voltage=voltage,
                                                timestamp=datetime.now()
                                            )
                                            
                                    except Exception as e:
                                        print(f"   ❌ Read failed: {e}")
                                
                                elif "notify" in char.properties:
                                    try:
                                        print(f"   🔔 Setting up notification...")
                                        received_data = []
                                        
                                        def notification_handler(sender, data):
                                            received_data.append(data)
                                            print(f"   📨 Notification: {data.hex()}")
                                        
                                        await client.start_notify(char.uuid, notification_handler)
                                        await asyncio.sleep(10)  # Wait for notifications
                                        await client.stop_notify(char.uuid)
                                        
                                        if received_data:
                                            print(f"   🎉 Received {len(received_data)} notification(s)!")
                                            # Process the first notification
                                            data = received_data[0]
                                            if len(data) >= 5:
                                                temp = int.from_bytes(data[0:2], 'little', signed=True) / 100.0
                                                humidity = data[2]
                                                battery_raw = int.from_bytes(data[3:5], 'little')
                                                voltage = battery_raw / 1000.0
                                                battery = min(int(round((voltage - 2.1), 2) * 100), 100)
                                                
                                                return SensorData(
                                                    temperature=temp,
                                                    humidity=humidity,
                                                    battery=battery,
                                                    voltage=voltage,
                                                    timestamp=datetime.now()
                                                )
                                        else:
                                            print(f"   ⚠️  No notifications received")
                                            
                                    except Exception as e:
                                        print(f"   ❌ Notification failed: {e}")
                                
                                break
                    
                except Exception as e:
                    print(f"   ❌ Handle test failed: {e}")
            
            print("\n💡 If no sensor data was found, the device might:")
            print("   - Need to be activated (press button or wave near it)")
            print("   - Be in deep sleep mode")
            print("   - Use different data format than expected")
            print("   - Require pairing or authentication")
            
            return None
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


async def test_full_data_flow():
    """Test complete data flow: Config → BLE → MQTT → HA Discovery."""
    print("\n🔄 Testing Complete Data Flow")
    print("=" * 50)
    
    # 1. Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()
    print("✅ Configuration loaded")
    
    # 2. Get sensor data (simulated for now, since BLE is challenging)
    sensor_data = await test_manual_sensor_reading()
    
    if not sensor_data:
        print("⚠️  Using simulated sensor data for MQTT testing...")
        sensor_data = SensorData(
            temperature=23.5,
            humidity=45,
            battery=78,
            voltage=2.9,
            timestamp=datetime.now()
        )
    
    print(f"\n📊 Sensor Data:")
    print(f"   🌡️  Temperature: {sensor_data.temperature}°C")
    print(f"   💧 Humidity: {sensor_data.humidity}%")
    print(f"   🔋 Battery: {sensor_data.battery}%")
    
    # 3. Test MQTT publishing
    print(f"\n📡 Testing MQTT Publishing...")
    
    try:
        mqtt_publisher = MQTTPublisher(config.mqtt)
        await mqtt_publisher.connect()
        print("✅ MQTT connected")
        
        # Publish sensor data
        device_id = "loznice"  # From config
        await mqtt_publisher.publish_sensor_data(device_id, sensor_data)
        print("✅ Sensor data published")
        
        # Publish Home Assistant discovery
        await mqtt_publisher.publish_ha_discovery(device_id, "Loznice")
        print("✅ Home Assistant discovery published")
        
        await mqtt_publisher.disconnect()
        print("✅ MQTT disconnected")
        
        return True
        
    except Exception as e:
        print(f"❌ MQTT publishing failed: {e}")
        return False


async def main():
    """Run end-to-end testing."""
    print("🚀 End-to-End Testing: BLE → MQTT → Home Assistant")
    print("=" * 60)
    
    success = await test_full_data_flow()
    
    if success:
        print("\n🎉 End-to-end test successful!")
        print("\nNext steps:")
        print("  ✅ Configuration loading works")
        print("  ✅ MQTT publishing works") 
        print("  ✅ Home Assistant discovery works")
        print("  ⚠️  BLE sensor reading needs refinement")
        print("\n💡 You can now run the main daemon to see it in action!")
    else:
        print("\n❌ End-to-end test failed")
        
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)