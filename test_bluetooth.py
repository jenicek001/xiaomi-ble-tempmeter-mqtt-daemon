#!/usr/bin/env python3
"""
Simple test script to verify the Bluetooth Manager implementation.
This can be run without the full daemon to test BLE functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bluetooth_manager import BluetoothManager
from constants import DEFAULT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_bluetooth_manager():
    """Test the Bluetooth Manager functionality."""
    logger.info("Testing Bluetooth Manager...")
    
    # Initialize Bluetooth manager
    bt_manager = BluetoothManager(DEFAULT_CONFIG["bluetooth"])
    
    try:
        # Test device discovery
        logger.info("Starting device discovery...")
        devices = await bt_manager.discover_devices()
        
        if not devices:
            logger.info("No Xiaomi devices found. Make sure devices are powered on and nearby.")
            return
            
        logger.info(f"Found {len(devices)} Xiaomi devices:")
        for device in devices:
            logger.info(f"  - {device['name']} ({device['mac']}) RSSI: {device['rssi']}")
            
        # Test reading data from first device
        if devices:
            test_device = devices[0]
            logger.info(f"Testing data reading from {test_device['name']} ({test_device['mac']})")
            
            sensor_data = await bt_manager.read_device_data(
                test_device['mac'], 
                test_device['mode']
            )
            
            if sensor_data:
                logger.info("Successfully read sensor data:")
                logger.info(f"  Temperature: {sensor_data.temperature}°C")
                logger.info(f"  Humidity: {sensor_data.humidity}%")
                logger.info(f"  Battery: {sensor_data.battery}%")
                logger.info(f"  Voltage: {sensor_data.voltage}V")
                logger.info(f"  JSON: {sensor_data.to_dict()}")
            else:
                logger.error("Failed to read sensor data")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        await bt_manager.cleanup()
        logger.info("Test completed")


if __name__ == "__main__":
    logger.info("Xiaomi Mijia Bluetooth Manager Test")
    logger.info("Make sure you have Xiaomi devices powered on and nearby.")
    logger.info("This test requires root privileges for Bluetooth access on Linux.")
    
    try:
        asyncio.run(test_bluetooth_manager())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)