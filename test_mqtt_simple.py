#!/usr/bin/env python3
"""
Simple MQTT connectivity test.
Tests MQTT connection and basic publishing with the configured credentials.
"""

import json
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ paho-mqtt not available. Install with: pip install paho-mqtt")
    exit(1)


def test_mqtt_connection():
    """Test MQTT connection with configured credentials."""
    print("🧪 MQTT Connection Test")
    print("=" * 40)
    
    # Configuration from your .env file
    config = {
        'broker': 'localhost',
        'port': 1883,
        'username': 'openhabian',
        'password': 'M30ZeZuQo1bHjrn7g93k',
        'client_id': 'mqtt-test-client'
    }
    
    print(f"🔗 Connecting to {config['broker']}:{config['port']} as {config['username']}...")
    
    # Connection status tracking
    connection_status = {'connected': False, 'error': None}
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            connection_status['connected'] = True
            print("✅ MQTT connection successful!")
        else:
            connection_status['error'] = f"Connection failed with code {rc}"
            print(f"❌ MQTT connection failed: {rc}")
    
    def on_disconnect(client, userdata, rc):
        print(f"📤 Disconnected from MQTT broker (code: {rc})")
    
    def on_publish(client, userdata, mid):
        print(f"📤 Message {mid} published successfully")
    
    # Create MQTT client
    try:
        client = mqtt.Client(client_id=config['client_id'])
        client.username_pw_set(config['username'], config['password'])
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect  
        client.on_publish = on_publish
        
        # Connect
        client.connect(config['broker'], config['port'], 60)
        client.loop_start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not connection_status['connected'] and not connection_status['error']:
            if time.time() - start_time > timeout:
                print(f"❌ Connection timeout after {timeout} seconds")
                return False
            time.sleep(0.1)
        
        if connection_status['error']:
            print(f"❌ {connection_status['error']}")
            return False
        
        # Test publishing
        print("\n📤 Testing message publishing...")
        
        # Test 1: Basic message
        test_topic = "mijiableht/test/status"
        test_message = json.dumps({
            "status": "test",
            "timestamp": datetime.now().isoformat(),
            "device": "test-device"
        })
        
        result = client.publish(test_topic, test_message, qos=0, retain=True)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"✅ Published test message to {test_topic}")
        else:
            print(f"❌ Failed to publish test message: {result.rc}")
        
        # Test 2: Home Assistant discovery message
        discovery_topic = "homeassistant/sensor/mijiableht_test_temp/config"
        discovery_payload = json.dumps({
            "name": "Test Temperature",
            "unique_id": "mijiableht_test_temp", 
            "state_topic": "mijiableht/test/state",
            "value_template": "{{ value_json.temperature }}",
            "unit_of_measurement": "°C",
            "device_class": "temperature"
        })
        
        result = client.publish(discovery_topic, discovery_payload, qos=0, retain=True)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"✅ Published HA discovery message to {discovery_topic}")
        else:
            print(f"❌ Failed to publish HA discovery: {result.rc}")
        
        # Test 3: Sensor data message
        sensor_topic = "mijiableht/test/state"
        sensor_data = json.dumps({
            "temperature": 23.5,
            "humidity": 45.2,
            "battery": 78,
            "last_seen": datetime.now().isoformat()
        })
        
        result = client.publish(sensor_topic, sensor_data, qos=0, retain=True)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"✅ Published sensor data to {sensor_topic}")
        else:
            print(f"❌ Failed to publish sensor data: {result.rc}")
        
        # Wait a moment for messages to be sent
        time.sleep(2)
        
        # Clean up
        client.loop_stop()
        client.disconnect()
        
        print("\n🎉 MQTT test completed successfully!")
        print("\n💡 You can monitor messages with:")
        print("   mosquitto_sub -h localhost -u openhabian -P M30ZeZuQo1bHjrn7g93k -t 'mijiableht/#' -v")
        
        return True
        
    except Exception as e:
        print(f"❌ MQTT test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = test_mqtt_connection()
    exit(0 if success else 1)