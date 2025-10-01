"""
Constants and configuration for Xiaomi Mijia Bluetooth Daemon.

Contains device modes, MQTT topics, and other shared constants.
"""

# Supported device modes
SUPPORTED_DEVICE_MODES = {
    "LYWSD03MMC": "Mijia BLE Temperature Hygrometer 2",
    "LYWSDCGQ/01ZM": "Original Mijia BLE Temperature Hygrometer"
}

# Default configuration values
DEFAULT_CONFIG = {
    "bluetooth": {
        "adapter": 0,
        "scan_interval": 300,
        "connection_timeout": 10,
        "retry_attempts": 3
    },
    "mqtt": {
        "broker_host": "localhost",
        "broker_port": 1883,
        "client_id": "mijia-ble-daemon",
        "username": None,
        "password": None,
        "keepalive": 60,
        "qos": 0,
        "retain": True,
        "discovery_prefix": "homeassistant"
    },
    "devices": {
        "auto_discovery": True,
        "poll_interval": 300,
        "static_devices": []
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
}

# MQTT topic patterns
MQTT_TOPICS = {
    "state": "mijiableht/{device_id}/state",
    "discovery": "{discovery_prefix}/sensor/mijiableht_{device_id}_{sensor_type}/config"
}

# Home Assistant device classes
HA_DEVICE_CLASSES = {
    "temperature": "temperature",
    "humidity": "humidity", 
    "battery": "battery"
}

# Units of measurement
UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "battery": "%"
}

# RSSI signal strength interpretation
def interpret_rssi(rssi: int | None) -> str:
    """
    Interpret RSSI value into human-readable signal strength.
    Optimized for indoor Bluetooth Low Energy applications.
    
    Args:
        rssi: RSSI value in dBm (negative integer)
        
    Returns:
        Human-readable signal strength description
    """
    if rssi is None:
        return "unknown"
    
    if rssi >= -50:
        return "excellent"
    elif rssi >= -60:
        return "good"
    elif rssi >= -70:
        return "fair"
    elif rssi >= -80:
        return "weak"
    else:
        return "very weak"