#!/usr/bin/env python3
"""
Extended scan test to catch ALL advertisement types from LYWSDCGQ/01ZM sensors.
This will help us understand if we're missing humidity/battery advertisements.
"""

import asyncio
import sys
import signal
from datetime import datetime, timezone
sys.path.append("/home/honzik/xiaomi-ble-tempmeter-mqtt-daemon/src")

from bluetooth_manager import BluetoothManager

# Test devices
TEST_DEVICES = {
    "4C:65:A8:DB:99:44": "Chodba",
    "4C:65:A8:DC:84:01": "Loznice"
}

class ExtendedScanner:
    def __init__(self):
        self.running = True
        self.advertisement_count = {}
        
    async def run_scan(self, duration=60):
        """Run extended scan to capture all advertisement types"""
        
        config = {
            'bluetooth_adapter': 0,
            'bluetooth_timeout': duration,
            'scan_interval': 1.0,
            'devices': []
        }
        
        bt_manager = BluetoothManager(config)
        
        print(f"🔍 Starting {duration}s extended scan for all advertisement types...")
        print(f"📍 Target devices: {TEST_DEVICES}")
        print(f"📊 Looking for advertisement patterns:")
        print(f"   - 0d1004: Temperature data")  
        print(f"   - 061002: Humidity data")
        print(f"   - 0a1001: Battery data")
        print(f"   - Other: Unknown patterns")
        print("=" * 70)
        
        # Set up signal handling
        def signal_handler(signum, frame):
            self.running = False
            print("\n🛑 Stopping scan...")
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Override advertisement callback for detailed logging
        original_callback = bt_manager._advertisement_callback
        
        def enhanced_callback(device, advertisement_data):
            mac_address = device.address
            
            if mac_address in TEST_DEVICES:
                rssi = advertisement_data.rssi or 0
                service_data = advertisement_data.service_data
                
                timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
                
                if service_data:
                    for uuid, data in service_data.items():
                        if uuid == "0000fe95-0000-1000-8000-00805f9b34fb":
                            hex_data = data.hex()
                            
                            # Track advertisement patterns
                            if mac_address not in self.advertisement_count:
                                self.advertisement_count[mac_address] = {}
                            
                            # Look for specific patterns in the data
                            pattern = "unknown"
                            if "0d1004" in hex_data:
                                pattern = "0d1004_temp"
                            elif "061002" in hex_data:
                                pattern = "061002_humidity" 
                            elif "0a1001" in hex_data:
                                pattern = "0a1001_battery"
                            elif len(hex_data) >= 20:
                                # Check pattern at specific positions
                                if hex_data[20:26] == "0d1004":
                                    pattern = "0d1004_temp"
                                elif hex_data[20:26] == "061002": 
                                    pattern = "061002_humidity"
                                elif hex_data[20:26] == "0a1001":
                                    pattern = "0a1001_battery"
                            
                            if pattern not in self.advertisement_count[mac_address]:
                                self.advertisement_count[mac_address][pattern] = 0
                            self.advertisement_count[mac_address][pattern] += 1
                            
                            device_name = TEST_DEVICES[mac_address]
                            print(f"[{timestamp}] 📡 {device_name} ({mac_address})")
                            print(f"           Pattern: {pattern}")
                            print(f"           RSSI: {rssi} dBm")
                            print(f"           Data: {hex_data}")
                            print(f"           Length: {len(data)} bytes")
                            
                            # Try to parse with current logic
                            try:
                                result = original_callback(device, advertisement_data)
                                if result:
                                    print(f"           ✅ Parsed: T={result.temperature}°C, H={result.humidity}%, B={result.battery}%")
                                else:
                                    print(f"           ❌ Parse failed")
                            except Exception as e:
                                print(f"           ❌ Parse error: {e}")
                            print("-" * 50)
            
            return original_callback(device, advertisement_data)
        
        bt_manager._advertisement_callback = enhanced_callback
        
        try:
            await bt_manager.start_scanning()
            
            # Wait for the specified duration or until stopped
            start_time = asyncio.get_event_loop().time()
            while self.running and (asyncio.get_event_loop().time() - start_time < duration):
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"❌ Scan error: {e}")
        finally:
            await bt_manager.cleanup()
            
        # Print summary
        print("\n" + "=" * 70)
        print("📊 SCAN SUMMARY")
        print("=" * 70)
        
        if self.advertisement_count:
            for mac_address, patterns in self.advertisement_count.items():
                device_name = TEST_DEVICES[mac_address]
                print(f"\n🔸 {device_name} ({mac_address}):")
                total = sum(patterns.values())
                print(f"   Total advertisements: {total}")
                
                for pattern, count in sorted(patterns.items()):
                    percentage = (count / total) * 100 if total > 0 else 0
                    status = "✅" if pattern != "unknown" else "❓"
                    print(f"   {status} {pattern}: {count} ({percentage:.1f}%)")
        else:
            print("❌ No advertisements received from target devices")
            
        print(f"\n💡 ANALYSIS:")
        print(f"   - If only seeing 0d1004_temp: Need longer scan or different timing")
        print(f"   - If seeing 061002_humidity/0a1001_battery: Check parsing logic")  
        print(f"   - If seeing 'unknown': May need to update pattern detection")

if __name__ == "__main__":
    scanner = ExtendedScanner()
    asyncio.run(scanner.run_scan(duration=90))  # 90 second scan