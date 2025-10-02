#!/usr/bin/env python3
"""
Test script for MQTT publisher functionality.

This script demonstrates the MQTT publisher integration
without requiring actual Bluetooth devices.
"""
import asyncio
import logging
import json
from datetime import datetime

from src.mqtt_publisher import MQTTPublisher, MQTTConfig
from src.bluetooth_manager import SensorData

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_mqtt_publisher():
    """Test MQTT publisher with sample data."""
    logger.info("Testing MQTT Publisher...")
    
    # Create MQTT configuration
    mqtt_config = MQTTConfig(
        broker_host="localhost",  # Change to your MQTT broker
        broker_port=1883,
        client_id="mijia-test-client",
        # username="your_username",  # Uncomment if authentication is needed
        # password="your_password",
    )
    
    # Create publisher
    publisher = MQTTPublisher(mqtt_config)
    
    try:
        # Start MQTT connection
        logger.info("Starting MQTT publisher...")
        await publisher.start()
        
        if not publisher.is_connected:
            logger.error("Failed to connect to MQTT broker")
            return
            
        # Create sample sensor data
        sensor_data = SensorData(
            temperature=22.5,
                humidity=48,
            battery=85,
                voltage=2.95,
            timestamp=datetime.now()
        )
        
        # Test device ID (MAC address without colons)
        device_id = "A4C1384B1234"
        
        logger.info(f"Publishing sensor data: {sensor_data.to_dict()}")
        
        # Publish sensor data
        success = await publisher.publish_sensor_data(device_id, sensor_data)
        
        if success:
            logger.info("Successfully published sensor data!")
        else:
            logger.error("Failed to publish sensor data")
            
        # Wait a bit to see the results
        await asyncio.sleep(2)
        
        # Get stats
        stats = publisher.get_stats()
        logger.info(f"Publisher stats: {json.dumps(stats, indent=2)}")
        
        # Test publishing data for another device
        logger.info("Publishing data for second device...")
        sensor_data2 = SensorData(
            temperature=24.1,
                humidity=53,
            battery=72,
                voltage=2.84,
            timestamp=datetime.now()
        )
        
        device_id2 = "A4C1384B5678"
        success2 = await publisher.publish_sensor_data(device_id2, sensor_data2)
        
        if success2:
            logger.info("Successfully published data for second device!")
            
        # Wait and get updated stats
        await asyncio.sleep(1)
        stats = publisher.get_stats()
        logger.info(f"Updated stats: {json.dumps(stats, indent=2)}")
        
        # Test removing a device
        logger.info("Removing discovery for first device...")
        await publisher.remove_device_discovery(device_id)
        
        # Final stats
        stats = publisher.get_stats()
        logger.info(f"Final stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        # Stop publisher
        await publisher.stop()
        logger.info("MQTT publisher stopped")


if __name__ == "__main__":
    asyncio.run(test_mqtt_publisher())