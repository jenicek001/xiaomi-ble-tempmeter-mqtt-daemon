#!/usr/bin/env python3
"""
Test bleak API to understand the correct method names.
"""

import asyncio
from bleak import BleakClient


async def test_bleak_api():
    """Check what methods are available in bleak."""
    target_mac = "4C:65:A8:DC:84:01"
    
    try:
        async with BleakClient(target_mac, timeout=15) as client:
            if client.is_connected:
                print("✅ Connected - checking available methods:")
                
                # List all available methods
                methods = [method for method in dir(client) if not method.startswith('_')]
                print(f"Available methods: {', '.join(methods)}")
                
                # Try different service discovery methods
                try:
                    if hasattr(client, 'services'):
                        services = client.services
                        print(f"✅ client.services worked: {len(services)} services")
                    elif hasattr(client, 'get_services'):
                        services = await client.get_services()
                        print(f"✅ client.get_services() worked: {len(services)} services")
                    else:
                        print("❌ No service discovery method found")
                        
                except Exception as e:
                    print(f"❌ Service discovery error: {e}")
                    
    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_bleak_api())