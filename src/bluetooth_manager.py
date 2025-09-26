#!/usr/bin/env python3
"""
Bluetooth Manager - GATT connection-based implementation (correct approach)
Based on the original Home Assistan                    # Start notifications and wait for data
                    await client.start_notify(notify_char, notification_handler)
                    logger.debug(f"Started notifications, waiting up to {scan_timeout}s for data...")
                    
                    # Wait for notification
                    start_time = asyncio.get_event_loop().time()
                    while received_data is None:
                        await asyncio.sleep(0.1)
                        
                        # Check timeout
                        if (asyncio.get_event_loop().time() - start_time) > scan_timeout:
                            logger.warning(f"Timeout waiting for notification from {mac_address}")
                            break
                    
                    await client.stop_notify(notify_char)emp_bt2
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Sensor data from Xiaomi device"""
    temperature: float
    humidity: float
    battery: int
    voltage: float
    timestamp: datetime
    rssi: Optional[int] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "voltage": self.voltage,
            "timestamp": self.timestamp.isoformat(),
            "rssi": self.rssi
        }


class BluetoothManager:
    """Handles Bluetooth Low Energy connections and data reading from Xiaomi devices"""
    
    def __init__(self, config: dict):
        """Initialize the Bluetooth manager with configuration"""
        self.config = config
        self.retry_attempts = config.get('retry_attempts', 3)
        self.connection_timeout = config.get('connection_timeout', 10)
        logger.debug(f"Initializing BluetoothManager with config: {config}")
        
    async def read_sensor_data(self, mac_address: str, scan_timeout: int = 10) -> Optional[SensorData]:
        """
        Read sensor data from Xiaomi device using GATT connection (correct protocol).
        
        Args:
            mac_address: Device MAC address
            scan_timeout: Timeout for GATT operations
            
        Returns:
            SensorData object with temperature, humidity, battery and voltage
        """
        logger.info(f"Reading sensor data from {mac_address}")
        
        for attempt in range(self.retry_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Connection attempt {attempt + 1} for device {mac_address}")
                    await asyncio.sleep(5)  # Wait between retries
                
                # Connect to device
                async with BleakClient(mac_address, timeout=scan_timeout) as client:
                    logger.debug(f"Connected to {mac_address}")
                    
                    # Find the correct characteristic by service and char UUID
                    # Service: 226c0000-6476-4566-7562-66734470666d
                    # Char: 226caa55-6476-4566-7562-66734470666d (notify)
                    notify_char = None
                    for service in client.services:
                        if service.uuid.lower() == "226c0000-6476-4566-7562-66734470666d":
                            for char in service.characteristics:
                                if char.uuid.lower() == "226caa55-6476-4566-7562-66734470666d":
                                    notify_char = char
                                    break
                            if notify_char:
                                break
                    
                    if not notify_char:
                        raise Exception("Temperature/Humidity notification characteristic not found")
                    
                    logger.debug(f"Found notification characteristic: {notify_char.uuid} handle {notify_char.handle}")
                    
                    # Enable notifications for temperature, humidity and battery
                    await client.write_gatt_char(notify_char, b"\x01\x00")
                    logger.debug(f"Enabled notifications on characteristic {notify_char.uuid}")
                    
                    # Configure device for LYWSDCGQ/01ZM mode (if needed)
                    # This is optional for LYWSDCGQ/01ZM sensors, skip for now
                    logger.debug("Skipping optional device configuration")
                    
                    # Set up data collection
                    received_data = None
                    
                    def notification_handler(sender, data: bytearray):
                        nonlocal received_data
                        logger.debug(f"Received notification: {data.hex()}")
                        
                        try:
                            # Try ASCII format first (some LYWSDCGQ firmware)
                            try:
                                text_data = data.decode('ascii').rstrip('\x00')
                                logger.debug(f"ASCII data: {text_data}")
                                
                                # Parse "T=24.9 H=48.3" format
                                import re
                                temp_match = re.search(r'T=(-?\d+\.?\d*)', text_data)
                                humid_match = re.search(r'H=(-?\d+\.?\d*)', text_data)
                                
                                if temp_match and humid_match:
                                    temperature = round(float(temp_match.group(1)), 1)
                                    humidity = round(float(humid_match.group(1)), 1)
                                    
                                    # ASCII format doesn't include voltage/battery, use defaults
                                    voltage = 3.0  # Assume good battery
                                    battery = 80   # Assume 80% battery
                                    
                                    received_data = SensorData(
                                        temperature=temperature,
                                        humidity=humidity,
                                        battery=battery,
                                        voltage=voltage,
                                        timestamp=datetime.now()
                                    )
                                    
                                    logger.debug(f"Parsed ASCII: T={temperature}°C, H={humidity}%, B={battery}%, V={voltage:.3f}V")
                                    return
                            except (UnicodeDecodeError, AttributeError, ValueError):
                                pass  # Not ASCII format, try binary
                            
                            # Try binary format (original Xiaomi protocol)
                            if len(data) >= 5:
                                # Parse 5-byte notification
                                temp_raw = int.from_bytes(data[0:2], byteorder="little", signed=True)
                                temperature = round(temp_raw / 100.0, 1)  # Scale: /100
                                
                                humidity = round(int.from_bytes(data[2:3], byteorder="little"), 1)
                                
                                voltage_raw = int.from_bytes(data[3:5], byteorder="little")
                                voltage = voltage_raw / 1000.0  # Scale: /1000
                                
                                # Calculate battery percentage (2.1V = 0%, 3.1V+ = 100%)
                                battery = max(0, min(100, int(round((voltage - 2.1) * 100))))
                                
                                received_data = SensorData(
                                    temperature=temperature,
                                    humidity=humidity,
                                    battery=battery,
                                    voltage=voltage,
                                    timestamp=datetime.now()
                                )
                                
                                logger.debug(f"Parsed binary: T={temperature}°C, H={humidity}%, B={battery}%, V={voltage:.3f}V")
                            else:
                                logger.warning(f"Unexpected notification length: {len(data)} bytes")
                                
                        except Exception as e:
                            logger.error(f"Error parsing notification data: {e}")
                    
                    # Start notifications and wait for data
                    await client.start_notify(notify_char, notification_handler)
                    logger.debug(f"Started notifications, waiting up to {scan_timeout}s for data...")
                    
                    # Wait for notification
                    start_time = asyncio.get_event_loop().time()
                    while received_data is None:
                        await asyncio.sleep(0.1)
                        
                        # Check timeout
                        if (asyncio.get_event_loop().time() - start_time) > scan_timeout:
                            logger.warning(f"Timeout waiting for notification from {mac_address}")
                            break
                    
                    # Stop notifications  
                    await client.stop_notify(notify_char)
                    
                    if received_data:
                        logger.info(f"Successfully read sensor data from {mac_address}")
                        logger.info(f"Final result: T={received_data.temperature}°C, H={received_data.humidity}%, "
                                  f"B={received_data.battery}%, V={received_data.voltage:.3f}V")
                        return received_data
                    
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed for {mac_address}: {e}")
                if attempt == self.retry_attempts - 1:
                    logger.error(f"All {self.retry_attempts} connection attempts failed for {mac_address}")
        
        return None

    async def discover_devices(self) -> list:
        """Discover available Xiaomi temperature sensors"""
        logger.info("Discovering Xiaomi temperature sensors...")
        
        discovered = []
        
        # Try to find devices by scanning for advertisements
        try:
            logger.debug("Scanning for BLE devices...")
            devices = await BleakScanner.discover(timeout=10.0)
            
            for device in devices:
                # Check if it's a known Xiaomi temperature sensor
                if device.name and device.name in ["MJ_HT_V1", "LYWSD03MMC", "LYWSDCGQ/01ZM"]:
                    device_info = {
                        "mac": device.address,
                        "name": device.name,
                        "mode": "LYWSDCGQ",  # Default mode for these devices
                        "rssi": getattr(device, 'rssi', None)
                    }
                    discovered.append(device_info)
                    logger.info(f"Found Xiaomi device: {device_info}")
        
        except Exception as e:
            logger.error(f"Error during device discovery: {e}")
        
        # Also add configured static devices from config if available
        if hasattr(self, 'config') and 'static_devices' in self.config:
            for static_device in self.config.get('static_devices', []):
                if static_device.get('enabled', True):
                    device_info = {
                        "mac": static_device['mac'],
                        "name": static_device.get('name', 'Unknown'),
                        "mode": static_device.get('mode', 'LYWSDCGQ'),
                        "rssi": None
                    }
                    # Add if not already discovered
                    if not any(d['mac'] == device_info['mac'] for d in discovered):
                        discovered.append(device_info)
                        logger.info(f"Added static device: {device_info}")
        
        logger.info(f"Discovery complete. Found {len(discovered)} devices")
        return discovered

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Bluetooth cleanup completed")


# Compatibility alias for existing code
def read_device_data(self, mac_address: str, device_mode: str = "LYWSDCGQ/01ZM", scan_timeout: int = 30):
    """Compatibility wrapper - redirect to new method"""
    return self.read_sensor_data(mac_address, scan_timeout)

# Add compatibility method to class
BluetoothManager.read_device_data = read_device_data