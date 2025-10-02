#!/usr/bin/env python3
"""Decode Xiaomi advertisements with proper humidity detection."""

def decode_xiaomi_advertisement(service_data_hex: str, mac: str) -> dict:
    """Decode Xiaomi sensor data from advertisement."""
    try:
        data = bytes.fromhex(service_data_hex)
        result = {}
        
        print(f"\nDecoding {mac}: {service_data_hex}")
        
        # Look for different message types
        for i in range(len(data) - 2):
            # Check for 3-byte patterns
            if i + 2 < len(data):
                pattern = data[i:i+3]
                
                # Temperature + Humidity message (0d1004)
                if pattern == bytes([0x0d, 0x10, 0x04]):
                    print(f"  Found temp+humidity message (0d1004) at offset {i}")
                    if i+3 < len(data):
                        temp_raw = data[i+3]
                        temp = temp_raw / 10.0
                        print(f"  Temperature: {temp:.1f}°C")
                        result['temperature'] = temp
                        
                        # Check remaining bytes for humidity
                        remaining_bytes = data[i+4:i+7] if i+7 <= len(data) else data[i+4:]
                        print(f"  Remaining bytes after temp: {remaining_bytes.hex()}")
                    
                # Battery message (0a1001)  
                elif pattern == bytes([0x0a, 0x10, 0x01]):
                    print(f"  Found battery message (0a1001) at offset {i}")
                    if i+3 < len(data):
                        battery = data[i+3]
                        print(f"  Battery: {battery}%")
                        result['battery'] = battery
                        
                # Humidity message (061002)
                elif pattern == bytes([0x06, 0x10, 0x02]):
                    print(f"  Found humidity message (061002) at offset {i}")
                    if i+5 <= len(data):
                        hum_bytes = data[i+3:i+5]
                        print(f"  Humidity bytes: {hum_bytes.hex()}")
                        
                        # Try little-endian 16-bit
                        hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                        hum = hum_raw / 100.0
                        print(f"  Humidity (as /100): {hum:.1f}%")
                        
                        # Also try just first byte
                        hum_byte = data[i+3]
                        print(f"  Humidity (first byte): {hum_byte}")
                        
                        if 40 <= hum <= 60:
                            print(f"  *** REASONABLE HUMIDITY: {hum:.1f}% ***")
                            result['humidity'] = hum
                        elif 40 <= hum_byte <= 60:
                            print(f"  *** REASONABLE HUMIDITY (byte): {hum_byte}% ***")
                            result['humidity'] = hum_byte
                            
                # Alternative humidity message (041002)
                elif pattern == bytes([0x04, 0x10, 0x02]):
                    print(f"  Found alt humidity message (041002) at offset {i}")
                    if i+4 < len(data):
                        remaining = data[i+3:i+6] if i+6 <= len(data) else data[i+3:]
                        print(f"  Alt humidity bytes: {remaining.hex()}")
                        
                        # Try first byte as humidity
                        if remaining:
                            hum_byte = remaining[0]
                            if 40 <= hum_byte <= 60:
                                print(f"  *** REASONABLE ALT HUMIDITY: {hum_byte}% ***")
                                result['humidity'] = hum_byte
                    
        return result
        
    except Exception as e:
        print(f"Error decoding {mac}: {e}")
        return {}

# Test with samples that have different message types
samples = [
    ("4C:65:A8:DC:84:01", "5020aa01e70184dca8654c0d1004f800ea01"),  # Has 0d1004
    ("4C:65:A8:DC:84:01", "5020aa01e80184dca8654c061002ea01"),      # Has 061002  
    ("4C:65:A8:DC:84:01", "5020aa01ef0184dca8654c0a100137"),        # Has 0a1001
    ("4C:65:A8:DB:99:44", "5020aa01594499dba8654c041002f700"),      # Has 041002
]

print("Decoding Xiaomi advertisements for temperature and humidity:")
print("Target values: Temp 24.6-24.8°C, Humidity ~48.5%")

for mac, data in samples:
    result = decode_xiaomi_advertisement(data, mac)
    if result:
        print(f"  DECODED: {result}")
        
print("\n=== Analysis ===")
print("Different message types found:")
print("- 0d1004: Temperature message (temp/10)")
print("- 061002: Possible humidity message") 
print("- 0a1001: Battery message")
print("- 041002: Alternative humidity message")