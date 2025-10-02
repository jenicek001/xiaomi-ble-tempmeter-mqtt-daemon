#!/usr/bin/env python3
"""
Test script to verify friendly_name functionality in the MQTT daemon.
"""

import asyncio
import logging
from datetime import datetime, timezone
from src.config_manager import ConfigManager
from src.sensor_cache import SensorCache
from src.bluetooth_manager import SensorData

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_friendly_name_config():
    """Test that friendly names are loaded from config correctly."""
    logger.info("=== Testing Friendly Name Configuration ===")
    
    # Load config
    config_manager = ConfigManager("config/config.yaml")
    config = config_manager.get_config()
    
    logger.info(f"Loaded {len(config.devices.static_devices)} static devices:")
    for device in config.devices.static_devices:
        logger.info(f"  MAC: {device.mac}, Friendly Name: {device.friendly_name}")
    
    # Test sensor cache with friendly names
    logger.info("\n=== Testing Sensor Cache ===")
    bluetooth_config = config.bluetooth.model_dump()
    static_devices_dicts = [
        device.model_dump() if hasattr(device, 'model_dump') else device
        for device in config.devices.static_devices
    ]
    bluetooth_config['static_devices'] = static_devices_dicts
    
    cache_config = bluetooth_config.copy()
    cache_config.update({
        'temperature_threshold': config.thresholds.temperature,
        'humidity_threshold': config.thresholds.humidity,
        'publish_interval': config.mqtt.publish_interval
    })
    
    sensor_cache = SensorCache(cache_config)
    logger.info(f"Sensor cache loaded with {len(sensor_cache.friendly_names)} friendly names")
    
    # Test device discovery with friendly names
    for device in config.devices.static_devices:
        mac = device.mac.upper()
        record = sensor_cache.discover_device(mac)
        logger.info(f"Device {mac}: friendly_name = '{record.friendly_name}'")
    
    # Test SensorData.to_dict() with friendly_name
    logger.info("\n=== Testing SensorData.to_dict() ===")
    test_sensor_data = SensorData(
        temperature=23.5,
        humidity=45.2,
        battery=78,
        last_seen=datetime.now(tz=timezone.utc).astimezone(),
        rssi=-70
    )
    
    # Without friendly name
    dict_without = test_sensor_data.to_dict()
    logger.info(f"Without friendly_name: {dict_without}")
    assert 'friendly_name' not in dict_without
    
    # With friendly name
    dict_with = test_sensor_data.to_dict(friendly_name="Living Room", message_type="threshold-based")
    logger.info(f"With friendly_name: {dict_with}")
    assert dict_with['friendly_name'] == "Living Room"
    assert dict_with['message_type'] == "threshold-based"
    
    logger.info("\n=== All Tests Passed! ===")


if __name__ == "__main__":
    asyncio.run(test_friendly_name_config())
