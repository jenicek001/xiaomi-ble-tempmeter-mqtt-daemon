#!/usr/bin/env python3
"""
Test the GATT-based Bluetooth manager (correct approach)
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

async def test_gatt_connection():
    """Test GATT connection to Xiaomi sensors"""
    
    targets = [
        ("4C:65:A8:DC:84:01", "Loznice"),
        ("4C:65:A8:DB:99:44", "Chodba")
    ]
    
    # Create minimal config
    class Config:
        retry_attempts = 3
    
    manager = BluetoothManager(Config())
    
    for mac_address, name in targets:
        print(f"\n🔍 Testing GATT connection to {name} ({mac_address})")
        print("=" * 60)
        
        try:
            # Test GATT connection approach
            sensor_data = await manager.read_sensor_data(mac_address, scan_timeout=15)
            
            if sensor_data:
                print(f"\n✅ SUCCESS - GATT Connection Method:")
                print(f"  Device: {name} ({mac_address})")
                print(f"  Temperature: {sensor_data.temperature}°C")
                print(f"  Humidity: {sensor_data.humidity}%") 
                print(f"  Battery: {sensor_data.battery}%")
                print(f"  Voltage: {sensor_data.voltage:.3f}V")
                print(f"  Timestamp: {sensor_data.timestamp}")
                
                # Validate data quality
                temp_valid = -50 < sensor_data.temperature < 80
                humidity_valid = 0 <= sensor_data.humidity <= 100
                battery_valid = 0 <= sensor_data.battery <= 100
                voltage_valid = 2.0 < sensor_data.voltage < 4.0
                
                print(f"\n📊 DATA VALIDATION:")
                print(f"  Temperature: {'✅' if temp_valid else '❌'} {sensor_data.temperature}°C")
                print(f"  Humidity: {'✅' if humidity_valid else '❌'} {sensor_data.humidity}%")
                print(f"  Battery: {'✅' if battery_valid else '❌'} {sensor_data.battery}%")
                print(f"  Voltage: {'✅' if voltage_valid else '❌'} {sensor_data.voltage:.3f}V")
                
                if all([temp_valid, humidity_valid, battery_valid, voltage_valid]):
                    print(f"  Status: 🎉 ALL DATA VALID!")
                else:
                    print(f"  Status: ⚠️  Some data may be invalid")
                    
            else:
                print(f"❌ No data received from {name}")
                
        except Exception as e:
            logger.error(f"Error testing {name}: {e}")
            print(f"❌ Error: {e}")
    
    print("\n🧹 Cleaning up...")
    await manager.cleanup()
    print("✅ Test completed")

if __name__ == "__main__":
    print("🔬 Testing GATT-based Bluetooth Manager")
    print("This uses the CORRECT protocol from the original Home Assistant component")
    asyncio.run(test_gatt_connection())