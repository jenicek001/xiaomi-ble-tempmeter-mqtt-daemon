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
import struct
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner
from pydantic import BaseModel, Field

try:
    from .constants import interpret_rssi
except ImportError:
    from constants import interpret_rssi

logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Sensor data from Xiaomi device"""
    temperature: float
    humidity: float
    battery: int
    last_seen: datetime  # Should be timezone-aware
    rssi: Optional[int] = None
    
    def to_dict(self, friendly_name: Optional[str] = None, message_type: str = "periodic"):
        """Convert to dictionary for JSON serialization
        
        Args:
            friendly_name: Optional user-friendly name for the device
            message_type: Type of message ("periodic" or "threshold-based")
        """
        result = {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "last_seen": self.last_seen.isoformat(),  # includes TZ info
            "rssi": self.rssi,
            "signal": interpret_rssi(self.rssi),
            "message_type": message_type
        }
        if friendly_name:
            result["friendly_name"] = friendly_name
        return result


class BluetoothManager:
    """Handles Bluetooth Low Energy connections and data reading from Xiaomi devices"""
    
    def __init__(self, config: dict):
        """Initialize the Bluetooth manager with configuration"""
        self.config = config
        self.retry_attempts = config.get('retry_attempts', 3)
        self.connection_timeout = config.get('connection_timeout', 10)
        self._rssi_cache = {}  # Cache for last known RSSI values per MAC
        logger.debug(f"Initializing BluetoothManager with config: {config}")
        
    def _parse_mibeacon_advertisement(self, service_data: bytes) -> Optional[dict]:
        """
        Parse MiBeacon advertisement data from LYWSDCGQ devices.
        
        Args:
            service_data: Raw service data bytes from UUID 0000fe95-0000-1000-8000-00805f9b34fb
            
        Returns:
            Dictionary with parsed sensor data or None if parsing fails
        """
        try:
            if len(service_data) < 14:
                return None
                
            # Validate MiBeacon header
            if service_data[:4] != b'\x50\x20\xaa\x01':
                return None
                
            logger.debug(f"MiBeacon packet: {service_data.hex()}")
            
            result = {}
            
            if len(service_data) == 18:
                # 18-byte format: Temperature + Humidity (type 0x0d) 
                data_type = service_data[11]
                payload_len = service_data[13]
                
                if data_type == 0x0d and payload_len == 4:
                    # Parse temp (2 bytes) + humidity (2 bytes), little-endian
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    humid_raw = struct.unpack('<H', service_data[16:18])[0]
                    
                    result['temperature'] = round(temp_raw / 10.0, 1)
                    result['humidity'] = round(humid_raw / 10.0, 1)
                    
            elif len(service_data) == 16:
                # 16-byte format: Temperature only (0x04) or Humidity only (0x06)
                data_type = service_data[11] 
                payload_len = service_data[13]
                
                if data_type == 0x04 and payload_len >= 2:
                    # Temperature only
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    result['temperature'] = round(temp_raw / 10.0, 1)
                elif data_type == 0x06 and payload_len >= 2:
                    # Humidity only
                    humid_raw = struct.unpack('<H', service_data[14:16])[0]
                    result['humidity'] = round(humid_raw / 10.0, 1)
                    
            elif len(service_data) == 15:
                # 15-byte format: Battery only (type 0x0a)
                data_type = service_data[11]
                payload_len = service_data[13]
                
                if data_type == 0x0a and payload_len >= 1:
                    result['battery'] = service_data[14]
                    
            return result if result else None
            
        except Exception as e:
            logger.debug(f"Failed to parse MiBeacon data: {e}")
            return None
    
    async def read_sensor_data_advertisement(self, mac_address: str, scan_timeout: int = 30) -> Optional[SensorData]:
        """
        Read sensor data from LYWSDCGQ device using advertisement scanning (MiBeacon protocol).
        
        This method is specifically for LYWSDCGQ/01ZM devices that broadcast sensor data
        in BLE advertisements using the MiBeacon protocol.
        
        Args:
            mac_address: Device MAC address
            scan_timeout: How long to scan for advertisements
            
        Returns:
            SensorData object with temperature, humidity, battery and voltage
        """
        logger.info(f"Reading sensor data via advertisements from {mac_address}")
        
        # Data collection state
        collected_data = {}
        last_rssi = None
        last_seen = None
        
        def advertisement_callback(device, advertisement_data):
            nonlocal collected_data, last_rssi, last_seen
            
            # Filter for our target device
            if device.address.upper() != mac_address.upper():
                return
                
            # Update RSSI and timestamp
            if hasattr(advertisement_data, 'rssi'):
                last_rssi = advertisement_data.rssi
                self._rssi_cache[mac_address] = last_rssi
            last_seen = datetime.now(tz=timezone.utc).astimezone()
            
            # Look for MiBeacon service data
            service_data_dict = getattr(advertisement_data, 'service_data', {})
            xiaomi_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
            
            if xiaomi_uuid in service_data_dict:
                service_data = service_data_dict[xiaomi_uuid]
                parsed = self._parse_mibeacon_advertisement(service_data)
                
                if parsed:
                    collected_data.update(parsed)
                    logger.debug(f"Advertisement update: {parsed}")
        
        try:
            # Start scanning with callback
            scanner = BleakScanner(detection_callback=advertisement_callback)
            await scanner.start()
            
            logger.debug(f"Scanning for advertisements from {mac_address} for {scan_timeout}s...")
            await asyncio.sleep(scan_timeout)
            
            await scanner.stop()
            
            # Check if we have complete data (temperature, humidity, battery)
            if ('temperature' in collected_data and 
                'humidity' in collected_data and 
                'battery' in collected_data):
                
                sensor_data = SensorData(
                    temperature=collected_data['temperature'],
                    humidity=collected_data['humidity'],
                    battery=collected_data['battery'],
                    last_seen=last_seen,  # Only use real timestamp from advertisement
                    rssi=last_rssi
                )
                
                logger.info(f"Successfully read complete advertisement data from {mac_address}")
                logger.info(f"Result: T={sensor_data.temperature}°C, H={sensor_data.humidity}%, "
                          f"B={sensor_data.battery}%, RSSI={sensor_data.rssi}")
                return sensor_data
            else:
                logger.warning(f"Incomplete data from advertisements (need temp+humidity+battery): {collected_data}")
                return None
                
        except Exception as e:
            logger.error(f"Advertisement scanning failed for {mac_address}: {e}")
            return None
    
    async def _detect_device_type(self, mac_address: str) -> str:
        """
        Detect device type by scanning for device name in advertisements.
        
        Returns:
            Device name like "MJ_HT_V1" (LYWSDCGQ), "LYWSD03MMC", etc.
        """
        detected_name = None
        
        def detection_callback(device, advertisement_data):
            nonlocal detected_name
            if device.address.upper() == mac_address.upper() and device.name:
                detected_name = device.name
        
        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(3.0)  # Quick scan for device name
            await scanner.stop()
            
            return detected_name or "Unknown"
            
        except Exception as e:
            logger.debug(f"Device detection failed: {e}")
            return "Unknown"
        
    async def read_sensor_data(self, mac_address: str, scan_timeout: int = 10) -> Optional[SensorData]:
        """
        Read sensor data from Xiaomi device using the appropriate method.
        
        For LYWSDCGQ/01ZM (MJ_HT_V1) devices: Uses advertisement-based MiBeacon protocol
        For LYWSD03MMC devices: Uses GATT connection protocol
        
        Args:
            mac_address: Device MAC address
            scan_timeout: Timeout for operations
            
        Returns:
            SensorData object with temperature, humidity, battery and voltage
        """
        logger.info(f"Reading sensor data from {mac_address}")
        
        # Detect device type to choose appropriate communication method
        device_type = await self._detect_device_type(mac_address)
        logger.debug(f"Detected device type: {device_type} for {mac_address}")
        
        # Use advertisement-based approach for all devices (MiBeacon only)
        logger.info(f"Using advertisement-based communication for device {mac_address}")
        return await self.read_sensor_data_advertisement(mac_address, scan_timeout)
    


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
                
                # Check if this is a new device or RSSI update
                is_new_device = device.address not in discovered_devices
                
                # Update device info (overwrites previous entry with updated RSSI)
                discovered_devices[device.address] = {
                    "mac": device.address,
                    "name": device.name,
                    "mode": "LYWSDCGQ",  # Default mode for these devices
                    "rssi": rssi_value
                }
                
                # Cache RSSI value if available
                if rssi_value is not None:
                    self._rssi_cache[device.address] = rssi_value
                
                # Log appropriately based on whether it's new or an update
                if is_new_device:
                    logger.info(f"Found Xiaomi device: {device.address} ({device.name}, RSSI: {rssi_value} dBm)")
                else:
                    logger.debug(f"Updated RSSI for {device.address}: {rssi_value} dBm")
        
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