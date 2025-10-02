#!/usr/bin/env python3
"""
Decode Xiaomi advertisement data to extract sensor readings.
"""

def decode_xiaomi_advertisement(data_hex):
    """Decode Xiaomi service data format."""
    data = bytes.fromhex(data_hex.replace(' ', ''))
    
    print(f"Raw data: {data.hex()}")
    print(f"Length: {len(data)} bytes")
    
    if len(data) < 10:
        print("❌ Data too short")
        return None
    
    # Xiaomi format analysis
    print(f"\nXiaomi advertisement format:")
    print(f"Bytes 0-1:  {data[0:2].hex()} - Frame control")
    print(f"Bytes 2-3:  {data[2:4].hex()} - Product ID") 
    print(f"Byte 4:     {data[4]:02x} - Frame counter")
    print(f"Bytes 5-10: {data[5:11].hex()} - MAC address")
    
    if len(data) > 11:
        print(f"Bytes 11+:  {data[11:].hex()} - Sensor data")
        
        # Look for temperature/humidity in the payload
        payload = data[11:]
        
        # Common Xiaomi sensor data patterns
        if len(payload) >= 4:
            # Try different offsets
            for offset in range(len(payload) - 3):
                try:
                    # Temperature (2 bytes, signed, /100)
                    temp_raw = int.from_bytes(payload[offset:offset+2], 'little', signed=True)
                    temp = temp_raw / 100.0
                    
                    # Humidity (1-2 bytes after temp)
                    if offset + 2 < len(payload):
                        humidity = payload[offset + 2]
                    elif offset + 3 < len(payload):
                        humidity_raw = int.from_bytes(payload[offset+2:offset+4], 'little')
                        humidity = humidity_raw / 100.0
                    else:
                        continue
                    
                    # Sanity check
                    if -40 <= temp <= 80 and 0 <= humidity <= 100:
                        print(f"\n🎉 DECODED SENSOR DATA (offset {offset}):")
                        print(f"🌡️  Temperature: {temp}°C")
                        print(f"💧 Humidity: {humidity}%")
                        
                        # Look for battery data
                        if len(payload) > offset + 3:
                            remaining = payload[offset+3:]
                            print(f"🔋 Additional data: {remaining.hex()}")
                        
                        return {'temperature': temp, 'humidity': humidity}
                        
                except Exception as e:
                    continue
        
        # Try Xiaomi MiBeacon format (type-length-value)
        pos = 0
        found_sensor_data = {}
        
        while pos < len(payload) - 2:
            data_type = payload[pos]
            data_len = payload[pos + 1]
            
            if pos + 2 + data_len > len(payload):
                break
                
            data_value = payload[pos + 2:pos + 2 + data_len]
            
            print(f"TLV: Type 0x{data_type:02x}, Len {data_len}, Data: {data_value.hex()}")
            
            # Xiaomi sensor types
            if data_type == 0x04 and data_len == 2:  # Temperature
                temp = int.from_bytes(data_value, 'little', signed=True) / 100.0
                print(f"   🌡️  Temperature: {temp}°C")
                found_sensor_data['temperature'] = temp
            elif data_type == 0x06 and data_len == 2:  # Humidity  
                humidity = int.from_bytes(data_value, 'little') / 100.0
                print(f"   💧 Humidity: {humidity}%")
                found_sensor_data['humidity'] = humidity
            elif data_type == 0x0A and data_len == 1:  # Battery
                battery = data_value[0]
                print(f"   🔋 Battery: {battery}%")
                found_sensor_data['battery'] = battery
            elif data_type == 0x10 and data_len == 4:  # Combined temp+humidity
                temp = int.from_bytes(data_value[0:2], 'little', signed=True) / 100.0
                humidity = int.from_bytes(data_value[2:4], 'little') / 100.0
                print(f"   🌡️🦸 Combined: Temp={temp}°C, Humidity={humidity}%")
                found_sensor_data['temperature'] = temp
                found_sensor_data['humidity'] = humidity
            
            pos += 2 + data_len
        
        if found_sensor_data:
            print(f"\n🎉 FOUND SENSOR DATA via TLV:")
            if 'temperature' in found_sensor_data:
                print(f"🌡️  Temperature: {found_sensor_data['temperature']}°C")
            if 'humidity' in found_sensor_data:
                print(f"💧 Humidity: {found_sensor_data['humidity']}%")
            if 'battery' in found_sensor_data:
                print(f"🔋 Battery: {found_sensor_data['battery']}%")
            return found_sensor_data
    
    return None


# Test with the actual data we captured
test_data = "5020aa01470184dca8654c0d1004fb00e401"
print("🔍 Decoding captured Xiaomi advertisement data:")
print("=" * 50)

result = decode_xiaomi_advertisement(test_data)

if not result:
    print("\n🔧 Trying alternative parsing...")
    
    # Alternative: look for the known pattern in different positions
    data = bytes.fromhex(test_data)
    
    # The last few bytes often contain sensor data
    if len(data) >= 4:
        last_4 = data[-4:]
        print(f"Last 4 bytes: {last_4.hex()}")
        
        # Try interpreting as temp(2) + humidity(2) 
        temp = int.from_bytes(last_4[0:2], 'little', signed=True) / 100.0
        humidity = int.from_bytes(last_4[2:4], 'little') / 100.0
        
        print(f"Interpretation 1: Temp={temp}°C, Humidity={humidity}%")
        
        # Try other interpretations
        temp2 = int.from_bytes(last_4[2:4], 'little', signed=True) / 100.0  
        humidity2 = last_4[0]
        print(f"Interpretation 2: Temp={temp2}°C, Humidity={humidity2}%")
        
        # Check which looks reasonable
        if -40 <= temp <= 80 and 0 <= humidity <= 100:
            print(f"✅ Interpretation 1 looks valid!")
        elif -40 <= temp2 <= 80 and 0 <= humidity2 <= 100:
            print(f"✅ Interpretation 2 looks valid!")