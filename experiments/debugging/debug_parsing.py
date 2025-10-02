#!/usr/bin/env python3
"""
Debug the Xiaomi parsing with exact service data we captured.
"""

def debug_xiaomi_parsing():
    """Debug the parsing step by step."""
    
    # Real service data we captured
    service_data_hex = "5020aa01a90184dca8654c0d1004f800ea01"
    service_data = bytes.fromhex(service_data_hex)
    
    print(f"🔍 Debug Xiaomi Advertisement Parsing")
    print(f"=" * 50)
    print(f"Raw service data: {service_data.hex()}")
    print(f"Length: {len(service_data)} bytes")
    print()
    
    # Parse header
    print(f"📋 Header Analysis:")
    print(f"   Bytes 0-1 (Frame control): {service_data[0:2].hex()}")
    print(f"   Bytes 2-3 (Product ID): {service_data[2:4].hex()}")
    print(f"   Byte 4 (Frame counter): {service_data[4]:02x}")
    print(f"   Bytes 5-10 (MAC): {service_data[5:11].hex()}")
    
    if len(service_data) > 11:
        payload = service_data[11:]
        print(f"   Bytes 11+ (Payload): {payload.hex()}")
        print()
        
        print(f"📊 TLV Parsing:")
        pos = 0
        
        while pos < len(payload) - 1:
            if pos + 1 >= len(payload):
                break
                
            data_type = payload[pos]
            data_len = payload[pos + 1]
            
            print(f"   Position {pos}: Type=0x{data_type:02x}, Length={data_len}")
            
            if pos + 2 + data_len > len(payload):
                print(f"      ❌ Invalid length - would exceed payload")
                break
            
            if data_len > 0:
                value_data = payload[pos + 2:pos + 2 + data_len]
                print(f"      Value: {value_data.hex()}")
                
                # Try to decode based on type
                if data_type == 0x04 and data_len == 2:  # Temperature
                    temp = int.from_bytes(value_data, 'little', signed=True) / 100.0
                    print(f"      🌡️  Temperature: {temp}°C")
                elif data_type == 0x06 and data_len == 2:  # Humidity
                    humidity = int.from_bytes(value_data, 'little') / 100.0
                    print(f"      💧 Humidity: {humidity}%")
                elif data_type == 0x0A and data_len == 1:  # Battery
                    battery = value_data[0]
                    print(f"      🔋 Battery: {battery}%")
                elif data_type == 0x10 and data_len == 4:  # Combined
                    temp = int.from_bytes(value_data[0:2], 'little', signed=True) / 100.0
                    humidity = int.from_bytes(value_data[2:3], 'little')
                    print(f"      🌡️💧 Combined: Temp={temp}°C, Humidity={humidity}%")
                    
                    # Try voltage from last bytes
                    if len(value_data) == 4:
                        # Method 1: bytes 2-3 as voltage
                        voltage1 = int.from_bytes(value_data[2:4], 'little') / 1000.0
                        battery1 = max(0, min(100, int((voltage1 - 2.1) * 100)))
                        print(f"      ⚡ Voltage interpretation 1: {voltage1:.3f}V → {battery1}%")
                        
                        # Method 2: byte 3 as battery direct
                        battery2 = value_data[3]
                        print(f"      🔋 Battery interpretation 2: {battery2}%")
                else:
                    print(f"      ❓ Unknown/other type")
            
            pos += 2 + data_len
            print()
    
    print(f"🔧 Let's try all possible interpretations:")
    
    # Try different approaches to the payload
    if len(service_data) >= 15:  # Header + some data
        payload = service_data[11:]
        
        # Approach 1: Direct bytes interpretation (like original notification)
        if len(payload) >= 7:  # 0d1004 + 4 bytes data
            # Skip the TLV header (0d1004) and get the 4-byte value
            data_bytes = payload[3:7]  # Get the f800ea01 part
            
            print(f"\n🔬 Direct 4-byte interpretation:")
            print(f"   Data bytes: {data_bytes.hex()}")
            
            if len(data_bytes) >= 4:
                # Try original mitemp_bt2 format
                temp = int.from_bytes(data_bytes[0:2], 'little', signed=True) / 100.0
                humidity = data_bytes[2]
                voltage_raw = int.from_bytes(data_bytes[2:4], 'little')
                voltage = voltage_raw / 1000.0
                battery = max(0, min(100, int((voltage - 2.1) * 100)))
                
                print(f"   🌡️  Temperature: {temp}°C")
                print(f"   💧 Humidity: {humidity}%")
                print(f"   ⚡ Voltage: {voltage:.3f}V")
                print(f"   🔋 Battery: {battery}%")
                
                if -40 <= temp <= 80 and 0 <= humidity <= 100:
                    print(f"   ✅ This looks reasonable!")
                    return temp, humidity, battery
                else:
                    print(f"   ❌ Values out of range")


if __name__ == "__main__":
    debug_xiaomi_parsing()