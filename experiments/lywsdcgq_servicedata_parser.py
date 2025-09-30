#!/usr/bin/env python3
"""
LYWSDCGQ ServiceData Parser - Corrected Implementation

Based on real device analysis, LYWSDCGQ devices use Xiaomi ServiceData format 
with UUID "0000fe95-0000-1000-8000-00805f9b34fb".

Data format analysis from real device 4C:65:A8:DC:84:01:

Standard packets (18 bytes):
5020aa01[XX01]84dca8654c0d1004[YY00][ZZ01]

Where:
- 5020aa01: Xiaomi header/identifier
- XX01: Temperature data (little-endian, /10 for Celsius)
- 84dca8654c: Device MAC address (reversed)
- 0d: Data type indicator
- 1004: Unknown/constant
- YY00: Humidity data (single byte YY = humidity %)
- ZZ01: Battery data (single byte ZZ = battery %)

Shorter packets (16 bytes):
5020aa01[XX01]84dca8654c06100298[01]

Different data type (06 instead of 0d), different payload structure.
"""

import asyncio
import logging
import struct
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from bleak import BleakScanner, BLEDevice, AdvertisementData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LYWSDCGQReading:
    """Complete sensor reading from LYWSDCGQ device"""
    mac_address: str
    timestamp: datetime
    rssi: int
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    battery: Optional[int] = None
    packet_type: Optional[str] = None
    raw_data: Optional[str] = None

class LYWSDCGQServiceDataParser:
    """Parser for LYWSDCGQ ServiceData format"""
    
    XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
    EXPECTED_HEADER = bytes([0x50, 0x20, 0xaa, 0x01])  # 5020aa01
    
    def __init__(self):
        self.device_cache = {}
        
    def parse_servicedata(self, service_data: bytes, mac_address: str, rssi: int) -> Optional[LYWSDCGQReading]:
        """Parse Xiaomi ServiceData packet"""
        
        if len(service_data) < 4:
            logger.debug(f"Packet too short: {len(service_data)} bytes")
            return None
            
        # Check for Xiaomi header
        if service_data[:4] != self.EXPECTED_HEADER:
            logger.debug(f"Invalid header: {service_data[:4].hex()}")
            return None
            
        logger.info(f"Valid Xiaomi packet: {service_data.hex()}")
        
        reading = LYWSDCGQReading(
            mac_address=mac_address,
            timestamp=datetime.now(),
            rssi=rssi,
            raw_data=service_data.hex()
        )
        
        try:
            if len(service_data) >= 16:
                # MiBeacon format: 5020aa01[cnt][cnt][MAC][type][len][data...]
                reading.packet_type = "mibeacon"
                
                # Parse according to MiBeacon protocol
                # Packet: 5020aa01670184dca8654c0d1004ff009301
                # 5020aa01 = header
                # 67 01 = frame counter 
                # 84dca8654c = MAC (reversed)
                # 0d = data type (temp+humidity)
                # 10 = length indicator
                # 04 = payload length
                # ff00 = temperature (little-endian)
                # 9301 = humidity (little-endian)
                
                data_type = service_data[11]  # At offset 11 after MAC
                payload_len = service_data[13]  # At offset 13
                
                logger.debug(f"Packet: {service_data.hex()}")
                logger.debug(f"Data type: 0x{data_type:02x}, Payload len: {payload_len}")
                
                if data_type == 0x0d and payload_len >= 4:  # Temperature + Humidity
                    # Temperature: offset 14-15 (little-endian, /10)
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    reading.temperature = temp_raw / 10.0
                    
                    # Humidity: offset 16-17 (little-endian, /10)
                    if len(service_data) >= 18:
                        humid_raw = struct.unpack('<H', service_data[16:18])[0]
                        reading.humidity = humid_raw / 10.0
                    
                elif data_type == 0x04 and payload_len >= 2:  # Temperature only
                    # Temperature: offset 14-15 (little-endian, /10)
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    reading.temperature = temp_raw / 10.0
                    
                elif data_type == 0x06 and payload_len >= 2:  # Humidity only
                    # Humidity: offset 14-15 (little-endian, /10)
                    humid_raw = struct.unpack('<H', service_data[14:16])[0]
                    reading.humidity = humid_raw / 10.0
                    
                elif data_type == 0x0a and payload_len >= 1:  # Battery only
                    # Battery: single byte at offset 14
                    reading.battery = service_data[14]
                    
                logger.info(f"Parsed MiBeacon: T={reading.temperature}°C, H={reading.humidity}%, B={reading.battery}%")
                
            elif len(service_data) == 16:
                # 16-byte format - temperature only or humidity only
                reading.packet_type = "mibeacon_16"
                
                data_type = service_data[11]
                payload_len = service_data[13]
                
                logger.debug(f"16-byte packet: {service_data.hex()}")
                logger.debug(f"Data type: 0x{data_type:02x}, Payload len: {payload_len}")
                
                if data_type == 0x04 and payload_len >= 2:  # Temperature only
                    temp_raw = struct.unpack('<H', service_data[14:16])[0]
                    reading.temperature = temp_raw / 10.0
                elif data_type == 0x06 and payload_len >= 2:  # Humidity only
                    humid_raw = struct.unpack('<H', service_data[14:16])[0]
                    reading.humidity = humid_raw / 10.0
                    
                logger.info(f"Parsed MiBeacon 16: T={reading.temperature}°C, H={reading.humidity}%")
                
            elif len(service_data) == 15:
                # 15-byte format - typically battery only
                reading.packet_type = "mibeacon_15"
                
                data_type = service_data[11]
                payload_len = service_data[13]
                
                logger.debug(f"15-byte packet: {service_data.hex()}")
                logger.debug(f"Data type: 0x{data_type:02x}, Payload len: {payload_len}")
                
                if data_type == 0x0a and payload_len >= 1:  # Battery only
                    reading.battery = service_data[14]
                    logger.info(f"🔋 Found battery packet: {reading.battery}%")
                    
                logger.info(f"Parsed MiBeacon 15: B={reading.battery}%")
                
            else:
                logger.warning(f"Unknown packet length: {len(service_data)} bytes")
                reading.packet_type = f"unknown_{len(service_data)}"
                
        except (struct.error, IndexError) as e:
            logger.error(f"Error parsing packet: {e}")
            return None
            
        return reading

class LYWSDCGQAdvertisementScanner:
    """Advertisement scanner for LYWSDCGQ devices using corrected ServiceData format"""
    
    def __init__(self, target_mac: Optional[str] = None):
        self.target_mac = target_mac.upper() if target_mac else None
        self.parser = LYWSDCGQServiceDataParser()
        self.readings = []
        self.device_cache = {}
        
    async def scan(self, duration: int = 30):
        """Scan for LYWSDCGQ advertisements"""
        logger.info(f"Starting ServiceData scan for {duration} seconds...")
        if self.target_mac:
            logger.info(f"Filtering for MAC address: {self.target_mac}")
            
        def callback(device: BLEDevice, advertisement_data: AdvertisementData):
            # Filter by MAC if specified
            if self.target_mac and device.address.upper() != self.target_mac:
                return
                
            # Check for LYWSDCGQ device name
            device_name = advertisement_data.local_name or ""
            if "MJ_HT_V1" not in device_name:
                return
                
            logger.info(f"=== LYWSDCGQ Device Found: {device.address} ===")
            logger.info(f"Device Name: {device_name}")
            logger.info(f"RSSI: {advertisement_data.rssi}")
            
            # Parse ServiceData
            service_data_dict = advertisement_data.service_data or {}
            
            for service_uuid, data in service_data_dict.items():
                logger.info(f"Service UUID: {service_uuid}")
                logger.info(f"ServiceData: {data.hex()}")
                
                if service_uuid == self.parser.XIAOMI_SERVICE_UUID:
                    reading = self.parser.parse_servicedata(
                        data, device.address, advertisement_data.rssi
                    )
                    
                    if reading:
                        self.readings.append(reading)
                        logger.info(f"✓ Successfully parsed reading #{len(self.readings)}")
                        
                        # Store in cache for aggregation
                        self.update_device_cache(reading)
                        
            logger.info("=" * 50)
            
        scanner = BleakScanner(callback)
        await scanner.start()
        
        try:
            await asyncio.sleep(duration)
        finally:
            await scanner.stop()
            
        logger.info(f"\nScan completed. Collected {len(self.readings)} readings.")
        self.print_summary()
        
    def update_device_cache(self, reading: LYWSDCGQReading):
        """Update device cache with latest reading"""
        mac = reading.mac_address
        
        if mac not in self.device_cache:
            self.device_cache[mac] = {}
            
        cache = self.device_cache[mac]
        
        # Update available data
        if reading.temperature is not None:
            cache['temperature'] = reading.temperature
            cache['temp_timestamp'] = reading.timestamp
            
        if reading.humidity is not None:
            cache['humidity'] = reading.humidity
            cache['humid_timestamp'] = reading.timestamp
            
        if reading.battery is not None:
            cache['battery'] = reading.battery
            cache['batt_timestamp'] = reading.timestamp
            
        cache['rssi'] = reading.rssi
        cache['last_seen'] = reading.timestamp
        
        # Check if we have complete reading
        has_temp = 'temperature' in cache
        has_humid = 'humidity' in cache
        has_batt = 'battery' in cache
        
        if has_temp and has_humid and has_batt:
            logger.info(f"🎉 COMPLETE READING for {mac}:")
            logger.info(f"   Temperature: {cache['temperature']:.1f}°C")
            logger.info(f"   Humidity: {cache['humidity']}%")
            logger.info(f"   Battery: {cache['battery']}%")
            logger.info(f"   RSSI: {cache['rssi']} dBm")
            
    def print_summary(self):
        """Print summary of collected data"""
        logger.info("\n=== SCAN SUMMARY ===")
        logger.info(f"Total readings: {len(self.readings)}")
        
        for mac, cache in self.device_cache.items():
            logger.info(f"\nDevice: {mac}")
            logger.info(f"  Last seen: {cache.get('last_seen', 'N/A')}")
            logger.info(f"  RSSI: {cache.get('rssi', 'N/A')} dBm")
            logger.info(f"  Temperature: {cache.get('temperature', 'N/A')}")
            logger.info(f"  Humidity: {cache.get('humidity', 'N/A')}")
            logger.info(f"  Battery: {cache.get('battery', 'N/A')}")
            
        # Show packet type distribution
        packet_types = {}
        for reading in self.readings:
            ptype = reading.packet_type or "unknown"
            packet_types[ptype] = packet_types.get(ptype, 0) + 1
            
        logger.info(f"\nPacket types: {packet_types}")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LYWSDCGQ ServiceData Scanner")
    parser.add_argument("mac_address", nargs="?", help="Target MAC address (optional)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Scan duration in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    scanner = LYWSDCGQAdvertisementScanner(args.mac_address)
    await scanner.scan(args.duration)

if __name__ == "__main__":
    asyncio.run(main())