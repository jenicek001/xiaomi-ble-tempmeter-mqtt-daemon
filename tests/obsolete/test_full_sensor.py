#!/usr/bin/env python3
"""
Test script to capture complete sensor data over an extended period.
"""

import asyncio
import logging
from datetime import datetime
from src.bluetooth_manager import BluetoothManager

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_full_sensor_data():
    """Test capture of all sensor data types over extended period."""
    
    targets = [
        ("4C:65:A8:DC:84:01", "Loznice"),
        ("4C:65:A8:DB:99:44", "Chodba")
    ]
    
    # Create a simple config dict
    config = {
        "adapter": 0,
        "scan_interval": 300,
        "connection_timeout": 45,  # Use longer timeout
        "retry_attempts": 3,
        "devices": [
            {"mac": "4C:65:A8:DC:84:01", "name": "Loznice"},
            {"mac": "4C:65:A8:DB:99:44", "name": "Chodba"}
        ]
    }
    manager = BluetoothManager(config)
    
    for mac_address, name in targets:
        print(f"\n🔍 Testing complete sensor data for {name} ({mac_address})")
        print("=" * 60)
        
        try:
            # Use read_device_data with LYWSDCGQ device mode
            sensor_data = await manager.read_device_data(mac_address, "LYWSDCGQ/01ZM")
            
            if sensor_data:
                print(f"\n✅ COMPLETE SENSOR DATA:")
                print(f"  Device: {name} ({mac_address})")
                print(f"  Temperature: {sensor_data.temperature}°C")
                print(f"  Humidity: {sensor_data.humidity}%")
                print(f"  Battery: {sensor_data.battery}%")
                print(f"  RSSI: {sensor_data.rssi} dBm")
                print(f"  Last seen: {sensor_data.last_seen}")
                
                # Check data quality
                has_temp = sensor_data.temperature is not None and sensor_data.temperature > -50
                has_humidity = sensor_data.humidity is not None and sensor_data.humidity > 0
                has_battery = sensor_data.battery is not None and sensor_data.battery > 0
                
                print(f"\n📊 DATA QUALITY CHECK:")
                print(f"  Temperature: {'✅ Valid' if has_temp else '❌ Missing/Invalid'}")
                print(f"  Humidity: {'✅ Valid' if has_humidity else '❌ Missing/Invalid'}")
                print(f"  Battery: {'✅ Valid' if has_battery else '❌ Missing/Invalid'}")
                
                if has_temp and has_humidity and has_battery:
                    print(f"  Status: 🎉 COMPLETE DATA SET!")
                elif has_temp:
                    print(f"  Status: ⚠️  Temperature only (partial data)")
                else:
                    print(f"  Status: ❌ No valid data")
                    
            else:
                print(f"❌ No data received from {name}")
                
        except Exception as e:
            logger.error(f"Error reading from {name}: {e}")
            print(f"❌ Error: {e}")
    
    print("\n🧹 Cleaning up...")
    await manager.cleanup()
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_full_sensor_data())