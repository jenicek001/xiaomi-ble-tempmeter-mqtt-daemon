"""
Tests for Configuration Manager.

TODO: Implement in Step 7 - Comprehensive Testing Suite  
- Test YAML configuration loading
- Test environment variable overrides
- Test Pydantic validation
- Test configuration error handling
"""

import os
import tempfile
import yaml
import pytest
from pathlib import Path
from src.config_manager import ConfigManager, DaemonConfigModel

SAMPLE_YAML = {
    "mqtt": {
        "broker_host": "localhost",
        "broker_port": 1883,
        "username": "user",
        "password": "pass",
        "client_id": "test-client",
        "keepalive": 60,
        "qos": 1,
        "retain": True,
        "discovery_prefix": "homeassistant"
    },
    "bluetooth": {
        "adapter": 0,
        "scan_interval": 300,
        "connection_timeout": 10,
        "retry_attempts": 3
    },
    "devices": {
        "auto_discovery": True,
        "poll_interval": 300,
        "static_devices": []
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": None
    }
}

@pytest.fixture
def temp_yaml_file():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as f:
        yaml.dump(SAMPLE_YAML, f)
        f.flush()
        yield f.name
    os.remove(f.name)

def test_load_yaml_config(temp_yaml_file):
    cm = ConfigManager(config_file=temp_yaml_file)
    config = cm.get_config()
    assert isinstance(config, DaemonConfigModel)
    assert config.mqtt.broker_host == "localhost"
    assert config.mqtt.client_id == "test-client"
    assert config.bluetooth.adapter == 0
    assert config.devices.auto_discovery is True
    assert config.logging.level == "INFO"

def test_env_override(temp_yaml_file, monkeypatch):
    monkeypatch.setenv("MIJIA_MQTT_BROKER_HOST", "envhost")
    cm = ConfigManager(config_file=temp_yaml_file)
    config = cm.get_config()
    assert config.mqtt.broker_host == "envhost"

def test_invalid_config_raises(temp_yaml_file):
    # Remove required field
    with open(temp_yaml_file, "r") as f:
        data = yaml.safe_load(f)
    del data["mqtt"]["broker_host"]
    with open(temp_yaml_file, "w") as f:
        yaml.dump(data, f)
    cm = ConfigManager(config_file=temp_yaml_file)
    with pytest.raises(Exception):
        cm.get_config()

def test_reload_config(temp_yaml_file):
    cm = ConfigManager(config_file=temp_yaml_file)
    config1 = cm.get_config()
    cm.reload_config()
    config2 = cm.get_config()
    assert config1.mqtt.broker_host == config2.mqtt.broker_host