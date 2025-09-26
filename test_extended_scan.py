#!/usr/bin/env python3
"""
Test extended scanning to capture all advertisement types
from LYWSDCGQ/01ZM devices
"""
import asyncio
import logging
from datetime import datetime
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Setup logging for detailed debugging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("extended_scan")

XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
TARGET_MAC_1 = "4C:65:A8:DC:84:01"
TARGET_MAC_2 = "4C:65:A8:DB:99:44"

# Data tracking
scan_data = {
    TARGET_MAC_1: {"temperature": [], "humidity": [], "battery": [], "rssi": []},
    TARGET_MAC_2: {"temperature": [], "humidity": [], "battery": [], "rssi": []}
}

def parse_xiaomi_data(service_data: bytes, mac_address: str) -> dict:
    """Parse Xiaomi LYWSDCGQ/01ZM service data"""
    try:
        if len(service_data) < 15:
            return {}
            
        data_hex = service_data.hex()
        logger.info(f"📊 Raw service data from {mac_address}: {data_hex}")
        
        # Skip header, find data type patterns
        for i in range(len(service_data) - 4):
            if i + 4 < len(service_data):
                pattern = service_data[i:i+2].hex()
                
                if pattern == "0d10" and i + 4 < len(service_data):  # Temperature
                    temp_bytes = service_data[i+2:i+4]
                    if len(temp_bytes) == 2:
                        temp_raw = int.from_bytes(temp_bytes, 'little', signed=True)
                        temperature = temp_raw / 10.0
                        logger.info(f"🌡️  Temperature: {temperature}°C (raw: {temp_raw})")
                        return {"temperature": temperature}
                        
                elif pattern == "0610" and i + 4 < len(service_data):  # Humidity  
                    humidity_bytes = service_data[i+2:i+4]
                    if len(humidity_bytes) == 2:
                        humidity_raw = int.from_bytes(humidity_bytes, 'little')
                        humidity = humidity_raw / 10.0
                        logger.info(f"💧 Humidity: {humidity}% (raw: {humidity_raw})")
                        return {"humidity": humidity}
                        
                elif pattern == "0a10" and i + 2 < len(service_data):  # Battery
                    battery = service_data[i+2]
                    logger.info(f"🔋 Battery: {battery}%")
                    return {"battery": battery}
                    
        return {}
        
    except Exception as e:
        logger.error(f"❌ Parse error for {mac_address}: {e}")
        return {}

def advertisement_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    """Process advertisements from target devices"""
    mac = device.address
    
    if mac in [TARGET_MAC_1, TARGET_MAC_2]:
        rssi = advertisement_data.rssi
        
        if XIAOMI_SERVICE_UUID in advertisement_data.service_data:
            service_data = advertisement_data.service_data[XIAOMI_SERVICE_UUID]
            
            logger.info(f"📡 Advertisement from {mac} (RSSI: {rssi} dBm)")
            parsed = parse_xiaomi_data(service_data, mac)
            
            # Track all data types
            if "temperature" in parsed:
                scan_data[mac]["temperature"].append(parsed["temperature"])
                scan_data[mac]["rssi"].append(rssi)
            elif "humidity" in parsed:
                scan_data[mac]["humidity"].append(parsed["humidity"])
            elif "battery" in parsed:
                scan_data[mac]["battery"].append(parsed["battery"])

async def main():
    """Extended scan test"""
    print("🔍 Starting extended 60-second scan for both sensors...")
    print(f"Target sensors: {TARGET_MAC_1} and {TARGET_MAC_2}")
    print("Looking for separate temperature, humidity, and battery advertisements\n")
    
    # Start scanning
    scanner = BleakScanner(advertisement_callback, service_uuids=[])
    
    try:
        await scanner.start()
        
        # Scan for 60 seconds with progress updates
        for i in range(12):  # 12 x 5 seconds = 60 seconds
            await asyncio.sleep(5)
            elapsed = (i + 1) * 5
            
            print(f"⏰ Elapsed: {elapsed}s")
            for mac in [TARGET_MAC_1, TARGET_MAC_2]:
                temp_count = len(scan_data[mac]["temperature"])
                humidity_count = len(scan_data[mac]["humidity"]) 
                battery_count = len(scan_data[mac]["battery"])
                rssi_count = len(scan_data[mac]["rssi"])
                
                print(f"  📍 {mac}: T={temp_count}, H={humidity_count}, B={battery_count}, RSSI samples={rssi_count}")
                
                # Show latest values if available
                if scan_data[mac]["temperature"]:
                    latest_temp = scan_data[mac]["temperature"][-1]
                    latest_rssi = scan_data[mac]["rssi"][-1] if scan_data[mac]["rssi"] else "?"
                    print(f"    Latest: T={latest_temp}°C, RSSI={latest_rssi} dBm")
                if scan_data[mac]["humidity"]:
                    latest_humidity = scan_data[mac]["humidity"][-1]
                    print(f"    Latest: H={latest_humidity}%")
                if scan_data[mac]["battery"]:
                    latest_battery = scan_data[mac]["battery"][-1]
                    print(f"    Latest: B={latest_battery}%")
            print()
        
    except KeyboardInterrupt:
        print("⚡ Scan interrupted by user")
    finally:
        await scanner.stop()
    
    # Final summary
    print("\n📊 FINAL SCAN RESULTS:")
    print("=" * 50)
    
    for mac in [TARGET_MAC_1, TARGET_MAC_2]:
        name = "Loznice" if mac == TARGET_MAC_1 else "Chodba"
        print(f"\n🏠 {name} ({mac}):")
        
        data = scan_data[mac]
        
        if data["temperature"]:
            avg_temp = sum(data["temperature"]) / len(data["temperature"])
            print(f"  🌡️  Temperature: {data['temperature'][-1]:.1f}°C (avg: {avg_temp:.1f}°C, {len(data['temperature'])} samples)")
        else:
            print("  🌡️  Temperature: No data")
            
        if data["humidity"]:
            avg_humidity = sum(data["humidity"]) / len(data["humidity"])
            print(f"  💧 Humidity: {data['humidity'][-1]:.1f}% (avg: {avg_humidity:.1f}%, {len(data['humidity'])} samples)")
        else:
            print("  💧 Humidity: No data")
            
        if data["battery"]:
            avg_battery = sum(data["battery"]) / len(data["battery"])
            print(f"  🔋 Battery: {data['battery'][-1]}% (avg: {avg_battery:.0f}%, {len(data['battery'])} samples)")
        else:
            print("  🔋 Battery: No data")
            
        if data["rssi"]:
            avg_rssi = sum(data["rssi"]) / len(data["rssi"])
            print(f"  📡 RSSI: {data['rssi'][-1]} dBm (avg: {avg_rssi:.0f} dBm, {len(data['rssi'])} samples)")
        else:
            print("  📡 RSSI: No data")

if __name__ == "__main__":
    asyncio.run(main())