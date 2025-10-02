#!/usr/bin/env python3
"""
LYWSDCGQ/01ZM ServiceData Analyzer

Analyzes the actual data format received from LYWSDCGQ devices
to understand the correct parsing approach.
"""

import asyncio
import logging
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

class LYWSDCGQServiceDataAnalyzer:
    """Analyzer for LYWSDCGQ ServiceData format"""
    
    # Expected service UUID for Xiaomi devices
    XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
    
    def __init__(self, target_mac: Optional[str] = None):
        self.target_mac = target_mac.lower() if target_mac else None
        self.packets_analyzed = 0
        self.data_samples = []
        
    async def advertisement_callback(self, device: BLEDevice, adv_data: AdvertisementData):
        """Callback for BLE advertisements"""
        mac = device.address.lower()
        
        # Filter by target MAC if specified
        if self.target_mac and mac != self.target_mac:
            return
            
        # Check if this looks like a LYWSDCGQ device
        if not self._is_lywsdcgq_device(device, adv_data):
            return
            
        self.packets_analyzed += 1
        logger.info(f"=== PACKET #{self.packets_analyzed} from {device.address} ===")
        logger.info(f"Device Name: {device.name or 'Unknown'}")
        logger.info(f"RSSI: {adv_data.rssi}")
        
        # Analyze ServiceData
        if adv_data.service_data:
            for service_uuid, data_bytes in adv_data.service_data.items():
                logger.info(f"Service UUID: {service_uuid}")
                hex_data = data_bytes.hex()
                logger.info(f"Raw hex data: {hex_data}")
                logger.info(f"Data length: {len(data_bytes)} bytes")
                
                # Store sample for later analysis
                sample = {
                    "timestamp": datetime.now().isoformat(),
                    "mac": mac,
                    "rssi": adv_data.rssi,
                    "service_uuid": service_uuid,
                    "hex_data": hex_data,
                    "data_bytes": data_bytes
                }
                self.data_samples.append(sample)
                
                # Try to parse if it's the Xiaomi service
                if service_uuid == self.XIAOMI_SERVICE_UUID:
                    self._analyze_xiaomi_service_data(data_bytes, hex_data)
                    
        # Analyze ManufacturerData too
        if adv_data.manufacturer_data:
            for manufacturer_id, data_bytes in adv_data.manufacturer_data.items():
                logger.info(f"Manufacturer ID: {manufacturer_id}")
                hex_data = data_bytes.hex()
                logger.info(f"Manufacturer hex data: {hex_data}")
                logger.info(f"Manufacturer data length: {len(data_bytes)} bytes")
                
        logger.info("=" * 50)
        
    def _is_lywsdcgq_device(self, device: BLEDevice, adv_data: AdvertisementData) -> bool:
        """Check if this appears to be a LYWSDCGQ device"""
        
        # Check device name
        if device.name and "MJ_HT_V1" in device.name:
            return True
            
        # Check for Xiaomi service data
        if adv_data.service_data and self.XIAOMI_SERVICE_UUID in adv_data.service_data:
            return True
            
        return False
        
    def _analyze_xiaomi_service_data(self, data_bytes: bytes, hex_data: str):
        """Analyze Xiaomi service data format"""
        logger.info(f"Analyzing Xiaomi service data...")
        
        if len(data_bytes) < 10:
            logger.info("Data too short for analysis")
            return
            
        # Try to parse according to Xiaomi Mi format
        # Based on research, Xiaomi format typically starts with specific headers
        
        # Print byte-by-byte analysis
        logger.info("Byte-by-byte analysis:")
        for i, byte in enumerate(data_bytes):
            logger.info(f"  Byte {i:2d}: 0x{byte:02x} ({byte:3d}) '{chr(byte) if 32 <= byte <= 126 else '.'}'")
            
        # Look for known patterns
        if len(data_bytes) >= 18:
            # Try temperature parsing (various possible positions)
            for offset in range(0, min(len(data_bytes) - 2, 15)):
                try:
                    # Try little-endian signed 16-bit temperature (divided by 10 or 100)
                    temp_raw = int.from_bytes(data_bytes[offset:offset+2], byteorder='little', signed=True)
                    temp_div10 = temp_raw / 10.0
                    temp_div100 = temp_raw / 100.0
                    
                    # Check if temperature values are reasonable
                    if -50 < temp_div10 < 100:
                        logger.info(f"  Possible temp at offset {offset}: {temp_div10:.1f}°C (raw={temp_raw}, /10)")
                    if -50 < temp_div100 < 100:
                        logger.info(f"  Possible temp at offset {offset}: {temp_div100:.1f}°C (raw={temp_raw}, /100)")
                        
                except (ValueError, IndexError):
                    pass
                    
            # Try humidity parsing
            for offset in range(0, min(len(data_bytes) - 2, 15)):
                try:
                    # Try various humidity formats
                    humidity_raw = int.from_bytes(data_bytes[offset:offset+2], byteorder='little', signed=False)
                    humidity_div10 = humidity_raw / 10.0
                    humidity_div100 = humidity_raw / 100.0
                    humidity_single = data_bytes[offset]
                    
                    # Check if humidity values are reasonable
                    if 0 <= humidity_single <= 100:
                        logger.info(f"  Possible humidity at offset {offset}: {humidity_single}% (single byte)")
                    if 0 <= humidity_div10 <= 100:
                        logger.info(f"  Possible humidity at offset {offset}: {humidity_div10:.1f}% (raw={humidity_raw}, /10)")
                    if 0 <= humidity_div100 <= 100:
                        logger.info(f"  Possible humidity at offset {offset}: {humidity_div100:.1f}% (raw={humidity_raw}, /100)")
                        
                except (ValueError, IndexError):
                    pass
                    
            # Try battery parsing
            for offset in range(0, len(data_bytes)):
                try:
                    battery_single = data_bytes[offset]
                    if 0 <= battery_single <= 100:
                        logger.info(f"  Possible battery at offset {offset}: {battery_single}%")
                        
                    if offset < len(data_bytes) - 1:
                        battery_raw = int.from_bytes(data_bytes[offset:offset+2], byteorder='little', signed=False)
                        battery_voltage = battery_raw / 1000.0
                        if 0.5 <= battery_voltage <= 3.5:
                            logger.info(f"  Possible voltage at offset {offset}: {battery_voltage:.3f}V (raw={battery_raw})")
                            
                except (ValueError, IndexError):
                    pass
                    
    def print_summary(self):
        """Print analysis summary"""
        logger.info(f"\n=== ANALYSIS SUMMARY ===")
        logger.info(f"Total packets analyzed: {self.packets_analyzed}")
        logger.info(f"Samples collected: {len(self.data_samples)}")
        
        if self.data_samples:
            logger.info("\nData format analysis:")
            logger.info(f"Service UUID: {self.XIAOMI_SERVICE_UUID}")
            
            # Show unique data lengths
            lengths = set(len(sample['data_bytes']) for sample in self.data_samples)
            logger.info(f"Data lengths observed: {sorted(lengths)}")
            
            # Show first few samples
            for i, sample in enumerate(self.data_samples[:3]):
                logger.info(f"\nSample {i+1}:")
                logger.info(f"  Timestamp: {sample['timestamp']}")
                logger.info(f"  RSSI: {sample['rssi']}")
                logger.info(f"  Hex: {sample['hex_data']}")
        
        logger.info("=" * 30)

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze LYWSDCGQ ServiceData format")
    parser.add_argument("mac", nargs="?", help="Target MAC address (optional)")
    parser.add_argument("--duration", "-d", type=int, default=30, help="Scan duration in seconds")
    
    args = parser.parse_args()
    
    analyzer = LYWSDCGQServiceDataAnalyzer(args.mac)
    
    logger.info(f"Starting ServiceData analysis for {args.duration} seconds...")
    if args.mac:
        logger.info(f"Filtering for MAC address: {args.mac}")
        
    scanner = BleakScanner(analyzer.advertisement_callback)
    
    try:
        await scanner.start()  
        await asyncio.sleep(args.duration)
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
    finally:
        await scanner.stop()
        
    analyzer.print_summary()

if __name__ == "__main__":
    asyncio.run(main())