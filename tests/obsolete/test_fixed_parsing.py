#!/usr/bin/env python3
"""
Test the fixed Xiaomi advertisement parsing with both sensors.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from bleak import BleakScanner
    from config_manager import ConfigManager
    from bluetooth_manager import BluetoothManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak --with pydantic --with pyyaml --with python-dotenv python test_fixed_parsing.py")
    exit(1)


async def test_both_sensors():
    """Test reading from both configured sensors."""
    print("🔬 Testing Fixed Xiaomi Advertisement Parsing")
    print("=" * 60)
    
    # Load configuration
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        print(f"✅ Configuration loaded - found {len(config.devices.static_devices)} devices")
        
        for i, device in enumerate(config.devices.static_devices, 1):
            print(f"   Device {i}: {device['mac']} ({device['mode']}) - {device['name']}")
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Create Bluetooth manager
    bt_manager = BluetoothManager(config.bluetooth.dict())
    
    # Test each configured device
    success_count = 0
    
    for device_config in config.devices.static_devices:
        mac = device_config['mac']
        mode = device_config['mode'] 
        name = device_config['name']
        
        print(f"\n📡 Testing device: {name}")
        print(f"   📍 MAC: {mac}")
        print(f"   🔧 Mode: {mode}")
        
        try:
            # Use the fixed advertisement-based reading
            sensor_data = await bt_manager.read_device_data(mac, mode)
            
            if sensor_data:
                print(f"   🎉 SUCCESS! Sensor data received:")
                print(f"      🌡️  Temperature: {sensor_data.temperature}°C")
                print(f"      💧 Humidity: {sensor_data.humidity}%")
                print(f"      🔋 Battery: {sensor_data.battery}%")
                print(f"      ⚡ Voltage: {sensor_data.voltage:.2f}V")
                print(f"      ⏰ Timestamp: {sensor_data.timestamp}")
                success_count += 1
            else:
                print(f"   ❌ No sensor data received")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Results: {success_count}/{len(config.devices.static_devices)} sensors working")
    
    if success_count == len(config.devices.static_devices):
        print(f"🎉 All sensors are working perfectly!")
        print(f"\n✅ Ready to run the full daemon!")
    elif success_count > 0:
        print(f"⚠️  Partial success - some sensors are working")
    else:
        print(f"❌ No sensors responding - check device power and proximity")
    
    return success_count > 0


async def test_manual_scanning():
    """Manual scanning to see raw advertisement data."""
    print(f"\n🔍 Manual Advertisement Scanning (10 seconds)")
    print(f"=" * 50)
    
    found_devices = []
    
    def detection_callback(device, advertisement_data):
        if device.address.upper() in ["4C:65:A8:DC:84:01", "4C:65:A8:DB:99:44"]:
            found_devices.append((device, advertisement_data))
            
            print(f"📱 {device.name or 'Unknown'} ({device.address})")
            
            xiaomi_service_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
            if xiaomi_service_uuid in advertisement_data.service_data:
                service_data = advertisement_data.service_data[xiaomi_service_uuid]
                print(f"   📊 Raw service data: {service_data.hex()}")
                
                # Parse with our fixed method
                from bluetooth_manager import BluetoothManager
                bt_manager = BluetoothManager({})
                result = bt_manager._parse_xiaomi_advertisement(service_data)
                
                if result:
                    print(f"   🎉 Parsed: {result.temperature}°C, {result.humidity}%, {result.battery}%")
                else:
                    print(f"   ❌ Parsing failed")
    
    try:
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(10)
        await scanner.stop()
        
        print(f"\n📊 Found {len(found_devices)} target device advertisements")
        
    except Exception as e:
        print(f"❌ Scanning failed: {e}")


async def main():
    """Run all tests."""
    # Test 1: Configuration and parsing
    success = await test_both_sensors()
    
    # Test 2: Manual verification
    await test_manual_scanning()
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)