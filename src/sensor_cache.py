#!/usr/bin/env python3
"""
Sensor Cache System for Hybrid MiBeacon Daemon.

Manages device discovery, data caching, threshold detection,
and intelligent MQTT publishing decisions.
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List

try:
    from .bluetooth_manager import SensorData
except ImportError:
    from bluetooth_manager import SensorData

logger = logging.getLogger(__name__)


@dataclass
class DeviceRecord:
    """Cache record for a single Xiaomi temperature/humidity sensor."""
    mac_address: str
    friendly_name: Optional[str] = None
    first_seen: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc).astimezone())
    
    # Partial data cache for incremental updates
    cached_temperature: Optional[float] = None
    cached_humidity: Optional[float] = None
    cached_battery: Optional[int] = None
    cached_rssi: Optional[int] = None
    last_update_time: Optional[datetime] = None
    
    # Complete sensor data (only when all required fields are available)
    current_data: Optional[SensorData] = None
    last_published_data: Optional[SensorData] = None
    last_publish_time: Optional[datetime] = None
    
    # Track if device has ever published complete data
    has_published_once: bool = False
    
    def is_data_complete(self) -> bool:
        """
        Check if we have all required fields for a complete sensor reading.
        
        Returns:
            True if temperature, humidity, and battery are all available
        """
        return all([
            self.cached_temperature is not None,
            self.cached_humidity is not None,
            self.cached_battery is not None
        ])
        
    def update_partial_data(self, parsed_data: dict, rssi: Optional[int] = None) -> bool:
        """
        Update partial sensor data from MiBeacon packet.
        
        Args:
            parsed_data: Dictionary with parsed MiBeacon fields
            rssi: RSSI value if available
            
        Returns:
            True if data was updated
        """
        updated = False
        current_time = datetime.now(tz=timezone.utc).astimezone()
        
        if 'temperature' in parsed_data:
            self.cached_temperature = parsed_data['temperature']
            updated = True
            
        if 'humidity' in parsed_data:
            self.cached_humidity = parsed_data['humidity']
            updated = True
            
        if 'battery' in parsed_data:
            self.cached_battery = parsed_data['battery']
            updated = True
            
        if rssi is not None:
            self.cached_rssi = rssi
            updated = True
            
        if updated:
            self.last_update_time = current_time
            
        return updated
        
    def create_complete_sensor_data(self) -> Optional[SensorData]:
        """
        Create complete SensorData object if all required fields are cached.
        
        Returns:
            SensorData object or None if data is incomplete
        """
        # Only return data if we have real sensor data with real timestamp
        if not self.is_data_complete() or self.last_update_time is None:
            return None
            
        return SensorData(
            temperature=self.cached_temperature,
            humidity=self.cached_humidity,
            battery=self.cached_battery or 0,
            last_seen=self.last_update_time,  # Must be real timestamp from sensor
            rssi=self.cached_rssi
        )
        
    def should_publish_immediately(self, temperature_threshold: float = 0.2, humidity_threshold: float = 1.0) -> bool:
        """
        Check if current data should trigger immediate MQTT publishing.
        Only returns True if we have complete data and significant changes.
        
        Args:
            temperature_threshold: °C threshold for immediate publishing
            humidity_threshold: % RH threshold for immediate publishing
            
        Returns:
            True if immediate publishing is required
        """
        # Must have complete data to publish
        if not self.is_data_complete():
            return False
            
        # If never published before and have complete data, publish immediately
        if not self.has_published_once:
            logger.info(f"First complete reading for {self.mac_address} - publishing immediately")
            return True
            
        # Check thresholds against last published data
        if not self.last_published_data:
            return True
            
        temp_delta = abs(self.cached_temperature - self.last_published_data.temperature)
        humidity_delta = abs(self.cached_humidity - self.last_published_data.humidity)
        
        if temp_delta >= temperature_threshold:
            logger.info(f"Temperature change {temp_delta:.1f}°C >= {temperature_threshold}°C threshold for {self.mac_address}")
            return True
            
        if humidity_delta >= humidity_threshold:
            logger.info(f"Humidity change {humidity_delta:.1f}% >= {humidity_threshold}% threshold for {self.mac_address}")
            return True
            
        return False
        
    def should_publish_periodic(self, publish_interval: int = 300) -> bool:
        """
        Check if device should publish based on time interval.
        Only returns True if we have complete data.
        
        Args:
            publish_interval: Minimum seconds between periodic publications
            
        Returns:
            True if periodic publishing is due
        """
        # Must have complete data to publish
        if not self.is_data_complete():
            return False
            
        if not self.last_publish_time:
            return True
            
        time_since_publish = (datetime.now(tz=timezone.utc) - self.last_publish_time).total_seconds()
        return time_since_publish >= publish_interval
        
    def has_new_data(self) -> bool:
        """Check if cached data differs from last published data."""
        if not self.is_data_complete() or not self.last_published_data:
            return self.is_data_complete()  # Only "new" if complete
            
        return (
            self.cached_temperature != self.last_published_data.temperature or
            self.cached_humidity != self.last_published_data.humidity or
            self.cached_battery != self.last_published_data.battery
        )
        
    def mark_published(self) -> None:
        """Mark current cached data as published."""
        if self.is_data_complete() and self.last_update_time is not None:
            # Only mark as published if we have real sensor data with real timestamp
            self.current_data = self.create_complete_sensor_data()
            self.last_published_data = SensorData(
                temperature=self.cached_temperature,
                humidity=self.cached_humidity,
                battery=self.cached_battery,
                last_seen=self.last_update_time,  # Must be real timestamp from sensor
                rssi=self.cached_rssi
            )
            self.last_publish_time = datetime.now(tz=timezone.utc)
            self.has_published_once = True
            logger.debug(f"Marked {self.mac_address} as published at {self.last_publish_time}")
        else:
            logger.warning(f"Cannot mark {self.mac_address} as published - incomplete data or no real timestamp")


class SensorCache:
    """
    Central cache for all discovered Xiaomi temperature/humidity sensors.
    
    Handles automatic device discovery, data updates, threshold detection,
    and intelligent publishing decisions.
    """
    
    def __init__(self, config: dict):
        """Initialize sensor cache with configuration."""
        self.devices: Dict[str, DeviceRecord] = {}
        self.friendly_names: Dict[str, str] = {}
        
        # Load friendly names from static device configuration
        self._load_friendly_names(config)
        
        # Cache configuration
        self.temperature_threshold = config.get('temperature_threshold', 0.2)
        self.humidity_threshold = config.get('humidity_threshold', 1.0)
        self.publish_interval = config.get('publish_interval', 300)
        
        logger.info(f"SensorCache initialized with thresholds: temp={self.temperature_threshold}°C, humidity={self.humidity_threshold}%")
        logger.info(f"Periodic publish interval: {self.publish_interval}s")
        
    def _load_friendly_names(self, config: dict) -> None:
        """Load friendly names from static devices configuration."""
        static_devices = config.get('static_devices', [])
        
        for device in static_devices:
            # Handle both dict and StaticDeviceModel objects
            if hasattr(device, 'mac'):
                # It's a Pydantic model
                mac = device.mac.upper()
                name = device.friendly_name
            else:
                # It's a dict
                mac = device.get('mac', '').upper()
                name = device.get('friendly_name') or device.get('name')
            
            if mac and name:
                self.friendly_names[mac] = name
                logger.debug(f"Loaded friendly name '{name}' for device {mac}")
        
    def discover_device(self, mac_address: str) -> DeviceRecord:
        """
        Discover and register a new device.
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            New or existing DeviceRecord
        """
        mac_address = mac_address.upper()
        
        if mac_address not in self.devices:
            friendly_name = self.friendly_names.get(mac_address)
            device = DeviceRecord(
                mac_address=mac_address,
                friendly_name=friendly_name
            )
            self.devices[mac_address] = device
            logger.info(f"Discovered new LYWSDCGQ device: {mac_address}" + 
                       (f" ({friendly_name})" if friendly_name else ""))
        
        return self.devices[mac_address]
        
    def update_partial_sensor_data(self, mac_address: str, parsed_data: dict, rssi: Optional[int] = None) -> Tuple[bool, bool]:
        """
        Update partial sensor data for a device and check publishing triggers.
        
        Args:
            mac_address: Device MAC address
            parsed_data: Parsed MiBeacon data dictionary
            rssi: RSSI value if available
            
        Returns:
            Tuple of (should_publish_immediately, should_publish_periodic)
        """
        mac_address = mac_address.upper()
        device = self.discover_device(mac_address)  # Auto-discover if new
        
        # Update partial data cache
        was_updated = device.update_partial_data(parsed_data, rssi)
        
        if not was_updated:
            return False, False
            
        logger.debug(f"Updated partial data for {mac_address}: {parsed_data}")
        
        # Check if we now have complete data for publishing
        if device.is_data_complete():
            # Update current_data with complete sensor reading
            device.current_data = device.create_complete_sensor_data()
            
            # Check publishing triggers
            immediate = device.should_publish_immediately(self.temperature_threshold, self.humidity_threshold)
            periodic = device.should_publish_periodic(self.publish_interval) and device.has_new_data()
            
            if immediate:
                logger.info(f"Immediate publish triggered for {mac_address} (complete data available)")
            elif periodic:
                logger.debug(f"Periodic publish triggered for {mac_address}")
                
            return immediate, periodic
        else:
            # Incomplete data - wait for more MiBeacon packets
            missing_fields = []
            if device.cached_temperature is None: missing_fields.append('temperature')
            if device.cached_humidity is None: missing_fields.append('humidity')
            if device.cached_battery is None: missing_fields.append('battery')
            
            logger.debug(f"Waiting for complete data from {mac_address}, missing: {missing_fields}")
            return False, False
        
    def mark_device_published(self, mac_address: str) -> None:
        """Mark a device's current data as published."""
        mac_address = mac_address.upper()
        if mac_address in self.devices:
            self.devices[mac_address].mark_published()
            
    def get_devices_for_periodic_publish(self) -> List[DeviceRecord]:
        """
        Get all devices that should be published in the next periodic cycle.
        Only includes devices with complete data.
        Publishes heartbeat messages even if data hasn't changed.
        
        Returns:
            List of devices ready for periodic publishing
        """
        ready_devices = []
        current_time = datetime.now(tz=timezone.utc).astimezone()
        
        for device in self.devices.values():
            if device.is_data_complete() and device.should_publish_periodic(self.publish_interval):
                # Ensure current_data is up to date
                device.current_data = device.create_complete_sensor_data()
                
                # Check if sensor data is stale (last_seen older than last publish)
                if device.last_publish_time and device.last_update_time:
                    if device.last_update_time < device.last_publish_time:
                        time_diff = (current_time - device.last_update_time).total_seconds()
                        logger.error(
                            f"Sensor lost: {device.friendly_name or device.mac_address} "
                            f"(MAC: {device.mac_address}) - No data received for {time_diff:.0f}s. "
                            f"Last seen: {device.last_update_time.isoformat()}"
                        )
                
                ready_devices.append(device)
                
        return ready_devices
        
    def get_device_count(self) -> int:
        """Get total number of discovered devices."""
        return len(self.devices)
        
    def get_device_summary(self) -> Dict[str, dict]:
        """Get summary of all devices for debugging/monitoring."""
        summary = {}
        
        for mac, device in self.devices.items():
            summary[mac] = {
                'friendly_name': device.friendly_name,
                'first_seen': device.first_seen.isoformat() if device.first_seen else None,
                'last_publish': device.last_publish_time.isoformat() if device.last_publish_time else None,
                'has_published_once': device.has_published_once,
                'is_complete': device.is_data_complete(),
                'cached_temperature': device.cached_temperature,
                'cached_humidity': device.cached_humidity,
                'cached_battery': device.cached_battery,
                'cached_rssi': device.cached_rssi,
                'last_update': device.last_update_time.isoformat() if device.last_update_time else None
            }
            
        return summary