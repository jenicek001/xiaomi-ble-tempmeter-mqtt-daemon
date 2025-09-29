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
from datetime import datetime, timezone
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
    last_seen: datetime  # Should be timezone-aware
    rssi: Optional[int] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "voltage": self.voltage,
            "last_seen": self.last_seen.isoformat(),  # includes TZ info
            "rssi": self.rssi
        }


class BluetoothManager:
    """Handles Bluetooth Low Energy connections and data reading from Xiaomi devices"""
    
    def __init__(self, config: dict):
        """Initialize the Bluetooth manager with configuration"""
        self.config = config
        self.retry_attempts = config.get('retry_attempts', 3)
        self.connection_timeout = config.get('connection_timeout', 10)
        self._rssi_cache = {}  # Cache for last known RSSI values per MAC
        logger.debug(f"Initializing BluetoothManager with config: {config}")
        
    def _calculate_aaa_battery_percentage(self, voltage: float) -> int:
        """
        Calculate battery percentage for AAA alkaline battery based on voltage.
        
        AAA alkaline battery voltage ranges:
        - Fresh/Full: 1.65V (100%)
        - Good: 1.5V (90%) 
        - Usable: 1.3V (50%)
        - Low: 1.2V (20%)
        - Nearly dead: 1.0V (5%)
        - Dead: 0.9V (0%)
        """
        if voltage >= 1.65:
            return 100
        elif voltage >= 1.5:
            # Linear interpolation between 1.5V (90%) and 1.65V (100%)
            return int(90 + (voltage - 1.5) / (1.65 - 1.5) * 10)
        elif voltage >= 1.3:
            # Linear interpolation between 1.3V (50%) and 1.5V (90%)
            return int(50 + (voltage - 1.3) / (1.5 - 1.3) * 40)
        elif voltage >= 1.2:
            # Linear interpolation between 1.2V (20%) and 1.3V (50%)
            return int(20 + (voltage - 1.2) / (1.3 - 1.2) * 30)
        elif voltage >= 1.0:
            # Linear interpolation between 1.0V (5%) and 1.2V (20%)
            return int(5 + (voltage - 1.0) / (1.2 - 1.0) * 15)
        elif voltage >= 0.9:
            # Linear interpolation between 0.9V (0%) and 1.0V (5%)
            return int((voltage - 0.9) / (1.0 - 0.9) * 5)
        else:
            # Below 0.9V is completely dead
            return 0
        
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
                    
                    # Try to get current RSSI if supported by backend
                    try:
                        current_rssi = None
                        
                        # Try different methods to get RSSI
                        if hasattr(client, 'get_rssi'):
                            current_rssi = await client.get_rssi()
                        elif hasattr(client, '_device') and hasattr(client._device, 'rssi'):
                            current_rssi = client._device.rssi
                        elif hasattr(client, '_backend') and hasattr(client._backend, 'get_rssi'):
                            current_rssi = await client._backend.get_rssi()
                        
                        if current_rssi is not None:
                            self._rssi_cache[mac_address] = current_rssi
                            logger.debug(f"Updated RSSI cache: {current_rssi} for {mac_address}")
                        else:
                            logger.debug(f"Could not retrieve RSSI from connected client for {mac_address}")
                    except Exception as e:
                        logger.debug(f"Could not get RSSI from connected device: {e}")
                    
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
                                    
                                    # ASCII format doesn't include voltage/battery, use reasonable AAA estimates
                                    voltage = 1.4  # Assume good AAA alkaline battery (between 1.3-1.5V)
                                    battery = self._calculate_aaa_battery_percentage(voltage)  # ~70%
                                    
                                    # Get cached RSSI
                                    cached_rssi = self._rssi_cache.get(mac_address)
                                    logger.debug(f"RSSI cache lookup for {mac_address}: {cached_rssi}")
                                    logger.debug(f"Current RSSI cache: {dict(self._rssi_cache)}")
                                    
                                    received_data = SensorData(
                                        temperature=temperature,
                                        humidity=humidity,
                                        battery=battery,
                                        voltage=voltage,
                                        last_seen=datetime.now(tz=timezone.utc).astimezone(),
                                        rssi=cached_rssi
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
                                
                                # Calculate battery percentage for AAA alkaline battery
                                # Fresh: 1.65V (100%), Good: 1.5V (90%), Low: 1.2V (20%), Dead: 0.9V (0%)
                                battery = self._calculate_aaa_battery_percentage(voltage)
                                
                                # Get cached RSSI
                                cached_rssi = self._rssi_cache.get(mac_address)
                                logger.debug(f"RSSI cache lookup for {mac_address}: {cached_rssi}")
                                logger.debug(f"Current RSSI cache: {dict(self._rssi_cache)}")
                                
                                received_data = SensorData(
                                    temperature=temperature,
                                    humidity=humidity,
                                    battery=battery,
                                    voltage=voltage,
                                    last_seen=datetime.now(tz=timezone.utc).astimezone(),
                                    rssi=cached_rssi
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
        
        # Try to find devices by scanning for advertisements with callback
        discovered_devices = {}
        
        def detection_callback(device, advertisement_data):
            """Callback to capture devices with RSSI during scanning"""
            if device.name and device.name in ["MJ_HT_V1", "LYWSD03MMC", "LYWSDCGQ/01ZM"]:
                # Get RSSI from advertisement data
                rssi_value = advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None
                
                # Also try to get from device object
                if rssi_value is None:
                    for attr in ['rssi', 'RSSI', '_rssi']:
                        if hasattr(device, attr):
                            rssi_value = getattr(device, attr)
                            break
                
                # Cache RSSI value if available
                if rssi_value is not None:
                    self._rssi_cache[device.address] = rssi_value
                    logger.debug(f"Cached RSSI {rssi_value} for device {device.address} during scan")
                
                discovered_devices[device.address] = {
                    "mac": device.address,
                    "name": device.name,
                    "mode": "LYWSDCGQ",  # Default mode for these devices
                    "rssi": rssi_value
                }
                logger.info(f"Found Xiaomi device during scan: {discovered_devices[device.address]}")
        
        try:
            logger.debug("Scanning for BLE devices with callback...")
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(10.0)  # Scan for 10 seconds
            await scanner.stop()
            
            # Convert to list
            for device_info in discovered_devices.values():
                discovered.append(device_info)
                
        except Exception as scan_error:
            logger.warning(f"Callback scanning failed: {scan_error}, falling back to discover method")
            
            # Fallback to discover method
            try:
                logger.debug("Scanning for BLE devices...")
                devices = await BleakScanner.discover(timeout=10.0)
                
                for device in devices:
                    # Check if it's a known Xiaomi temperature sensor
                    if device.name and device.name in ["MJ_HT_V1", "LYWSD03MMC", "LYWSDCGQ/01ZM"]:
                        # Try different ways to get RSSI value
                        rssi_value = None
                        for attr in ['rssi', 'RSSI', '_rssi']:
                            if hasattr(device, attr):
                                rssi_value = getattr(device, attr)
                                break
                        
                        # Also try metadata/details dictionary
                        if rssi_value is None and hasattr(device, 'metadata'):
                            rssi_value = device.metadata.get('rssi') or device.metadata.get('RSSI')
                        if rssi_value is None and hasattr(device, 'details'):
                            rssi_value = device.details.get('rssi') or device.details.get('RSSI')
                        
                        # Cache RSSI value if available
                        if rssi_value is not None:
                            self._rssi_cache[device.address] = rssi_value
                            logger.debug(f"Cached RSSI {rssi_value} for device {device.address}")
                        else:
                            logger.debug(f"No RSSI found for device {device.address}, available attributes: {dir(device)}")
                        
                        device_info = {
                            "mac": device.address,
                            "name": device.name,
                            "mode": "LYWSDCGQ",  # Default mode for these devices
                            "rssi": rssi_value
                        }
                        discovered.append(device_info)
                        logger.info(f"Found Xiaomi device: {device_info}")
            
            except Exception as discover_error:
                logger.error(f"Both scanning methods failed: {discover_error}")
        
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
                        "rssi": self._rssi_cache.get(static_device['mac'])
                    }
                    # Add if not already discovered
                    if not any(d['mac'] == device_info['mac'] for d in discovered):
                        discovered.append(device_info)
                        logger.info(f"Added static device: {device_info}")
        
        logger.info(f"Discovery complete. Found {len(discovered)} devices")
        return discovered

    def get_cached_rssi(self, mac_address: str) -> Optional[int]:
        """Get the last known RSSI value for a device"""
        return self._rssi_cache.get(mac_address)
    
    def update_rssi_cache(self, mac_address: str, rssi: int):
        """Update the RSSI cache for a device"""
        self._rssi_cache[mac_address] = rssi
        logger.debug(f"Updated RSSI cache: {rssi} dBm for {mac_address}")
    
    def clear_rssi_cache(self):
        """Clear all cached RSSI values"""
        self._rssi_cache.clear()
        logger.debug("RSSI cache cleared")

    async def cleanup(self):
        """Clean up resources"""
        self.clear_rssi_cache()
        logger.info("Bluetooth cleanup completed")


# Compatibility alias for existing code
def read_device_data(self, mac_address: str, device_mode: str = "LYWSDCGQ/01ZM", scan_timeout: int = 30):
    """Compatibility wrapper - redirect to new method"""
    return self.read_sensor_data(mac_address, scan_timeout)

# Add compatibility method to class
BluetoothManager.read_device_data = read_device_data