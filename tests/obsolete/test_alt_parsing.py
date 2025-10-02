#!/usr/bin/env python3
"""
Test the alternative parsing approach.
"""

def test_alternative_parsing():
    # Real captured data
    service_data_hex = "5020aa01a90184dca8654c0d1004f800ea01"
    service_data = bytes.fromhex(service_data_hex)
    
    print(f"🔍 Testing Alternative Parsing")
    print(f"=" * 40)
    print(f"Service data: {service_data.hex()}")
    
    if len(service_data) >= 11:
        payload = service_data[11:]
        print(f"Payload: {payload.hex()}")
        
        # Check if it matches the pattern: 0d 10 04 [data]
        if len(payload) >= 7 and payload[0] == 0x0d and payload[1] == 0x10 and payload[2] == 0x04:
            sensor_data = payload[3:7]
            print(f"Sensor data: {sensor_data.hex()}")
            
            # Parse as temp(2) + humidity(1) + battery(1)
            temp_raw = int.from_bytes(sensor_data[0:2], byteorder="little", signed=True)
            temp = round(temp_raw / 100.0, 1)
            humidity = sensor_data[2]
            battery = sensor_data[3]
            
            print(f"🌡️  Temperature: {temp}°C")
            print(f"💧 Humidity: {humidity}%")  
            print(f"🔋 Battery: {battery}%")
            
            if -40 <= temp <= 80 and 0 <= humidity <= 100 and 0 <= battery <= 100:
                print(f"✅ All values look reasonable!")
                return True
            else:
                print(f"❌ Some values are out of range")
        else:
            print(f"❌ Doesn't match expected pattern")
    
    return False

if __name__ == "__main__":
    test_alternative_parsing()