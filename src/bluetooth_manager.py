"""
Bluetooth Manager for Xiaomi Mijia devices.

This module handles BLE communication with Xiaomi thermometers using bleak.
Ported from the original mitemp_bt2 implementation by @leonxi.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

logger = logging.getLogger(__name__)

# Xiaomi device modes and their local names
SUPPORTED_DEVICES = {
    "LYWSD03MMC": "Mijia BLE Temperature Hygrometer 2",
    "LYWSDCGQ/01ZM": "Original Mijia BLE Temperature Hygrometer"
}

# BLE characteristics handles
NOTIFY_HANDLE = 0x0038  # Enable notifications for temp/humidity/battery
CONFIG_HANDLE = 0x0046  # Device configuration (LYWSD03MMC specific)


@dataclass
class SensorData:
    """Container for sensor measurement data."""
    temperature: float
    humidity: int
    battery: int
    voltage: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format for MQTT publishing."""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "last_seen": self.timestamp.isoformat()
        }


class BluetoothManager:
    """Manages Bluetooth Low Energy communication with Xiaomi devices."""
    
    def __init__(self, config: Dict):
        """Initialize Bluetooth manager with configuration."""
        self.config = config
        self.adapter = config.get("adapter", 0)
        self.scan_interval = config.get("scan_interval", 300)
        self.connection_timeout = config.get("connection_timeout", 10)
        self.retry_attempts = config.get("retry_attempts", 3)
        
        # Track discovered devices to avoid duplicates
        self._discovered_devices: Set[str] = set()
        
    async def discover_devices(self) -> List[Dict]:
        """
        Discover Xiaomi Mijia thermometers via BLE scanning.
        
        Returns:
            List of discovered devices with MAC, name, and mode.
        """
        logger.info("Starting BLE device discovery...")
        discovered = []
        
        try:
            # Scan for BLE devices
            devices = await BleakScanner.discover(timeout=10.0)
            
            for device in devices:
                if device.name and device.name in SUPPORTED_DEVICES:
                    device_info = {
                        "mac": device.address,
                        "name": device.name, 
                        "mode": device.name,
                        "rssi": device.rssi if hasattr(device, 'rssi') else None,
                        "discovered_at": datetime.now().isoformat()
                    }
                    
                    # Only add if not already discovered
                    if device.address not in self._discovered_devices:
                        self._discovered_devices.add(device.address)
                        discovered.append(device_info)
                        logger.info(f"Discovered Xiaomi device: {device.name} ({device.address})")
                    
        except Exception as e:
            logger.error(f"Error during device discovery: {e}")
            
        logger.info(f"Discovery completed. Found {len(discovered)} new devices.")
        return discovered
        
    async def read_device_data(self, mac_address: str, device_mode: str) -> Optional[SensorData]:
        """
        Read sensor data from a specific device.
        
        Args:
            mac_address: BLE MAC address of the device
            device_mode: Device type (LYWSD03MMC or LYWSDCGQ/01ZM)
            
        Returns:
            SensorData object with temperature, humidity, and battery data
        """
        logger.debug(f"Reading data from device {mac_address} (mode: {device_mode})")
        
        for attempt in range(self.retry_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1} for device {mac_address}")
                    await asyncio.sleep(5)  # Wait before retry
                
                async with BleakClient(mac_address, timeout=self.connection_timeout) as client:
                    if not client.is_connected:
                        logger.warning(f"Failed to connect to {mac_address}")
                        continue
                        
                    logger.debug(f"Connected to {mac_address}")
                    
                    # Set up notification handling
                    sensor_data = None
                    notification_received = asyncio.Event()
                    
                    def notification_handler(sender, data: bytearray):
                        """Handle incoming sensor data notifications."""
                        nonlocal sensor_data
                        try:
                            sensor_data = self._parse_notification_data(data)
                            notification_received.set()
                        except Exception as e:
                            logger.error(f"Error parsing notification data: {e}")
                    
                    # Enable notifications for sensor data
                    await client.start_notify(NOTIFY_HANDLE, notification_handler)
                    
                    # For LYWSD03MMC, send device-specific configuration
                    if device_mode == "LYWSD03MMC":
                        await client.write_gatt_char(CONFIG_HANDLE, b"\xf4\x01\x00")
                    
                    # Wait for notification data (with timeout)
                    try:
                        await asyncio.wait_for(notification_received.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout waiting for data from {mac_address}")
                        continue
                        
                    # Stop notifications
                    await client.stop_notify(NOTIFY_HANDLE)
                    
                    if sensor_data:
                        logger.debug(f"Successfully read data from {mac_address}: "
                                   f"T={sensor_data.temperature}°C, H={sensor_data.humidity}%, "
                                   f"B={sensor_data.battery}%")
                        return sensor_data
                    
            except Exception as e:
                logger.error(f"Error reading from device {mac_address} (attempt {attempt + 1}): {e}")
                
        logger.error(f"Failed to read data from {mac_address} after {self.retry_attempts} attempts")
        return None
        
    def _parse_notification_data(self, data: bytearray) -> SensorData:
        """
        Parse the 5-byte notification data from Xiaomi devices.
        
        Data format:
        - Bytes 0-1: Temperature (signed 16-bit, divide by 100)
        - Byte 2: Humidity (8-bit)
        - Bytes 3-4: Battery voltage (16-bit, divide by 1000)
        
        Args:
            data: Raw notification data
            
        Returns:
            Parsed SensorData object
        """
        if len(data) != 5:
            raise ValueError(f"Invalid data length: expected 5 bytes, got {len(data)}")
            
        # Parse temperature (signed 16-bit little-endian)
        temp_raw = int.from_bytes(data[0:2], byteorder="little", signed=True)
        temperature = round(temp_raw / 100.0, 1)
        
        # Parse humidity (8-bit)
        humidity = int(data[2])
        
        # Parse battery voltage (16-bit little-endian)
        voltage_raw = int.from_bytes(data[3:5], byteorder="little")
        voltage = voltage_raw / 1000.0
        
        # Calculate battery percentage
        # Formula from original implementation: 3.1V+ = 100%, 2.1V = 0%
        battery_percentage = min(int(round((voltage - 2.1) * 100, 0)), 100)
        battery_percentage = max(battery_percentage, 0)  # Ensure non-negative
        
        return SensorData(
            temperature=temperature,
            humidity=humidity,
            battery=battery_percentage,
            voltage=voltage,
            timestamp=datetime.now()
        )
        
    async def test_device_connection(self, mac_address: str) -> bool:
        """
        Test if a device is reachable and responsive.
        
        Args:
            mac_address: BLE MAC address to test
            
        Returns:
            True if device responds, False otherwise
        """
        try:
            async with BleakClient(mac_address, timeout=5.0) as client:
                return client.is_connected
        except Exception as e:
            logger.debug(f"Device {mac_address} not reachable: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up BLE resources."""
        logger.info("Cleaning up Bluetooth resources...")
        # Clear discovered devices cache
        self._discovered_devices.clear()
        logger.info("Bluetooth cleanup completed")