#!/usr/bin/env python3
"""Analyze the actual captured Xiaomi advertisement format."""

def analyze_xiaomi_data(service_data_hex: str, mac: str):
    """Analyze the full Xiaomi service data format."""
    try:
        data = bytes.fromhex(service_data_hex)
        print(f"\nMAC {mac}: Full data: {service_data_hex}")
        print(f"Length: {len(data)} bytes")
        
        # Print each byte with hex and decimal
        for i, byte in enumerate(data):
            print(f"  [{i:2d}] 0x{byte:02x} = {byte:3d}")
        
        # Look for the pattern we found before: 0d1004
        for i in range(len(data) - 3):
            if data[i] == 0x0d and data[i+1] == 0x10 and data[i+2] == 0x04:
                print(f"  *** Found 0d1004 pattern at offset {i} ***")
                
                # Extract temperature and humidity data after the pattern
                if i + 6 < len(data):
                    temp_byte = data[i+3]
                    temp = temp_byte / 10.0
                    
                    # Look for humidity in the following bytes
                    print(f"  Temperature: {temp:.1f}°C (from byte {temp_byte})")
                    
                    # Check the next few bytes for humidity values around 48-49
                    for j in range(i+4, min(i+8, len(data))):
                        byte_val = data[j]
                        if 40 <= byte_val <= 60:
                            print(f"  *** Potential humidity at offset {j}: {byte_val}% ***")
                        else:
                            print(f"  Byte at offset {j}: {byte_val}")
                            
        # Also check for other patterns like 061002 and 041002
        for i in range(len(data) - 3):
            if data[i] == 0x06 and data[i+1] == 0x10 and data[i+2] == 0x02:
                print(f"  *** Found 061002 pattern at offset {i} ***")
                if i + 4 < len(data):
                    print(f"  Next bytes: {data[i+3:i+6].hex()}")
            elif data[i] == 0x04 and data[i+1] == 0x10 and data[i+2] == 0x02:
                print(f"  *** Found 041002 pattern at offset {i} ***")
                if i + 4 < len(data):
                    print(f"  Next bytes: {data[i+3:i+6].hex()}")
                    
    except Exception as e:
        print(f"Error analyzing {mac}: {e}")

# Test with some of the captured data samples
samples = [
    ("4C:65:A8:DC:84:01", "5020aa01e70184dca8654c0d1004f800ea01"),
    ("4C:65:A8:DC:84:01", "5020aa01e80184dca8654c061002ea01"),
    ("4C:65:A8:DB:99:44", "5020aa014b4499dba8654c0d1004f700e701"),
    ("4C:65:A8:DB:99:44", "5020aa014c4499dba8654c0d1004f500e701"),
    ("4C:65:A8:DC:84:01", "5020aa01f00184dca8654c0d1004f800e901"),
    ("4C:65:A8:DC:84:01", "5020aa01ef0184dca8654c0a100137"),
]

print("Analyzing captured Xiaomi advertisement samples:")
print("Known values: Temp 24.6-24.8°C, Humidity ~48.5%")

for mac, data in samples:
    analyze_xiaomi_data(data, mac)

print("\n=== SUMMARY ===")
print("Pattern analysis:")
print("- Temperature appears to be at offset +3 after '0d1004' pattern")
print("- 0xf8 = 248 / 10 = 24.8°C ✓")
print("- 0xf7 = 247 / 10 = 24.7°C ✓") 
print("- 0xf5 = 245 / 10 = 24.5°C ✓")
print("- Looking for humidity values around 48-49...")