#!/usr/bin/env python3
"""
Test script for the integrated bluetooth manager with advertisement support
"""
import asyncio
import logging
from src.bluetooth_manager import BluetoothManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_lywsdcgq_device():
    """Test reading from LYWSDCGQ device using the integrated approach"""
    
    # Test device
    mac_address = "4C:65:A8:DC:84:01"
    
    # Create bluetooth manager
    config = {
        'retry_attempts': 2,
        'connection_timeout': 15
    }
    bt_manager = BluetoothManager(config)
    
    try:
        print(f"\n=== Testing integrated bluetooth manager ===")
        print(f"Target device: {mac_address}")
        print(f"Expected: LYWSDCGQ device using advertisement method")
        
        # Test the unified read method
        sensor_data = await bt_manager.read_sensor_data(mac_address, scan_timeout=20)
        
        if sensor_data:
            print(f"\n✅ SUCCESS!")
            print(f"Temperature: {sensor_data.temperature}°C")
            print(f"Humidity: {sensor_data.humidity}%")
            print(f"Battery: {sensor_data.battery}%")
            print(f"Voltage: {sensor_data.voltage}V")
            print(f"RSSI: {sensor_data.rssi} dBm")
            print(f"Last seen: {sensor_data.last_seen}")
            
            # Validate data quality
            if 20 <= sensor_data.temperature <= 30 and 30 <= sensor_data.humidity <= 50:
                print(f"✅ Data quality: GOOD (reasonable values)")
            else:
                print(f"⚠️ Data quality: Check needed (temp={sensor_data.temperature}°C, humidity={sensor_data.humidity}%)")
        else:
            print(f"\n❌ FAILED to read sensor data")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bt_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_lywsdcgq_device())