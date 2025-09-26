#!/usr/bin/env python3
"""
Manual TLV decoding of Xiaomi data.
"""

def decode_tlv(payload_hex):
    """Manually decode TLV format."""
    data = bytes.fromhex(payload_hex)
    print(f"Payload: {data.hex()}")
    print(f"Length: {len(data)} bytes")
    print()
    
    pos = 0
    while pos < len(data) - 1:
        if pos + 1 >= len(data):
            break
            
        data_type = data[pos]
        data_len = data[pos + 1]
        
        print(f"Position {pos}: Type=0x{data_type:02x}, Length={data_len}")
        
        if pos + 2 + data_len > len(data):
            print(f"  ❌ Invalid length - would exceed data bounds")
            break
        
        if data_len > 0:
            value_data = data[pos + 2:pos + 2 + data_len]
            print(f"  Value: {value_data.hex()}")
            
            # Decode known Xiaomi types
            if data_type == 0x04 and data_len == 2:  # Temperature
                temp = int.from_bytes(value_data, 'little', signed=True) / 100.0
                print(f"  🌡️  Temperature: {temp}°C")
            elif data_type == 0x06 and data_len == 2:  # Humidity
                humidity = int.from_bytes(value_data, 'little') / 100.0  
                print(f"  💧 Humidity: {humidity}%")
            elif data_type == 0x0A and data_len == 1:  # Battery
                battery = value_data[0]
                print(f"  🔋 Battery: {battery}%")
            elif data_type == 0x10 and data_len == 4:  # Combined temp+humidity
                temp = int.from_bytes(value_data[0:2], 'little', signed=True) / 100.0
                humidity = int.from_bytes(value_data[2:4], 'little') / 100.0
                print(f"  🌡️💧 Temp: {temp}°C, Humidity: {humidity}%")
            else:
                print(f"  ❓ Unknown type or raw data")
        
        pos += 2 + data_len
        print()


print("🔍 Manual TLV Decoding:")
print("=" * 30)

# Our captured sensor data
payload = "0d1004fb00e401"
decode_tlv(payload)

print("\n🔧 Alternative interpretation:")
print("=" * 30)

# Maybe it's not TLV but direct encoding
data = bytes.fromhex(payload)
print(f"Raw bytes: {[f'0x{b:02x}' for b in data]}")

# Try different interpretations
print("\nInterpretation attempts:")

# Attempt 1: bytes 2-5 as temp+humidity
if len(data) >= 6:
    temp1 = int.from_bytes(data[2:4], 'little', signed=True) / 100.0
    humidity1 = int.from_bytes(data[4:6], 'little') / 100.0
    print(f"1. Bytes 2-5: Temp={temp1}°C, Humidity={humidity1}%")

# Attempt 2: bytes 3-6 as temp+humidity  
if len(data) >= 7:
    temp2 = int.from_bytes(data[3:5], 'little', signed=True) / 100.0
    humidity2 = int.from_bytes(data[5:7], 'little') / 100.0
    print(f"2. Bytes 3-6: Temp={temp2}°C, Humidity={humidity2}%")

# Attempt 3: Last 4 bytes as temp+humidity
if len(data) >= 4:
    temp3 = int.from_bytes(data[-4:-2], 'little', signed=True) / 100.0  
    humidity3 = int.from_bytes(data[-2:], 'little') / 100.0
    print(f"3. Last 4 bytes: Temp={temp3}°C, Humidity={humidity3}%")

# Check reasonableness
print(f"\nReasonableness check:")
checks = [
    (temp1, humidity1, "Interpretation 1"),
    (temp2, humidity2, "Interpretation 2"), 
    (temp3, humidity3, "Interpretation 3")
]

for temp, humidity, name in checks:
    if -40 <= temp <= 80 and 0 <= humidity <= 100:
        print(f"✅ {name} looks reasonable: {temp}°C, {humidity}%")
    else:
        print(f"❌ {name} out of range: {temp}°C, {humidity}%")