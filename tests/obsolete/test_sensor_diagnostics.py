#!/usr/bin/env python3
"""
Diagnostic test to determine if the issue is sensor reading or device activation.
This will test various approaches to get data from the MJ_HT_V1 device.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from bleak import BleakClient, BleakScanner
    from bleak.exc import BleakDBusError, BleakError
    import struct
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak python test_sensor_diagnostics.py")
    exit(1)


async def test_device_activation_methods():
    """Test different methods to activate the device and get sensor data."""
    print("🔧 Device Activation & Sensor Reading Diagnostics")
    print("=" * 60)
    
    target_mac = "4C:65:A8:DC:84:01"
    
    print(f"Target device: MJ_HT_V1 ({target_mac})")
    print("Testing various activation and reading methods...\n")
    
    # Method 1: Read all readable characteristics
    success = await test_read_all_characteristics(target_mac)
    if success:
        return True
    
    # Method 2: Try notifications on all notification-capable characteristics
    success = await test_all_notifications(target_mac)
    if success:
        return True
    
    # Method 3: Try writing activation commands to writable characteristics
    success = await test_activation_commands(target_mac)
    if success:
        return True
    
    # Method 4: Test connection persistence (device might need time)
    success = await test_persistent_connection(target_mac)
    if success:
        return True
    
    return False


async def test_read_all_characteristics(mac_address):
    """Test reading from all readable characteristics."""
    print("📖 Method 1: Reading All Readable Characteristics")
    print("-" * 50)
    
    try:
        async with BleakClient(mac_address, timeout=30) as client:
            if not client.is_connected:
                print("❌ Could not connect")
                return False
            
            print("✅ Connected - waiting for service discovery...")
            await asyncio.sleep(3)
            
            readable_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "read" in char.properties:
                        readable_chars.append(char)
            
            print(f"Found {len(readable_chars)} readable characteristics:")
            
            for char in readable_chars:
                try:
                    print(f"\n📡 Reading {char.uuid} (handle 0x{char.handle:04x})...")
                    data = await client.read_gatt_char(char.uuid)
                    
                    print(f"   📊 Raw data: {data.hex()} ({len(data)} bytes)")
                    
                    # Try to interpret as sensor data
                    if len(data) >= 3:
                        result = try_decode_sensor_data(data, char.handle)
                        if result:
                            print(f"   🎉 SENSOR DATA FOUND!")
                            print(f"   🌡️  Temperature: {result['temperature']}°C")
                            print(f"   💧 Humidity: {result['humidity']}%")
                            if 'battery' in result:
                                print(f"   🔋 Battery: {result['battery']}%")
                            return True
                    
                except Exception as e:
                    print(f"   ❌ Read failed: {e}")
            
            print("❌ No sensor data found in readable characteristics")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_all_notifications(mac_address):
    """Test notifications on all notification-capable characteristics."""
    print("\n🔔 Method 2: Testing All Notification Characteristics")
    print("-" * 50)
    
    try:
        async with BleakClient(mac_address, timeout=30) as client:
            if not client.is_connected:
                print("❌ Could not connect")
                return False
            
            print("✅ Connected - waiting for service discovery...")
            await asyncio.sleep(3)
            
            notify_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties:
                        notify_chars.append(char)
            
            print(f"Found {len(notify_chars)} notification characteristics:")
            
            for char in notify_chars:
                print(f"\n📡 Testing notifications on {char.uuid} (handle 0x{char.handle:04x})...")
                
                received_data = []
                
                def notification_handler(sender, data):
                    print(f"   📨 Notification received: {data.hex()} ({len(data)} bytes)")
                    received_data.append(data)
                    
                    # Try to decode immediately
                    result = try_decode_sensor_data(data, char.handle)
                    if result:
                        print(f"   🎉 DECODED SENSOR DATA!")
                        print(f"   🌡️  Temperature: {result['temperature']}°C")
                        print(f"   💧 Humidity: {result['humidity']}%")
                        if 'battery' in result:
                            print(f"   🔋 Battery: {result['battery']}%")
                
                try:
                    await client.start_notify(char.uuid, notification_handler)
                    print(f"   ✅ Notifications enabled - waiting 15 seconds...")
                    await asyncio.sleep(15)
                    await client.stop_notify(char.uuid)
                    
                    if received_data:
                        print(f"   📊 Received {len(received_data)} notification(s)")
                        # Check if any contained sensor data
                        for data in received_data:
                            result = try_decode_sensor_data(data, char.handle)
                            if result:
                                return True
                    else:
                        print(f"   ⚠️  No notifications received")
                        
                except Exception as e:
                    print(f"   ❌ Notification setup failed: {e}")
            
            print("❌ No sensor data found via notifications")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_activation_commands(mac_address):
    """Try writing activation commands to wake up the device."""
    print("\n⚡ Method 3: Testing Device Activation Commands")
    print("-" * 50)
    
    # Common activation commands for Xiaomi devices
    activation_commands = [
        b'\x01\x00',           # Enable notifications
        b'\x02\x00',           # Alternative enable
        b'\x01',               # Simple enable
        b'\x00\x01',           # Reverse byte order
    ]
    
    try:
        async with BleakClient(mac_address, timeout=30) as client:
            if not client.is_connected:
                print("❌ Could not connect")
                return False
            
            print("✅ Connected - looking for writable characteristics...")
            await asyncio.sleep(3)
            
            writable_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "write" in char.properties or "write-without-response" in char.properties:
                        writable_chars.append(char)
            
            print(f"Found {len(writable_chars)} writable characteristics")
            
            for char in writable_chars:
                print(f"\n📡 Testing activation on {char.uuid} (handle 0x{char.handle:04x})...")
                
                for i, cmd in enumerate(activation_commands):
                    try:
                        print(f"   🔧 Sending command {i+1}: {cmd.hex()}")
                        
                        if "write-without-response" in char.properties:
                            await client.write_gatt_char(char.uuid, cmd, response=False)
                        else:
                            await client.write_gatt_char(char.uuid, cmd, response=True)
                        
                        print(f"   ✅ Command sent successfully")
                        
                        # Wait a moment and check if device activated
                        await asyncio.sleep(2)
                        
                        # Try to read from readable characteristics after activation
                        for service in client.services:
                            for read_char in service.characteristics:
                                if "read" in read_char.properties:
                                    try:
                                        data = await client.read_gatt_char(read_char.uuid)
                                        result = try_decode_sensor_data(data, read_char.handle)
                                        if result:
                                            print(f"   🎉 ACTIVATION SUCCESSFUL!")
                                            print(f"   🌡️  Temperature: {result['temperature']}°C")
                                            print(f"   💧 Humidity: {result['humidity']}%")
                                            return True
                                    except:
                                        continue
                        
                    except Exception as e:
                        print(f"   ❌ Command failed: {e}")
            
            print("❌ No activation commands succeeded")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_persistent_connection(mac_address):
    """Test maintaining connection for longer period - device might broadcast periodically."""
    print("\n⏰ Method 4: Testing Persistent Connection")
    print("-" * 50)
    
    try:
        async with BleakClient(mac_address, timeout=30) as client:
            if not client.is_connected:
                print("❌ Could not connect")
                return False
            
            print("✅ Connected - setting up monitoring for 60 seconds...")
            await asyncio.sleep(3)
            
            # Find notification characteristics
            notify_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties:
                        notify_chars.append(char)
            
            print(f"Monitoring {len(notify_chars)} notification characteristics...")
            
            received_any_data = False
            
            def universal_handler(sender, data):
                nonlocal received_any_data
                received_any_data = True
                print(f"📨 Data from {sender}: {data.hex()}")
                
                result = try_decode_sensor_data(data)
                if result:
                    print(f"🎉 SENSOR DATA DECODED!")
                    print(f"🌡️  Temperature: {result['temperature']}°C")
                    print(f"💧 Humidity: {result['humidity']}%")
                    if 'battery' in result:
                        print(f"🔋 Battery: {result['battery']}%")
            
            # Enable notifications on all possible characteristics
            active_notifications = []
            for char in notify_chars:
                try:
                    await client.start_notify(char.uuid, universal_handler)
                    active_notifications.append(char.uuid)
                    print(f"   ✅ Monitoring {char.uuid}")
                except:
                    pass
            
            print(f"\n⏱️  Waiting 60 seconds for any data...")
            print("💡 Try pressing the device button now or waving near it!")
            
            # Wait and periodically check
            for i in range(12):  # 12 x 5 seconds = 60 seconds
                await asyncio.sleep(5)
                print(f"   ⏳ {(i+1)*5}/60 seconds elapsed...")
            
            # Clean up notifications
            for uuid in active_notifications:
                try:
                    await client.stop_notify(uuid)
                except:
                    pass
            
            if received_any_data:
                print("📊 Some data was received during monitoring")
                return True
            else:
                print("❌ No data received during 60-second monitoring")
                return False
            
    except Exception as e:
        print(f"❌ Persistent connection failed: {e}")
        return False


def try_decode_sensor_data(data, handle=None):
    """Try to decode sensor data from raw bytes using various formats."""
    if len(data) < 3:
        return None
    
    try:
        # Format 1: Standard Xiaomi format (temp 2 bytes, humidity 1 byte, battery 2 bytes)
        if len(data) >= 5:
            temp_raw = struct.unpack('<h', data[0:2])[0]  # Signed 16-bit little endian
            temp = temp_raw / 100.0
            humidity = data[2]
            battery_raw = struct.unpack('<H', data[3:5])[0]  # Unsigned 16-bit
            voltage = battery_raw / 1000.0
            battery = min(int(round((voltage - 2.1) * 100)), 100)
            
            # Sanity check
            if -40 <= temp <= 80 and 0 <= humidity <= 100 and 0 <= battery <= 100:
                return {
                    'temperature': temp,
                    'humidity': humidity,
                    'battery': battery,
                    'voltage': voltage
                }
        
        # Format 2: Alternative format (temp 2 bytes, humidity 2 bytes)
        if len(data) >= 4:
            temp_raw = struct.unpack('<h', data[0:2])[0]
            temp = temp_raw / 100.0
            humidity_raw = struct.unpack('<H', data[2:4])[0]
            humidity = humidity_raw / 100.0
            
            if -40 <= temp <= 80 and 0 <= humidity <= 100:
                return {
                    'temperature': temp,
                    'humidity': humidity
                }
        
        # Format 3: Simple 3-byte format
        if len(data) >= 3:
            temp = struct.unpack('<h', data[0:2])[0] / 100.0
            humidity = data[2]
            
            if -40 <= temp <= 80 and 0 <= humidity <= 100:
                return {
                    'temperature': temp,
                    'humidity': humidity
                }
        
    except Exception:
        pass
    
    return None


async def main():
    """Run sensor diagnostics."""
    print("🔍 Xiaomi MJ_HT_V1 Sensor Diagnostics")
    print("=" * 60)
    print("This will test various methods to read sensor data from your device.")
    print("Keep the device close and try pressing its button during testing.\n")
    
    success = await test_device_activation_methods()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Sensor data reading is working!")
        print("The issue was device activation - now you know how to get data.")
    else:
        print("❌ DIAGNOSIS: Unable to read sensor data")
        print("\n🔧 Possible issues:")
        print("  1. Device is in deep sleep - try pressing button repeatedly")
        print("  2. Device needs pairing/bonding first")
        print("  3. Different data format than expected")
        print("  4. Device firmware version incompatibility")
        print("  5. BLE permissions or adapter issues")
        print("\n💡 Try these steps:")
        print("  - Press and hold the device button for 3+ seconds")
        print("  - Bring device very close to computer (< 1 meter)")
        print("  - Remove and reinsert battery")
        print("  - Check if device works with Mi Home app")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)