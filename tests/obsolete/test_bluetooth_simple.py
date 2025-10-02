#!/usr/bin/env python3
"""
Simplified test for BluetoothManager - focuses on core BLE functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from bleak import BleakClient, BleakScanner
    from config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak --with pydantic --with pyyaml --with python-dotenv python test_bluetooth_simple.py")
    exit(1)


async def test_config_loading():
    """Test that we can load configuration."""
    print("📄 Testing Configuration Loading")
    print("=" * 40)
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        print(f"✅ Configuration loaded successfully")
        print(f"   🏠 MQTT Broker: {config.mqtt.broker_host}:{config.mqtt.broker_port}")
        print(f"   📡 Poll interval: {config.devices.poll_interval}s")
        print(f"   🔧 Devices configured: {len(config.devices.static_devices)}")
        
        for i, device in enumerate(config.devices.static_devices, 1):
            print(f"   Device {i}: {device['mac']} ({device['mode']})")
        
        return config
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return None


async def test_device_scanning():
    """Test device scanning for our configured device."""
    print("\n🔍 Testing Device Scanning")
    print("=" * 40)
    
    target_mac = "4C:65:A8:DC:84:01"
    target_name = "MJ_HT_V1"
    
    print(f"Looking for device: {target_name} ({target_mac})")
    print("Scanning for 10 seconds...")
    
    found_device = None
    
    try:
        async with BleakScanner() as scanner:
            await asyncio.sleep(10)
            
            for device in scanner.discovered_devices:
                if device.address == target_mac:
                    found_device = device
                    print(f"✅ Found target device!")
                    print(f"   📍 MAC: {device.address}")
                    print(f"   📱 Name: {device.name}")
                    # RSSI might not be available in discovery
                    try:
                        print(f"   📶 RSSI: {device.rssi} dBm")
                    except AttributeError:
                        print(f"   📶 RSSI: Not available")
                    break
        
        if not found_device:
            print(f"⚠️  Target device not found in scan")
            print("   - Device might be sleeping or out of range")
            print("   - Try getting closer or checking battery")
        
        return found_device
        
    except Exception as e:
        print(f"❌ Scanning failed: {e}")
        return None


async def test_basic_connection():
    """Test basic BLE connection."""
    print("\n🔗 Testing Basic BLE Connection")
    print("=" * 40)
    
    target_mac = "4C:65:A8:DC:84:01"
    
    connection_attempts = [
        {"timeout": 10, "name": "Quick connection"},
        {"timeout": 20, "name": "Standard connection"},
        {"timeout": 30, "name": "Patient connection"}
    ]
    
    for i, attempt in enumerate(connection_attempts, 1):
        print(f"\nAttempt {i}: {attempt['name']} (timeout: {attempt['timeout']}s)")
        
        try:
            client = BleakClient(target_mac, timeout=attempt['timeout'])
            
            # Try connection
            await client.connect()
            
            if client.is_connected:
                print(f"✅ Connection successful!")
                
                try:
                    # Get services (wait a moment for discovery)
                    await asyncio.sleep(2)  # Give time for service discovery
                    services = client.services
                    service_count = len(list(services))
                    print(f"   📋 Found {service_count} services")
                    
                    # List all characteristics with handles
                    char_count = 0
                    for service in services:
                        for char in service.characteristics:
                            char_count += 1
                            handle_hex = f"0x{char.handle:04x}"
                            props = ", ".join(char.properties)
                            print(f"   📡 Handle {handle_hex}: {char.uuid} ({props})")
                            
                            # Highlight handles we're interested in
                            if "0038" in handle_hex.lower() or "0046" in handle_hex.lower():
                                print(f"      ⭐ This is a target handle for our device!")
                    
                    print(f"   📊 Total characteristics: {char_count}")
                    
                    await client.disconnect()
                    return True
                    
                except Exception as e:
                    print(f"   ⚠️  Connected but service discovery failed: {e}")
                    await client.disconnect()
                    return True  # Connection itself worked
            else:
                print(f"   ❌ Connection failed")
                
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
        
        # Wait between attempts
        if i < len(connection_attempts):
            print("   ⏳ Waiting 5 seconds before retry...")
            await asyncio.sleep(5)
    
    return False


async def test_notifications():
    """Test setting up notifications (if connection works)."""
    print("\n📢 Testing Notification Setup")
    print("=" * 40)
    
    target_mac = "4C:65:A8:DC:84:01"
    
    try:
        async with BleakClient(target_mac, timeout=20) as client:
            if not client.is_connected:
                print("❌ Could not connect for notification test")
                return False
            
            print("✅ Connected - looking for notification handles...")
            
            # Wait for service discovery to complete
            await asyncio.sleep(3)
            services = client.services
            
            # Look for handle 0x0038 (common notification handle for these devices)
            target_handle = None
            for service in services:
                for char in service.characteristics:
                    if char.handle == 0x0038 or "notify" in char.properties:
                        target_handle = char.handle
                        print(f"   📡 Found notification handle: 0x{char.handle:04x}")
                        print(f"      Properties: {', '.join(char.properties)}")
                        
                        if "notify" in char.properties:
                            print("      ✅ Supports notifications")
                        else:
                            print("      ⚠️  No notify property")
            
            if target_handle:
                # Try to enable notifications
                print(f"   🔔 Attempting to enable notifications on handle 0x{target_handle:04x}...")
                
                notification_data = []
                
                def notification_handler(sender, data):
                    notification_data.append(data)
                    print(f"   📨 Received notification: {len(data)} bytes")
                    print(f"      Data: {data.hex()}")
                
                try:
                    await client.start_notify(target_handle, notification_handler)
                    print("   ✅ Notifications enabled - waiting for data...")
                    
                    # Wait for notifications
                    await asyncio.sleep(15)
                    
                    await client.stop_notify(target_handle)
                    
                    if notification_data:
                        print(f"   🎉 Received {len(notification_data)} notification(s)!")
                        return True
                    else:
                        print("   ⚠️  No notifications received (device might be sleeping)")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ Notification setup failed: {e}")
                    return False
            else:
                print("   ⚠️  No suitable notification handle found")
                return False
                
    except Exception as e:
        print(f"❌ Notification test failed: {e}")
        return False


async def main():
    """Run simplified Bluetooth tests."""
    print("🧪 Simplified Bluetooth Testing")
    print("=" * 50)
    
    # Test 1: Configuration
    config = await test_config_loading()
    if not config:
        return False
    
    # Test 2: Device scanning  
    found_device = await test_device_scanning()
    
    # Test 3: Basic connection
    connection_success = await test_basic_connection()
    
    if connection_success:
        # Test 4: Notifications (only if connection worked)
        notification_success = await test_notifications()
        
        if notification_success:
            print("\n🎉 All tests passed! Your device is working correctly.")
        else:
            print("\n⚠️  Connection works but notifications need work.")
    else:
        print("\n❌ Connection tests failed - check device power and proximity.")
    
    return connection_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)