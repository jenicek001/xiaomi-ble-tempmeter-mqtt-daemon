#!/usr/bin/env python3
"""Test correct Xiaomi sensor data parsing using known actual values."""

def parse_xiaomi_service_data_correct(service_data_hex: str) -> dict:
    """Parse Xiaomi service data using correct mitemp_bt2 logic."""
    try:
        print(f"Raw service data: {service_data_hex}")
        data = bytes.fromhex(service_data_hex)
        print(f"Data bytes: {data.hex()} (length: {len(data)})")
        
        # Known actual values: Temp 24.6-24.8°C, Humidity 48.5%
        target_temp_range = (24.6, 24.8)
        target_humidity = 48.5  # Could be rounded to 48 or 49
        
        print(f"Target values: Temp {target_temp_range[0]}-{target_temp_range[1]}°C, Humidity ~{target_humidity}%")
        
        # Service data: "0d1004f800ea01"
        # Bytes: 0d 10 04 f8 00 ea 01
        
        print(f"\nAnalyzing byte by byte:")
        for i, byte in enumerate(data):
            print(f"Byte {i}: 0x{byte:02x} = {byte}")
        
        # Based on Xiaomi protocol: 0d 10 04 [sensor_data]
        # 0d = length, 10 = type, 04 = data type (temp/humidity)
        if len(data) >= 7 and data[2] == 0x04:
            print("\nFound data type 0x04 (temp/humidity)")
            sensor_data = data[3:]  # Skip header: f800ea01
            print(f"Sensor data after header: {sensor_data.hex()}")
            
            # Let's try all possible interpretations of the 4 bytes: f8 00 ea 01
            
            print("\n=== Method 1: Standard 2-byte temp + 1-byte humidity + 1-byte battery ===")
            if len(sensor_data) >= 3:
                # Temperature: f8 00 (little-endian signed 16-bit)
                temp_raw = int.from_bytes(sensor_data[0:2], byteorder="little", signed=True)
                temp = temp_raw / 100.0
                
                # Humidity: ea (234 decimal - way too high)
                humidity = sensor_data[2]
                
                print(f"Temp: {temp}°C, Humidity: {humidity}%")
                if target_temp_range[0] <= temp <= target_temp_range[1]:
                    print("*** TEMPERATURE MATCHES! ***")
                
            print("\n=== Method 2: Different byte order ===")
            # Maybe temp is: 00 f8 instead of f8 00
            if len(sensor_data) >= 3:
                temp_raw = int.from_bytes(sensor_data[1::-1], byteorder="little", signed=True)  # Reverse first 2 bytes
                temp = temp_raw / 100.0
                humidity = sensor_data[2]
                print(f"Temp (reversed): {temp}°C, Humidity: {humidity}%")
                
            print("\n=== Method 3: Temperature in different position ===")
            # Maybe temp is at offset 1-2: 00 ea
            if len(sensor_data) >= 4:
                temp_raw = int.from_bytes(sensor_data[1:3], byteorder="little", signed=True)
                temp = temp_raw / 100.0
                humidity = sensor_data[0]  # f8 = 248 (still too high)
                print(f"Temp (offset 1-2): {temp}°C, Humidity: {humidity}%")
                
            print("\n=== Method 4: Try different scaling ===")
            # Maybe different temperature scaling
            temp_raw = int.from_bytes(sensor_data[0:2], byteorder="little", signed=True)
            temp_div10 = temp_raw / 10.0
            temp_div1 = temp_raw / 1.0
            
            print(f"Temp /10: {temp_div10}°C")
            print(f"Temp /1: {temp_div1}°C")
            
            if target_temp_range[0] <= temp_div10 <= target_temp_range[1]:
                print("*** TEMPERATURE MATCHES with /10 scaling! ***")
                
            print("\n=== Method 5: Check if humidity is elsewhere ===")
            # Check all bytes for humidity value around 48-49
            for i, byte_val in enumerate(sensor_data):
                if 47 <= byte_val <= 50:
                    print(f"*** Potential humidity match at byte {i}: {byte_val} ***")
                    
            print("\n=== Method 6: Try big-endian ===")
            temp_raw_be = int.from_bytes(sensor_data[0:2], byteorder="big", signed=True)
            temp_be = temp_raw_be / 100.0
            print(f"Temp (big-endian): {temp_be}°C")
            
            print("\n=== Method 7: Check raw hex values ===")
            print("Raw bytes analysis:")
            print(f"f8 = {0xf8} = {int.from_bytes([0xf8], signed=False)} unsigned, {int.from_bytes([0xf8], signed=True)} signed")
            print(f"00 = {0x00}")
            print(f"ea = {0xea} = {int.from_bytes([0xea], signed=False)} unsigned, {int.from_bytes([0xea], signed=True)} signed") 
            print(f"01 = {0x01}")
            
            # Maybe the data is encoded differently for LYWSDCGQ/01ZM
            # Let's check if 0xf8 could be related to 24.8°C
            if 0xf8 == 248:
                temp_guess = 248 / 10.0  # 24.8 - matches!
                print(f"*** 0xf8 / 10 = {temp_guess}°C - MATCHES! ***")
                
            # And check if any value could be 48 or 49 for humidity
            # 0x00 = 0, 0xea = 234, 0x01 = 1
            # Maybe humidity is encoded differently or in a different location
        
        return {}
        
    except Exception as e:
        print(f"Error parsing service data: {e}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    # Test with the captured service data
    service_data = "0d1004f800ea01"
    result = parse_xiaomi_service_data_correct(service_data)