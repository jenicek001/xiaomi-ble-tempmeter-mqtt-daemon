#!/usr/bin/env python3
"""
Fixed BLE test that handles service discovery timing correctly.
"""

import asyncio
import sys
from pathlib import Path

try:
    from bleak import BleakClient, BleakScanner
    import struct
    import time
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak python test_ble_fixed.py")
    exit(1)


async def test_proper_service_discovery():
    """Test with proper service discovery handling."""
    print("🔧 Fixed BLE Test with Proper Service Discovery")
    print("=" * 60)
    
    target_mac = "4C:65:A8:DC:84:01"
    
    try:
        print("🔗 Connecting to device...")
        client = BleakClient(target_mac, timeout=30.0)
        
        await client.connect()
        
        if not client.is_connected:
            print("❌ Connection failed")
            return False
        
        print("✅ Connected! Waiting for automatic service discovery...")
        
        # Wait longer for service discovery to complete naturally
        await asyncio.sleep(5)
        
        # Check if services are available
        retry_count = 0
        max_retries = 10
        
        while retry_count < max_retries:
            try:
                services = client.services
                if services and len(list(services)) > 0:
                    print(f"✅ Service discovery completed - found {len(list(services))} services")
                    break
            except Exception as e:
                print(f"⏳ Service discovery not ready (attempt {retry_count + 1}): {e}")
            
            await asyncio.sleep(2)
            retry_count += 1
        
        if retry_count >= max_retries:
            print("❌ Service discovery failed after multiple attempts")
            await client.disconnect()
            return False
        
        # Now try to read data
        print("\n📊 Attempting to read sensor data...")
        
        # Method 1: Read from readable characteristics
        readable_found = 0
        for service in services:
            print(f"\n🔧 Service: {service.uuid}")
            for char in service.characteristics:
                print(f"   📡 Char: {char.uuid} - handle 0x{char.handle:04x} - props: {char.properties}")
                
                if "read" in char.properties:
                    readable_found += 1
                    try:
                        print(f"      🔍 Reading...")
                        data = await client.read_gatt_char(char.uuid)
                        print(f"      📊 Data: {data.hex()} ({len(data)} bytes)")
                        
                        # Try to decode
                        result = decode_xiaomi_data(data)
                        if result:
                            print(f"      🎉 DECODED SENSOR DATA!")
                            print(f"      🌡️  Temperature: {result['temperature']}°C")
                            print(f"      💧 Humidity: {result['humidity']}%")
                            if 'battery' in result:
                                print(f"      🔋 Battery: {result['battery']}%")
                            await client.disconnect()
                            return True
                        
                    except Exception as e:
                        print(f"      ❌ Read failed: {e}")
        
        print(f"\n📋 Found {readable_found} readable characteristics, none contained sensor data")
        
        # Method 2: Try notifications on key characteristics
        print("\n🔔 Testing notifications...")
        
        # Focus on the most promising characteristics
        target_uuids = [
            "00002a19-0000-1000-8000-00805f9b34fb",  # Battery
            "00001531-1212-efde-1523-785feabcd123",  # Xiaomi service
            "226caa55-6476-4566-7562-66734470666d",  # Custom
            "226cbb55-6476-4566-7562-66734470666d",  # Custom
        ]
        
        data_received = []
        
        def notification_handler(sender, data):
            print(f"📨 Notification from {sender}: {data.hex()}")
            data_received.append(data)
            
            result = decode_xiaomi_data(data)
            if result:
                print(f"🎉 NOTIFICATION CONTAINS SENSOR DATA!")
                print(f"🌡️  Temperature: {result['temperature']}°C")
                print(f"💧 Humidity: {result['humidity']}%")
                if 'battery' in result:
                    print(f"🔋 Battery: {result['battery']}%")
        
        # Enable notifications
        active_notifications = []
        for service in services:
            for char in service.characteristics:
                if char.uuid.lower() in [u.lower() for u in target_uuids] and "notify" in char.properties:
                    try:
                        print(f"   ✅ Enabling notifications on {char.uuid}")
                        await client.start_notify(char.uuid, notification_handler)
                        active_notifications.append(char.uuid)
                    except Exception as e:
                        print(f"   ❌ Failed to enable notifications on {char.uuid}: {e}")
        
        if active_notifications:
            print(f"\n⏱️  Monitoring {len(active_notifications)} characteristics for 30 seconds...")
            print("💡 Try pressing the device button NOW!")
            
            await asyncio.sleep(30)
            
            # Stop notifications
            for uuid in active_notifications:
                try:
                    await client.stop_notify(uuid)
                except:
                    pass
            
            if data_received:
                print(f"\n📊 Received {len(data_received)} notifications")
                for data in data_received:
                    result = decode_xiaomi_data(data)
                    if result:
                        await client.disconnect()
                        return True
            else:
                print("\n⚠️  No notifications received")
        
        await client.disconnect()
        return len(data_received) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def decode_xiaomi_data(data):
    """Decode Xiaomi sensor data from various formats."""
    if len(data) < 3:
        return None
    
    try:
        # Format 1: 5-byte format (temp 2, humidity 1, battery 2)
        if len(data) >= 5:
            temp = struct.unpack('<h', data[0:2])[0] / 100.0
            humidity = data[2] 
            voltage = struct.unpack('<H', data[3:5])[0] / 1000.0
            battery = max(0, min(100, int((voltage - 2.1) * 100)))
            
            if -40 <= temp <= 80 and 0 <= humidity <= 100:
                return {
                    'temperature': temp,
                    'humidity': humidity,
                    'battery': battery,
                    'voltage': voltage
                }
        
        # Format 2: 3-byte format (temp 2, humidity 1)
        if len(data) >= 3:
            temp = struct.unpack('<h', data[0:2])[0] / 100.0
            humidity = data[2]
            
            if -40 <= temp <= 80 and 0 <= humidity <= 100:
                return {
                    'temperature': temp,
                    'humidity': humidity
                }
        
        # Format 3: Battery only (handle 0x17 often contains just battery)
        if len(data) == 1:
            battery = data[0]
            if 0 <= battery <= 100:
                return {
                    'battery': battery
                }
                
    except Exception:
        pass
    
    return None


async def test_active_scanning():
    """Try active scanning to see if device broadcasts data."""
    print("\n📡 Testing Active Scanning for Advertisement Data")
    print("=" * 50)
    
    print("Scanning for 30 seconds - try pressing device button...")
    
    advertisements_seen = []
    
    def detection_callback(device, advertisement_data):
        if device.address == "4C:65:A8:DC:84:01":
            print(f"📨 Advertisement from MJ_HT_V1:")
            print(f"   📍 MAC: {device.address}")
            print(f"   📱 Name: {device.name}")
            print(f"   📊 Manufacturer data: {advertisement_data.manufacturer_data}")
            print(f"   📊 Service data: {advertisement_data.service_data}")
            
            advertisements_seen.append(advertisement_data)
            
            # Check manufacturer data for sensor info
            for company_id, data in advertisement_data.manufacturer_data.items():
                print(f"      🏭 Company {company_id:04x}: {data.hex()}")
                result = decode_xiaomi_data(data)
                if result:
                    print(f"      🎉 ADVERTISEMENT CONTAINS SENSOR DATA!")
                    print(f"      🌡️  Temperature: {result['temperature']}°C")
                    print(f"      💧 Humidity: {result['humidity']}%")
                    return True
            
            # Check service data
            for service_uuid, data in advertisement_data.service_data.items():
                print(f"      🔧 Service {service_uuid}: {data.hex()}")
                result = decode_xiaomi_data(data)
                if result:
                    print(f"      🎉 SERVICE DATA CONTAINS SENSOR DATA!")
                    print(f"      🌡️  Temperature: {result['temperature']}°C")
                    print(f"      💧 Humidity: {result['humidity']}%")
                    return True
    
    try:
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(30)
        await scanner.stop()
        
        print(f"\n📊 Saw {len(advertisements_seen)} advertisements from device")
        return len(advertisements_seen) > 0
        
    except Exception as e:
        print(f"❌ Scanning failed: {e}")
        return False


async def main():
    """Run comprehensive BLE diagnostics."""
    print("🔍 Comprehensive BLE Diagnostics for MJ_HT_V1")
    print("=" * 60)
    
    # Test 1: Proper connection and service discovery
    success1 = await test_proper_service_discovery()
    
    # Test 2: Advertisement scanning
    success2 = await test_active_scanning()
    
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC RESULTS:")
    
    if success1:
        print("✅ BLE connection and sensor reading: WORKING")
    else:
        print("❌ BLE connection and sensor reading: FAILED")
    
    if success2:
        print("✅ Advertisement data scanning: WORKING")
    else:
        print("❌ Advertisement data scanning: NO DATA")
    
    if success1 or success2:
        print("\n🎉 At least one method worked! The device is responding.")
    else:
        print("\n❌ No sensor data found via any method.")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("1. 📱 Press device button and hold for 3+ seconds")
        print("2. 🔄 Remove battery, wait 10 seconds, reinsert")
        print("3. 📏 Move device very close (< 50cm) to computer")
        print("4. 🏠 Check if device works with Mi Home app")
        print("5. 🔄 Try running test while continuously pressing button")
        print("6. ⚡ Check device battery level (replace if low)")
    
    return success1 or success2


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)