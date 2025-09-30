#!/usr/bin/env python3
"""
Continuous Bluetooth Manager for Hybrid MiBeacon Daemon.

Provides continuous BLE advertisement scanning and real-time
MiBeacon data processing for LYWSDCGQ/01ZM devices.
"""

import asyncio
import logging
import struct
from datetime import datetime, timezone
from typing import Optional, Callable
from dataclasses import dataclass

from bleak import BleakScanner
from .bluetooth_manager import SensorData  # Reuse existing SensorData class

logger = logging.getLogger(__name__)


class ContinuousBluetoothManager:
    """
    Continuous Bluetooth Manager for real-time MiBeacon processing.
    
    Replaces the polling-based approach with persistent advertisement scanning
    that processes all MiBeacon packets as they arrive.
    """
    
    def __init__(self, config: dict, data_callback: Optional[Callable] = None):
        """
        Initialize continuous Bluetooth manager.
        
        Args:
            config: Bluetooth configuration
            data_callback: Callback function for new sensor data
        """
        self.config = config
        self.data_callback = data_callback
        self.retry_attempts = config.get('retry_attempts', 3)
        self.connection_timeout = config.get('connection_timeout', 10)
        self._rssi_cache = {}  # Cache for RSSI values per MAC
        self.scanner = None
        self.running = False
        
        logger.info("ContinuousBluetoothManager initialized")
        

    
    def _parse_mibeacon_advertisement(self, service_data: bytes) -> Optional[dict]:
        """
        Parse MiBeacon advertisement data from LYWSDCGQ devices.
        
        Format based on packet length:
        - 18 bytes: Temperature + Humidity (0x0d) at positions 14-16, 16-18
        - 16 bytes: Temperature only (0x04) or Humidity only (0x06)
        - 15 bytes: Battery percentage only (0x0a) at position 14
        
        Returns:
            Dictionary with parsed sensor data or None if invalid
        """
        if len(service_data) < 15:
            return None
            
        try:
            # Check MiBeacon header
            if service_data[:4] != bytes([0x50, 0x20, 0xaa, 0x01]):
                return None
                
            # Parse based on packet length (following original working logic)
            data_type = service_data[11]
            logger.debug(f"MiBeacon packet: {service_data.hex()}")
            
            result = {}
            
            if len(service_data) == 18:
                # 18-byte format: Temperature + Humidity (type 0x0d)
                payload_len = service_data[13]
                
                if data_type == 0x0d and payload_len == 4:
                    # Parse temp (2 bytes) + humidity (2 bytes), little-endian
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    humid_raw = struct.unpack('<H', service_data[16:18])[0]
                    
                    temperature = round(temp_raw / 10.0, 1)
                    humidity = round(humid_raw / 10.0, 1)
                    
                    result = {
                        'temperature': temperature,
                        'humidity': humidity
                    }
                    logger.debug(f"Combined packet: T={temperature}°C, H={humidity}%")
                    
            elif len(service_data) == 16:
                # 16-byte format: Temperature only (0x04) or Humidity only (0x06)
                payload_len = service_data[13]
                
                if data_type == 0x04 and payload_len >= 2:
                    # Temperature only
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    temperature = round(temp_raw / 10.0, 1)
                    result = {'temperature': temperature}
                    logger.debug(f"Temperature packet: T={temperature}°C")
                    
                elif data_type == 0x06 and payload_len >= 2:
                    # Humidity only
                    humid_raw = struct.unpack('<H', service_data[14:16])[0]
                    humidity = round(humid_raw / 10.0, 1)
                    result = {'humidity': humidity}
                    logger.debug(f"Humidity packet: H={humidity}%")
                    
                elif data_type == 0x0a and payload_len >= 2:
                    # 16-byte battery packet with 2-byte voltage data
                    voltage_raw = struct.unpack('<H', service_data[14:16])[0]
                    voltage_mv = voltage_raw  # Already in millivolts
                    
                    # Calculate battery percentage from actual voltage measurement
                    # LYWSDCGQ voltage ranges: ~2100-3300mV for 0-100%
                    if voltage_mv >= 3000:
                        battery_pct = min(100, int((voltage_mv - 2100) / (3300 - 2100) * 100))
                    elif voltage_mv >= 2100:
                        battery_pct = int((voltage_mv - 2100) / (3000 - 2100) * 80)
                    else:
                        battery_pct = 0
                        
                    result = {'battery': max(0, battery_pct)}
                    logger.debug(f"Battery packet (16-byte voltage): B={battery_pct}% ({voltage_mv}mV)")
                    
            elif len(service_data) >= 15:
                # 15 byte format: Battery only (type 0x0a) 
                payload_len = service_data[13]
                
                if data_type == 0x0a and payload_len >= 1:
                    # Single byte - battery percentage directly from MiBeacon
                    battery_pct = service_data[14]
                    
                    result = {
                        'battery': battery_pct
                    }
                    logger.debug(f"Battery packet: B={battery_pct}%")
            
            return result if result else None
            
        except (struct.error, IndexError) as e:
            logger.debug(f"Error parsing MiBeacon data: {e}")
            return None
    
    def _advertisement_callback(self, device, advertisement_data):
        """
        Process BLE advertisements in real-time.
        
        Filters for LYWSDCGQ devices and processes MiBeacon data immediately.
        """
        try:
            # Filter for Xiaomi devices by name or service data
            device_name = getattr(device, 'name', '') or ''
            is_xiaomi_device = device_name in ['MJ_HT_V1', 'LYWSDCGQ/01ZM', 'LYWSD03MMC']
            
            # Also check for MiBeacon service data UUID
            service_data_dict = getattr(advertisement_data, 'service_data', {})
            xiaomi_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
            has_mibeacon = xiaomi_uuid in service_data_dict
            
            if not (is_xiaomi_device or has_mibeacon):
                return
                
            # Cache RSSI value
            rssi_value = None
            if hasattr(advertisement_data, 'rssi'):
                rssi_value = advertisement_data.rssi
                self._rssi_cache[device.address] = rssi_value
                
            # Process MiBeacon data if available
            if has_mibeacon:
                service_data = service_data_dict[xiaomi_uuid]
                parsed_data = self._parse_mibeacon_advertisement(service_data)
                
                if parsed_data:
                    logger.debug(f"Advertisement update from {device.address}: {parsed_data}")
                    
                    # Pass partial data directly to callback for cache accumulation
                    # No need to create SensorData objects with placeholder values
                    if self.data_callback:
                        asyncio.create_task(self._safe_callback(device.address, parsed_data, rssi_value))
                        
        except Exception as e:
            logger.error(f"Error in advertisement callback: {e}")
    
    async def _safe_callback(self, mac_address: str, parsed_data: dict, rssi: Optional[int]):
        """Safely call the data callback with error handling."""
        try:
            await self.data_callback(mac_address, parsed_data, rssi)
        except Exception as e:
            logger.error(f"Error in data callback for {mac_address}: {e}")
    
    async def start_continuous_scanning(self) -> bool:
        """
        Start continuous BLE advertisement scanning.
        
        Returns:
            True if scanning started successfully
        """
        if self.running:
            logger.warning("Continuous scanning already running")
            return True
            
        try:
            logger.info("Starting continuous BLE advertisement scanning...")
            self.scanner = BleakScanner(detection_callback=self._advertisement_callback)
            await self.scanner.start()
            self.running = True
            logger.info("Continuous scanning started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start continuous scanning: {e}")
            return False
    
    async def stop_continuous_scanning(self):
        """Stop continuous BLE advertisement scanning."""
        if not self.running:
            return
            
        self.running = False
        
        try:
            if self.scanner:
                logger.info("Stopping continuous BLE scanning...")
                await self.scanner.stop()
                self.scanner = None
                logger.info("Continuous scanning stopped")
        except Exception as e:
            logger.error(f"Error stopping scanner: {e}")
    
    def get_cached_rssi(self, mac_address: str) -> Optional[int]:
        """Get last cached RSSI value for a device."""
        return self._rssi_cache.get(mac_address.upper())
    
    def clear_rssi_cache(self):
        """Clear RSSI cache."""
        self._rssi_cache.clear()
        logger.debug("RSSI cache cleared")
        
    async def cleanup(self):
        """Clean up resources."""
        await self.stop_continuous_scanning()
        self.clear_rssi_cache()
        logger.info("ContinuousBluetoothManager cleanup completed")