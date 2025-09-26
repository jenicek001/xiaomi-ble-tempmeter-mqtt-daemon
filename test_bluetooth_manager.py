#!/usr/bin/env python3
"""
Test the actual BluetoothManager implementation from our daemon.
This tests the real logic we'll use in production.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path so we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from bleak import BleakClient, BleakScanner
    from bluetooth_manager import BluetoothManager, SensorData
    from config_manager import ConfigManager
    from constants import DEVICE_CHARACTERISTICS, SUPPORTED_DEVICES
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak --with pydantic python test_bluetooth_manager.py")
    exit(1)


async def test_bluetooth_manager():
    """Test our BluetoothManager class."""
    print("🧪 Testing BluetoothManager Implementation")
    print("=" * 50)
    
    # Load configuration
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   📡 Poll interval: {config.poll_interval}s")
        print(f"   🔧 Devices: {len(config.static_devices)} configured")
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    # Test each configured device
    for device_config in config.static_devices:
        print(f"\n📱 Testing device: {device_config.mac} ({device_config.device_type})")
        
        # Create BluetoothManager instance
        bt_manager = BluetoothManager()
        
        try:
            # Test device discovery first
            print("  🔍 Scanning for device...")
            
            async with BleakScanner() as scanner:
                await asyncio.sleep(5)  # Quick scan
                devices = scanner.discovered_devices
                
                target_device = None
                for device in devices:
                    if device.address == device_config.mac:
                        target_device = device
                        break
                
                if target_device:
                    print(f"  ✅ Device found! RSSI: {target_device.rssi} dBm")
                else:
                    print(f"  ⚠️  Device not found in quick scan - trying connection anyway")
            
            # Test connection and data reading
            print("  🔗 Testing connection and data reading...")
            
            sensor_data = await bt_manager.read_sensor_data(
                device_config.mac, 
                device_config.device_type
            )
            
            if sensor_data:
                print(f"  🎉 Successfully read sensor data!")
                print(f"     🌡️  Temperature: {sensor_data.temperature}°C")
                print(f"     💧 Humidity: {sensor_data.humidity}%")
                print(f"     🔋 Battery: {sensor_data.battery}%")
                print(f"     ⏰ Timestamp: {sensor_data.timestamp}")
                return True
            else:
                print("  ❌ Failed to read sensor data")
                return False
                
        except Exception as e:
            print(f"  ❌ Error testing device {device_config.mac}: {e}")
            return False


async def test_raw_connection():
    """Test raw BLE connection to understand timing issues."""
    mac_address = "4C:65:A8:DC:84:01"
    print(f"\n🔧 Testing raw connection to {mac_address}")
    print("=" * 50)
    
    # Multiple connection attempts with different strategies
    strategies = [
        {"timeout": 10.0, "name": "Standard timeout"},
        {"timeout": 20.0, "name": "Extended timeout"}, 
        {"timeout": 30.0, "name": "Long timeout"},
    ]
    
    for i, strategy in enumerate(strategies, 1):
        print(f"\nAttempt {i}: {strategy['name']} ({strategy['timeout']}s)")
        
        try:
            async with BleakClient(mac_address, timeout=strategy['timeout']) as client:
                if client.is_connected:
                    print(f"  ✅ Connection successful!")
                    
                    # Try to read device info
                    try:
                        services = await client.get_services()
                        print(f"  📋 Services available: {len(services.services)}")
                        
                        # Look for our expected characteristics
                        for service in services.services:
                            for char in service.characteristics:
                                handle_hex = f"0x{char.handle:04x}"
                                if handle_hex in ["0x0038", "0x0046"]:
                                    print(f"  ⭐ Found target handle: {handle_hex}")
                        
                        return True
                        
                    except Exception as e:
                        print(f"  ⚠️  Connected but couldn't read services: {e}")
                        return True  # Still a successful connection
                else:
                    print(f"  ❌ Connection failed")
                    
        except Exception as e:
            print(f"  ❌ Connection error: {e}")
            
        # Wait between attempts
        if i < len(strategies):
            print("  ⏳ Waiting 3 seconds before next attempt...")
            await asyncio.sleep(3)
    
    return False


async def main():
    """Run all Bluetooth manager tests."""
    print("🚀 Starting Bluetooth Manager Tests")
    print()
    
    # Test 1: Configuration and BluetoothManager
    manager_success = await test_bluetooth_manager()
    
    # Test 2: Raw connection debugging if manager test failed
    if not manager_success:
        print("\n🔧 Running raw connection test for debugging...")
        raw_success = await test_raw_connection()
        
        if raw_success:
            print("\n💡 Raw connection worked - issue might be in our manager logic")
        else:
            print("\n💡 Raw connection also failed - might be device timing or power issue")
    
    return manager_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)