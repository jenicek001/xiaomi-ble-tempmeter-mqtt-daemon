#!/usr/bin/env python3
"""
LYWSDCGQ/01ZM Advertisement Scanner Experiment

Based on research from JsBergbau/MiTemperature2, this script scans for
BLE advertisements from LYWSDCGQ/01ZM (MJ_HT_V1) sensors and attempts
to decode the four different advertisement packet types:

1. 0D - Both temperature and humidity  
2. 04 - Temperature only
3. 06 - Humidity only
4. 0A - Battery only

Usage:
    python experiments/lywsdcgq_advertisement_scanner.py [MAC_ADDRESS]

If no MAC address is provided, it will scan for all LYWSDCGQ devices.
"""

import asyncio
import argparse
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LYWSDCGQAdvertisementParser:
    """Parser for LYWSDCGQ/01ZM advertisement packets"""
    
    # Advertisement preamble for LYWSDCGQ packets
    PREAMBLE = "5020aa01"
    
    # Data identifiers for different packet types
    DATA_IDENTIFIERS = {
        "0D": "temperature_humidity",  # Both temp and humidity
        "04": "temperature_only",      # Temperature only
        "06": "humidity_only",         # Humidity only  
        "0A": "battery_only"           # Battery only
    }
    
    def __init__(self):
        self.data_cache = {}  # Cache for partial data from different packets
        
    def parse_advertisement(self, mac: str, adv_data: AdvertisementData, rssi: int) -> Optional[Dict[str, Any]]:
        """
        Parse LYWSDCGQ advertisement data
        
        Args:
            mac: Device MAC address
            adv_data: Advertisement data from Bleak
            rssi: Signal strength
            
        Returns:
            Parsed data dictionary or None if not a valid LYWSDCGQ packet
        """
        if not adv_data.manufacturer_data:
            return None
            
        # Convert manufacturer data to hex string
        for manufacturer_id, data_bytes in adv_data.manufacturer_data.items():
            hex_data = data_bytes.hex().lower()
            logger.debug(f"Raw advertisement data from {mac}: {hex_data}")
            
            # Look for LYWSDCGQ preamble
            preamble_start = hex_data.find(self.PREAMBLE)
            if preamble_start == -1:
                continue
                
            # Extract the data after preamble
            offset = preamble_start + len(self.PREAMBLE)
            stripped_data = hex_data[offset:]
            
            if len(stripped_data) < 16:
                logger.debug(f"Insufficient data length: {len(stripped_data)}")
                continue
                
            # Extract data identifier (at offset+14 from original, so +14-8=+6 from stripped)
            if len(stripped_data) >= 16:
                data_identifier = stripped_data[14:16].upper()
                logger.info(f"Found data identifier: {data_identifier} from {mac}")
                
                if data_identifier in self.DATA_IDENTIFIERS:
                    return self._parse_packet_by_type(mac, data_identifier, stripped_data, rssi)
                    
        return None
        
    def _parse_packet_by_type(self, mac: str, data_id: str, data: str, rssi: int) -> Dict[str, Any]:
        """Parse packet based on data identifier type"""
        
        result = {
            "mac": mac,
            "rssi": rssi,
            "timestamp": datetime.now().isoformat(),
            "packet_type": self.DATA_IDENTIFIERS[data_id],
            "data_identifier": data_id,
            "raw_data": data
        }
        
        try:
            if data_id == "0D" and len(data) >= 28:
                # Both temperature and humidity
                temp_bytes = data[20:24]
                humidity_bytes = data[24:28]
                
                temperature = int.from_bytes(bytes.fromhex(temp_bytes), byteorder='little', signed=True) / 10.0
                humidity = int.from_bytes(bytes.fromhex(humidity_bytes), byteorder='little', signed=True) / 10.0
                
                result.update({
                    "temperature": temperature,
                    "humidity": humidity
                })
                
                # Update cache
                self._update_cache(mac, temperature=temperature, humidity=humidity, rssi=rssi)
                
            elif data_id == "04" and len(data) >= 24:
                # Temperature only
                temp_bytes = data[20:24]
                temperature = int.from_bytes(bytes.fromhex(temp_bytes), byteorder='little', signed=True) / 10.0
                
                result["temperature"] = temperature
                self._update_cache(mac, temperature=temperature, rssi=rssi)
                
            elif data_id == "06" and len(data) >= 24:
                # Humidity only
                humidity_bytes = data[20:24]
                humidity = int.from_bytes(bytes.fromhex(humidity_bytes), byteorder='little', signed=True) / 10.0
                
                result["humidity"] = humidity
                self._update_cache(mac, humidity=humidity, rssi=rssi)
                
            elif data_id == "0A" and len(data) >= 22:
                # Battery only
                battery_bytes = data[20:22]
                battery = int.from_bytes(bytes.fromhex(battery_bytes), byteorder='little', signed=False)
                
                result["battery"] = battery
                self._update_cache(mac, battery=battery, rssi=rssi)
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing packet type {data_id}: {e}")
            
        return result
        
    def _update_cache(self, mac: str, **kwargs):
        """Update the data cache with new values"""
        if mac not in self.data_cache:
            self.data_cache[mac] = {}
            
        self.data_cache[mac].update(kwargs)
        self.data_cache[mac]["last_update"] = datetime.now()
        
    def get_cached_data(self, mac: str) -> Dict[str, Any]:
        """Get the most recent cached data for a device"""
        return self.data_cache.get(mac, {})
        
    def get_complete_reading(self, mac: str, max_age_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Get a complete reading if we have recent data for temp, humidity, and battery"""
        cached = self.get_cached_data(mac)
        if not cached or "last_update" not in cached:
            return None
            
        # Check if data is fresh enough
        age = (datetime.now() - cached["last_update"]).total_seconds()
        if age > max_age_seconds:
            return None
            
        # Check if we have all required data
        required_fields = ["temperature", "humidity", "battery", "rssi"]
        if all(field in cached for field in required_fields):
            return {
                "mac": mac,
                "temperature": cached["temperature"],
                "humidity": cached["humidity"], 
                "battery": cached["battery"],
                "rssi": cached["rssi"],
                "last_update": cached["last_update"].isoformat(),
                "data_age_seconds": age
            }
            
        return None


class LYWSDCGQScanner:
    """BLE scanner for LYWSDCGQ/01ZM devices"""
    
    def __init__(self, target_mac: Optional[str] = None):
        self.target_mac = target_mac.lower() if target_mac else None
        self.parser = LYWSDCGQAdvertisementParser()
        self.packets_received = 0
        
    async def advertisement_callback(self, device: BLEDevice, adv_data: AdvertisementData):
        """Callback for BLE advertisements"""
        mac = device.address.lower()
        
        # Filter by target MAC if specified
        if self.target_mac and mac != self.target_mac:
            return
            
        # Check if this looks like a LYWSDCGQ device
        if not self._is_lywsdcgq_device(device, adv_data):
            return
            
        self.packets_received += 1
        logger.info(f"Packet #{self.packets_received} from {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
        
        # Parse the advertisement
        parsed_data = self.parser.parse_advertisement(mac, adv_data, adv_data.rssi)
        if parsed_data:
            self._log_parsed_data(parsed_data)
            
            # Check if we can create a complete reading
            complete = self.parser.get_complete_reading(mac)
            if complete:
                logger.info("=== COMPLETE READING ===")
                self._log_complete_reading(complete)
                logger.info("========================")
                
    def _is_lywsdcgq_device(self, device: BLEDevice, adv_data: AdvertisementData) -> bool:
        """Check if this appears to be a LYWSDCGQ device"""
        
        # Check device name
        if device.name and "MJ_HT_V1" in device.name:
            return True
            
        # Check for LYWSDCGQ preamble in manufacturer data
        if adv_data.manufacturer_data:
            for manufacturer_id, data_bytes in adv_data.manufacturer_data.items():
                hex_data = data_bytes.hex().lower()
                if LYWSDCGQAdvertisementParser.PREAMBLE in hex_data:
                    return True
                    
        return False
        
    def _log_parsed_data(self, data: Dict[str, Any]):
        """Log parsed advertisement data"""
        packet_type = data.get("packet_type", "unknown")
        data_id = data.get("data_identifier", "??")
        
        logger.info(f"  Type: {packet_type} (ID: {data_id})")
        
        if "temperature" in data:
            logger.info(f"  Temperature: {data['temperature']:.1f}°C")
        if "humidity" in data:
            logger.info(f"  Humidity: {data['humidity']:.1f}%")
        if "battery" in data:
            logger.info(f"  Battery: {data['battery']}%")
            
        logger.debug(f"  Raw data: {data['raw_data']}")
        
    def _log_complete_reading(self, reading: Dict[str, Any]):
        """Log a complete sensor reading"""
        logger.info(f"  MAC: {reading['mac']}")
        logger.info(f"  Temperature: {reading['temperature']:.1f}°C")
        logger.info(f"  Humidity: {reading['humidity']:.1f}%")
        logger.info(f"  Battery: {reading['battery']}%")
        logger.info(f"  RSSI: {reading['rssi']} dBm")
        logger.info(f"  Data Age: {reading['data_age_seconds']:.1f}s")
        
    async def scan(self, duration: int = 60):
        """Scan for LYWSDCGQ advertisements"""
        logger.info(f"Starting LYWSDCGQ advertisement scan for {duration} seconds...")
        if self.target_mac:
            logger.info(f"Filtering for MAC address: {self.target_mac}")
            
        scanner = BleakScanner(self.advertisement_callback)
        
        try:
            await scanner.start()
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            logger.info("Scan interrupted by user")
        finally:
            await scanner.stop()
            
        logger.info(f"Scan completed. Total packets received: {self.packets_received}")
        
        # Show final cache state
        if self.parser.data_cache:
            logger.info("\n=== FINAL CACHE STATE ===")
            for mac, data in self.parser.data_cache.items():
                logger.info(f"Device {mac}:")
                for key, value in data.items():
                    if key != "last_update":
                        logger.info(f"  {key}: {value}")
                    else:
                        logger.info(f"  {key}: {value.isoformat()}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Scan for LYWSDCGQ/01ZM BLE advertisements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "mac", 
        nargs="?", 
        help="Target MAC address (optional, will scan all devices if not provided)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Scan duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    scanner = LYWSDCGQScanner(args.mac)
    
    try:
        await scanner.scan(args.duration)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())