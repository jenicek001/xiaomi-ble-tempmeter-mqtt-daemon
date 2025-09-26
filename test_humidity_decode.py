#!/usr/bin/env python3
"""Test different humidity decoding methods for LYWSDCGQ/01ZM."""

def test_humidity_decoding():
    """Test various ways to decode humidity from captured data."""
    
    # Sample data with known humidity ~48.5%
    samples = [
        ("061002ea01", "ea01", "From 061002 message"),
        ("041002f700", "f700", "From 041002 message"),
        ("0d1004f800ea01", "ea", "Last byte from temp message"),
    ]
    
    target_humidity = 48.5
    
    print(f"Target humidity: ~{target_humidity}%")
    print("Testing different decoding methods:\n")
    
    for sample_desc, hex_data, desc in samples:
        print(f"=== {desc} ===")
        print(f"Raw data: {hex_data}")
        
        data = bytes.fromhex(hex_data)
        
        # Method 1: Little-endian 16-bit / 100
        if len(data) >= 2:
            val_le = int.from_bytes(data[:2], byteorder='little')
            hum_le_100 = val_le / 100.0
            hum_le_10 = val_le / 10.0
            print(f"  LE 16-bit /100: {hum_le_100:.1f}%")
            print(f"  LE 16-bit /10:  {hum_le_10:.1f}%")
            
            if abs(hum_le_100 - target_humidity) < 5:
                print(f"  *** CLOSE MATCH /100: {hum_le_100:.1f}% ***")
            if abs(hum_le_10 - target_humidity) < 5:
                print(f"  *** CLOSE MATCH /10: {hum_le_10:.1f}% ***")
        
        # Method 2: Big-endian 16-bit / 100 
        if len(data) >= 2:
            val_be = int.from_bytes(data[:2], byteorder='big')
            hum_be_100 = val_be / 100.0
            hum_be_10 = val_be / 10.0
            print(f"  BE 16-bit /100: {hum_be_100:.1f}%")
            print(f"  BE 16-bit /10:  {hum_be_10:.1f}%")
            
            if abs(hum_be_100 - target_humidity) < 5:
                print(f"  *** CLOSE MATCH /100: {hum_be_100:.1f}% ***")
            if abs(hum_be_10 - target_humidity) < 5:
                print(f"  *** CLOSE MATCH /10: {hum_be_10:.1f}% ***")
        
        # Method 3: Individual bytes
        for i, byte_val in enumerate(data):
            print(f"  Byte {i}: {byte_val} (0x{byte_val:02x})")
            
            # Try direct byte value
            if abs(byte_val - target_humidity) < 5:
                print(f"    *** CLOSE MATCH direct: {byte_val}% ***")
                
            # Try byte / 5 (in case it's encoded in 5% steps)
            hum_div5 = byte_val * 5
            if 0 <= hum_div5 <= 100 and abs(hum_div5 - target_humidity) < 5:
                print(f"    *** CLOSE MATCH *5: {hum_div5}% ***")
                
            # Try byte / 2 (in case it's encoded in 2% steps)  
            hum_div2 = byte_val / 2
            if abs(hum_div2 - target_humidity) < 5:
                print(f"    *** CLOSE MATCH /2: {hum_div2:.1f}% ***")
        
        print()
    
    # Special test for 0xea = 234
    print("=== Special analysis for 0xea (234) ===")
    ea_val = 0xea
    print(f"0xea = {ea_val}")
    print(f"234 - 200 = {ea_val - 200}")  # Maybe offset encoding?
    print(f"234 - 185 = {ea_val - 185}")  # Try different offset
    print(f"255 - 234 = {255 - ea_val}")  # Inverted?
    
    # Check if it could be encoded as percentage of 255
    hum_percent = (ea_val / 255.0) * 100
    print(f"(234/255) * 100 = {hum_percent:.1f}%")
    
    # Check if it's related to our target by some factor
    factor = ea_val / target_humidity
    print(f"234 / 48.5 = {factor:.2f}")

if __name__ == "__main__":
    test_humidity_decoding()