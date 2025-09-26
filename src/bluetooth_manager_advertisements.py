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
    rssi: Optional[int] = None  # Signal strength in dBm
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format for MQTT publishing."""
        result = {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "last_seen": self.timestamp.isoformat()
        }
        
        if self.rssi is not None:
            result["rssi"] = self.rssi
            
            # Add signal quality interpretation
            if self.rssi >= -30:
                result["signal_quality"] = "excellent"
            elif self.rssi >= -67:
                result["signal_quality"] = "very_good"
            elif self.rssi >= -70:
                result["signal_quality"] = "good"
            elif self.rssi >= -80:
                result["signal_quality"] = "fair"
            elif self.rssi >= -90:
                result["signal_quality"] = "weak"
            else:
                result["signal_quality"] = "very_weak"
        
        return result


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
        Read sensor data from a specific device using advertisement scanning.
        
        This method uses passive scanning to read sensor data from Xiaomi device
        advertisements, which is more reliable than BLE connections.
        
        Args:
            mac_address: BLE MAC address of the device
            device_mode: Device type (LYWSD03MMC or LYWSDCGQ/01ZM)
            
        Returns:
            SensorData object with temperature, humidity, and battery data
        """
        logger.debug(f"Scanning for advertisement data from {mac_address} (mode: {device_mode})")
        
        for attempt in range(self.retry_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Advertisement scan attempt {attempt + 1} for device {mac_address}")
                    await asyncio.sleep(2)  # Short wait between attempts
                
                # Use advertisement scanning instead of connection
                sensor_data = None
                scan_timeout = min(30, self.connection_timeout * 2)  # Max 30 seconds
                
                def advertisement_callback(device: BLEDevice, advertisement_data):
                    """Handle advertisement data from target device."""
                    nonlocal sensor_data
                    
                    if device.address.upper() == mac_address.upper():
                        rssi = advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None
                        logger.debug(f"Received advertisement from {device.address}, RSSI: {rssi} dBm")
                        
                        # Parse Xiaomi service data (UUID: 0000fe95-0000-1000-8000-00805f9b34fb)
                        xiaomi_service_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
                        
                        if xiaomi_service_uuid in advertisement_data.service_data:
                            service_data = advertisement_data.service_data[xiaomi_service_uuid]
                            logger.debug(f"Xiaomi service data: {service_data.hex()}")
                            
                            try:
                                parsed_data = self._parse_xiaomi_advertisement(service_data, device.address, rssi)
                                if parsed_data:
                                    sensor_data = parsed_data
                                    logger.debug(f"Successfully parsed sensor data with RSSI: {sensor_data}")
                            except Exception as e:
                                logger.error(f"Error parsing Xiaomi advertisement: {e}")
                
                # Perform the scan
                logger.debug(f"Starting {scan_timeout}s advertisement scan for {mac_address}")
                
                scanner = BleakScanner(detection_callback=advertisement_callback)
                await scanner.start()
                
                # Wait for data collection - LYWSDCGQ/01ZM sends separate advertisements for temp/humidity/battery
                start_time = time.time()
                min_scan_time = 15  # Minimum scan time to collect all data types
                max_scan_time = scan_timeout
                
                logger.debug(f"Scanning for {min_scan_time}-{max_scan_time}s to collect complete sensor data")
                
                while (time.time() - start_time) < max_scan_time:
                    await asyncio.sleep(1.0)  # Check every second
                    
                    # Check if we have cached data for this device
                    device_mac = mac_address.upper()
                    if (hasattr(self, '_device_cache') and device_mac in self._device_cache):
                        cache_entry = self._device_cache[device_mac]
                        elapsed_time = time.time() - start_time
                        
                        # Check if we have temperature (required)
                        if cache_entry['temperature'] is not None:
                            temp = cache_entry['temperature']
                            humidity = cache_entry['humidity'] if cache_entry['humidity'] is not None else 0
                            battery = cache_entry['battery'] if cache_entry['battery'] is not None else 0
                            
                            if humidity > 100:
                                humidity = 0
                            
                            sensor_data = SensorData(
                                temperature=temp,
                                humidity=humidity,
                                battery=battery,
                                voltage=0.0,
                                timestamp=cache_entry['last_update'],
                                rssi=cache_entry.get('rssi')
                            )
                            
                            # Determine if we have complete data
                            has_temp = temp is not None
                            has_humidity = cache_entry['humidity'] is not None and cache_entry['humidity'] > 0
                            has_battery = cache_entry['battery'] is not None and cache_entry['battery'] > 0
                            
                            logger.debug(f"Data status for {mac_address}: temp={has_temp}, humidity={has_humidity}, battery={has_battery}, elapsed={elapsed_time:.1f}s")
                            
                            # Stop early if we have all three types of data
                            if has_temp and has_humidity and has_battery and elapsed_time >= 5:
                                logger.info(f"Complete data collected for {mac_address} in {elapsed_time:.1f}s")
                                break
                            # Or stop after minimum scan time if we have temperature + at least one other
                            elif has_temp and (has_humidity or has_battery) and elapsed_time >= min_scan_time:
                                logger.info(f"Partial data collected for {mac_address} after {elapsed_time:.1f}s")
                                break
                            # Or stop after minimum time even with just temperature
                            elif has_temp and elapsed_time >= min_scan_time:
                                logger.info(f"Temperature-only data for {mac_address} after {elapsed_time:.1f}s")
                                break
                
                await scanner.stop()
                
                if sensor_data:
                    logger.info(f"Successfully read sensor data from {mac_address} via advertisement")
                    return sensor_data
                else:
                    logger.warning(f"No sensor data received from {mac_address} in {scan_timeout}s scan")
                    
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
    
    def _parse_xiaomi_advertisement(self, service_data: bytes, mac_address: str, rssi: Optional[int] = None) -> Optional[SensorData]:
        """
        Parse Xiaomi advertisement service data for LYWSDCGQ/01ZM devices.
        
        LYWSDCGQ/01ZM devices send separate messages for different sensor types:
        - 0d1004[temp]: Temperature message (temp_byte / 10)
        - 061002[hum]: Humidity message (little-endian 16-bit / 10)
        - 0a1001[bat]: Battery message (direct percentage)
        
        Args:
            service_data: Raw service data from Xiaomi advertisement
            
        Returns:
            Parsed SensorData object or None if parsing fails
        """
        if len(service_data) < 12:
            return None
        
        try:
            # Use instance variable to accumulate data from multiple advertisements
            # Each advertisement might only contain one type of sensor data
            if not hasattr(self, '_device_cache'):
                self._device_cache = {}
            
            # Get or create cache entry for this device
            device_mac = mac_address.upper()
            if device_mac not in self._device_cache:
                self._device_cache[device_mac] = {
                    'temperature': None, 
                    'humidity': None, 
                    'battery': None, 
                    'rssi': None,
                    'last_update': datetime.now()
                }
            
            cache_entry = self._device_cache[device_mac]
            current_time = datetime.now()
            
            # Update RSSI if provided
            if rssi is not None:
                cache_entry['rssi'] = rssi
            
            temp = None
            humidity = None
            battery = None
            
            # Look for message patterns in the advertisement data
            for i in range(len(service_data) - 5):
                # Temperature message: 0d1004[temp_low][temp_high]
                if (i + 5 <= len(service_data) and 
                    service_data[i:i+3] == bytes([0x0d, 0x10, 0x04])):
                    
                    temp_bytes = service_data[i + 3:i + 5]
                    temp_raw = int.from_bytes(temp_bytes, byteorder='little', signed=True)
                    temp = temp_raw / 10.0  # LYWSDCGQ/01ZM uses /10 scaling
                    cache_entry['temperature'] = temp
                    cache_entry['last_update'] = current_time
                    logger.debug(f"Temperature from {mac_address}: {temp:.1f}°C")
                
                # Humidity message: 061002[hum_low][hum_high]
                elif (i + 5 < len(service_data) and 
                      service_data[i:i+3] == bytes([0x06, 0x10, 0x02])):
                    
                    hum_bytes = service_data[i + 3:i + 5]
                    hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                    humidity = hum_raw / 10.0  # Little-endian /10 scaling
                    cache_entry['humidity'] = humidity
                    cache_entry['last_update'] = current_time
                    logger.debug(f"Humidity from {mac_address}: {humidity:.1f}%")
                
                # Battery message: 0a1001[battery_percent]
                elif (i + 4 < len(service_data) and 
                      service_data[i:i+3] == bytes([0x0a, 0x10, 0x01])):
                    
                    battery = service_data[i + 3]
                    cache_entry['battery'] = battery
                    cache_entry['last_update'] = current_time
                    logger.debug(f"Battery from {mac_address}: {battery}%")
                
                # Alternative humidity message: 041002[hum_low][hum_high]
                elif (i + 5 < len(service_data) and 
                      service_data[i:i+3] == bytes([0x04, 0x10, 0x02])):
                    
                    # Alternative humidity format similar to 061002
                    hum_bytes = service_data[i + 3:i + 5]
                    hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                    alt_humidity = hum_raw / 10.0  # Little-endian /10 scaling
                    
                    # Use alternative humidity if it's reasonable
                    if 0 <= alt_humidity <= 100:
                        humidity = alt_humidity
                        cache_entry['humidity'] = humidity
                        cache_entry['last_update'] = current_time
                        logger.debug(f"Alternative humidity from {mac_address}: {humidity:.1f}%")
            
            # Return complete sensor data if we have temperature (required) and data is fresh
            cached_temp = cache_entry['temperature']
            cached_humidity = cache_entry['humidity']
            cached_battery = cache_entry['battery']
            
            if cached_temp is not None:
                # Validate temperature range
                if -40 <= cached_temp <= 80:
                    # Use cached data or defaults
                    final_humidity = cached_humidity if cached_humidity is not None else 0
                    final_battery = cached_battery if cached_battery is not None else 0
                    
                    # Validate humidity range
                    if final_humidity > 100:
                        final_humidity = 0
                    
                    logger.debug(f"Complete sensor data for {mac_address}: T={cached_temp:.1f}°C, H={final_humidity:.1f}%, B={final_battery}%")
                    
                    return SensorData(
                        temperature=cached_temp,
                        humidity=final_humidity,
                        battery=final_battery,
                        voltage=0.0,  # Not available in advertisements
                        timestamp=current_time,
                        rssi=rssi
                    )
            
        except Exception as e:
            logger.error(f"Error parsing Xiaomi advertisement: {e}")
        
        return None
        
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