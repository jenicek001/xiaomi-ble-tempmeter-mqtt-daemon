#!/usr/bin/env python3
"""Debug why humidity parsing is failing."""

def debug_humidity_parsing():
    # Test data from the captures that should contain humidity
    test_samples = [
        "5020aa01564499dba8654c061002e301",  # Should be humidity 48.3%
        "5020aa014c4499dba8654c061002e801",  # Should be humidity 48.8%
        "5020aa01f40184dca8654c0a100137",    # Should be battery 55%
        "5020aa01f20184dca8654c041002f900",  # Alt format
    ]
    
    for sample in test_samples:
        print(f"\nTesting: {sample}")
        data = bytes.fromhex(sample)
        print(f"Length: {len(data)}")
        
        # Print all bytes first
        for i, byte in enumerate(data):
            print(f"  [{i:2d}] 0x{byte:02x} = {byte:3d}")
        
        # Look for patterns
        print("  Searching for patterns...")
        found_any = False
        
        for i in range(len(data) - 2):  # Only need 3 bytes for pattern
            if i + 2 < len(data):
                pattern = data[i:i+3]
                pattern_hex = pattern.hex()
                
                if pattern == bytes([0x06, 0x10, 0x02]):
                    print(f"  ✅ Found 061002 at offset {i}")
                    found_any = True
                    if i + 5 <= len(data):
                        hum_bytes = data[i + 3:i + 5]
                        hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                        humidity = hum_raw / 10.0
                        print(f"      Humidity: {humidity:.1f}% (bytes: {hum_bytes.hex()})")
                        
                elif pattern == bytes([0x0a, 0x10, 0x01]):
                    print(f"  ✅ Found 0a1001 at offset {i}")
                    found_any = True
                    if i + 4 <= len(data):
                        battery = data[i + 3]
                        print(f"      Battery: {battery}%")
                        
                elif pattern == bytes([0x04, 0x10, 0x02]):
                    print(f"  ✅ Found 041002 at offset {i}")
                    found_any = True
                    if i + 5 <= len(data):
                        alt_bytes = data[i + 3:i + 5]
                        print(f"      Alt data: {alt_bytes.hex()}")
                elif pattern == bytes([0x0d, 0x10, 0x04]):
                    print(f"  ✅ Found 0d1004 at offset {i}")
                    found_any = True
                    
        if not found_any:
            print("  ❌ No known patterns found!")

if __name__ == "__main__":
    debug_humidity_parsing()