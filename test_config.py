#!/usr/bin/env python3
"""
Test configuration management: loading, validation, error handling.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from config_manager import ConfigManager
    import yaml
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with pydantic --with pyyaml --with python-dotenv python test_config.py")
    exit(1)


def test_config_loading():
    """Test normal configuration loading."""
    print("📄 Testing Normal Configuration Loading")
    print("=" * 40)
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        print("✅ Configuration loaded successfully")
        print(f"   🏠 MQTT: {config.mqtt.broker_host}:{config.mqtt.broker_port}")
        print(f"   📡 Bluetooth: adapter {config.bluetooth.adapter}")
        print(f"   🔧 Devices: {len(config.devices.static_devices)} configured")
        print(f"   📝 Logging: {config.logging.level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


def test_missing_config_file():
    """Test behavior with missing config file."""
    print("\n📄 Testing Missing Config File")
    print("=" * 40)
    
    try:
        # Create config manager pointing to non-existent file
        config_manager = ConfigManager(config_file="nonexistent.yaml")
        config = config_manager.get_config()
        
        print("❌ Should have failed with missing file")
        return False
        
    except FileNotFoundError as e:
        print(f"✅ Correctly detected missing file: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_invalid_yaml():
    """Test behavior with invalid YAML."""
    print("\n📄 Testing Invalid YAML")
    print("=" * 40)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: {")
        temp_file = f.name
    
    try:
        config_manager = ConfigManager(config_file=temp_file)
        config = config_manager.get_config()
        
        print("❌ Should have failed with invalid YAML")
        return False
        
    except Exception as e:
        print(f"✅ Correctly detected invalid YAML: {type(e).__name__}")
        return True
    finally:
        os.unlink(temp_file)


def test_missing_required_fields():
    """Test behavior with missing required configuration fields."""
    print("\n📄 Testing Missing Required Fields")
    print("=" * 40)
    
    # Create minimal invalid config
    invalid_config = {
        "mqtt": {},  # Missing required fields
        "bluetooth": {},
        "devices": {},
        "logging": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = f.name
    
    try:
        config_manager = ConfigManager(config_file=temp_file)
        config = config_manager.get_config()
        
        print("❌ Should have failed with missing required fields")
        return False
        
    except Exception as e:
        print(f"✅ Correctly detected missing required fields: {type(e).__name__}")
        return True
    finally:
        os.unlink(temp_file)


def test_env_override():
    """Test environment variable override."""
    print("\n📄 Testing Environment Variable Override")
    print("=" * 40)
    
    # Set environment variable
    original_host = os.environ.get("MIJIA_MQTT_BROKER_HOST")
    os.environ["MIJIA_MQTT_BROKER_HOST"] = "test-override-host"
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        if config.mqtt.broker_host == "test-override-host":
            print("✅ Environment variable override works")
            return True
        else:
            print(f"❌ Environment override failed: got {config.mqtt.broker_host}")
            return False
            
    except Exception as e:
        print(f"❌ Environment override test failed: {e}")
        return False
    finally:
        # Restore original value
        if original_host:
            os.environ["MIJIA_MQTT_BROKER_HOST"] = original_host
        else:
            os.environ.pop("MIJIA_MQTT_BROKER_HOST", None)


def main():
    """Run all configuration tests."""
    print("🧪 Configuration Management Tests")
    print("=" * 50)
    
    tests = [
        test_config_loading,
        test_missing_config_file,
        test_invalid_yaml,
        test_missing_required_fields,
        test_env_override
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All configuration tests passed!")
    else:
        print("⚠️  Some configuration tests failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)