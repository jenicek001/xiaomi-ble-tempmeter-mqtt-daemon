"""Tests for MQTT publisher module."""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, call
from datetime import datetime

import paho.mqtt.client as mqtt
from src.mqtt_publisher import MQTTPublisher, MQTTConfig
from src.bluetooth_manager import SensorData


@pytest.fixture
def mqtt_config():
    """Create test MQTT configuration."""
    return MQTTConfig(
        broker_host="localhost",
        broker_port=1883,
        username="test_user",
        password="test_pass",
        client_id="test_client"
    )


@pytest.fixture
def sample_sensor_data():
    """Create sample sensor data."""
    return SensorData(
        temperature=23.5,
        humidity=45,
        battery=78,
        voltage=2.98,
        timestamp=datetime(2025, 1, 14, 10, 30, 45)
    )


@pytest.fixture
def mock_mqtt_client():
    """Create mock MQTT client."""
    with patch('paho.mqtt.client.Client') as mock_client_class:
        mock_client = Mock()
        mock_client.connect.return_value = Mock()
        mock_client.loop_start.return_value = None
        mock_client.loop_stop.return_value = None
        mock_client.disconnect.return_value = None
        mock_client.publish.return_value = Mock(rc=mqtt.MQTT_ERR_SUCCESS)
        mock_client_class.return_value = mock_client
        yield mock_client


class TestMQTTConfig:
    """Test MQTT configuration dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = MQTTConfig(broker_host="test.broker")
        
        assert config.broker_host == "test.broker"
        assert config.broker_port == 1883
        assert config.username is None
        assert config.password is None
        assert config.client_id == "mijia-ble-daemon"
        assert config.keepalive == 60
        assert config.qos == 0
        assert config.retain is True
        assert config.discovery_prefix == "homeassistant"
        
    def test_custom_values(self):
        """Test custom configuration values."""
        config = MQTTConfig(
            broker_host="custom.broker",
            broker_port=8883,
            username="user",
            password="pass",
            client_id="custom_client",
            keepalive=30,
            qos=1,
            retain=False,
            discovery_prefix="ha"
        )
        
        assert config.broker_host == "custom.broker"
        assert config.broker_port == 8883
        assert config.username == "user"
        assert config.password == "pass"
        assert config.client_id == "custom_client"
        assert config.keepalive == 30
        assert config.qos == 1
        assert config.retain is False
        assert config.discovery_prefix == "ha"


class TestMQTTPublisher:
    """Test MQTT publisher class."""
    
    def test_init(self, mqtt_config):
        """Test publisher initialization."""
        on_connect = Mock()
        publisher = MQTTPublisher(mqtt_config, on_connect)
        
        assert publisher.config == mqtt_config
        assert publisher._on_connect_callback == on_connect
        assert publisher._client is None
        assert publisher._is_connected is False
        assert publisher._discovered_devices == set()
        
    @pytest.mark.asyncio
    async def test_start_success(self, mqtt_config, mock_mqtt_client):
        """Test successful MQTT start."""
        publisher = MQTTPublisher(mqtt_config)
        
        await publisher.start()
        
        # Verify client creation and configuration
        mock_mqtt_client.username_pw_set.assert_called_once_with("test_user", "test_pass")
        mock_mqtt_client.connect.assert_called_once_with(
            host="localhost",
            port=1883,
            keepalive=60
        )
        mock_mqtt_client.loop_start.assert_called_once()
        
        # Verify callbacks are set
        assert mock_mqtt_client.on_connect is not None
        assert mock_mqtt_client.on_disconnect is not None
        assert mock_mqtt_client.on_publish is not None
        
    @pytest.mark.asyncio
    async def test_start_no_auth(self, mock_mqtt_client):
        """Test MQTT start without authentication."""
        config = MQTTConfig(broker_host="localhost")
        publisher = MQTTPublisher(config)
        
        await publisher.start()
        
        # Should not set authentication
        mock_mqtt_client.username_pw_set.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_start_connection_error(self, mqtt_config, mock_mqtt_client):
        """Test MQTT start with connection error."""
        mock_mqtt_client.connect.side_effect = Exception("Connection failed")
        
        publisher = MQTTPublisher(mqtt_config)
        
        with pytest.raises(Exception, match="Connection failed"):
            await publisher.start()
            
    @pytest.mark.asyncio
    async def test_stop(self, mqtt_config, mock_mqtt_client):
        """Test MQTT stop."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        
        await publisher.stop()
        
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
        assert publisher._client is None
        assert publisher._is_connected is False
        
    def test_on_connect_success(self, mqtt_config):
        """Test successful connection callback."""
        on_connect_callback = Mock()
        publisher = MQTTPublisher(mqtt_config, on_connect_callback)
        
        # Simulate successful connection
        publisher._on_connect(None, None, None, 0)
        
        assert publisher._is_connected is True
        on_connect_callback.assert_called_once()
        
    def test_on_connect_failure(self, mqtt_config):
        """Test failed connection callback."""
        publisher = MQTTPublisher(mqtt_config)
        
        # Simulate failed connection
        publisher._on_connect(None, None, None, 1)
        
        assert publisher._is_connected is False
        
    def test_on_disconnect(self, mqtt_config):
        """Test disconnect callback."""
        publisher = MQTTPublisher(mqtt_config)
        publisher._is_connected = True
        
        publisher._on_disconnect(None, None, None, 0)
        
        assert publisher._is_connected is False
        
    def test_is_connected_property(self, mqtt_config):
        """Test is_connected property."""
        publisher = MQTTPublisher(mqtt_config)
        
        assert publisher.is_connected is False
        
        publisher._is_connected = True
        assert publisher.is_connected is True
        
    @pytest.mark.asyncio
    async def test_publish_sensor_data_not_connected(self, mqtt_config, sample_sensor_data):
        """Test publishing when not connected."""
        publisher = MQTTPublisher(mqtt_config)
        
        result = await publisher.publish_sensor_data("A4C1384B1234", sample_sensor_data)
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_publish_sensor_data_success(self, mqtt_config, mock_mqtt_client, sample_sensor_data):
        """Test successful sensor data publishing."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._is_connected = True
        
        # Mock discovery setup
        publisher._setup_discovery = AsyncMock()
        
        result = await publisher.publish_sensor_data("A4C1384B1234", sample_sensor_data)
        
        assert result is True
        
        # Verify discovery was called
        publisher._setup_discovery.assert_called_once_with("A4C1384B1234")
        
        # Verify publish was called with correct parameters
        expected_topic = "mijiableht/A4C1384B1234/state"
        expected_payload = json.dumps(sample_sensor_data.to_dict())
        
        mock_mqtt_client.publish.assert_called_once_with(
            topic=expected_topic,
            payload=expected_payload,
            qos=0,
            retain=True
        )
        
    @pytest.mark.asyncio
    async def test_publish_sensor_data_publish_failure(self, mqtt_config, mock_mqtt_client, sample_sensor_data):
        """Test sensor data publishing with MQTT publish failure."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._is_connected = True
        
        # Mock publish failure
        mock_mqtt_client.publish.return_value = Mock(rc=mqtt.MQTT_ERR_NO_CONN)
        publisher._setup_discovery = AsyncMock()
        
        result = await publisher.publish_sensor_data("A4C1384B1234", sample_sensor_data)
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_setup_discovery_first_time(self, mqtt_config, mock_mqtt_client):
        """Test setting up discovery for first time."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._is_connected = True
        
        await publisher._setup_discovery("A4C1384B1234")
        
        # Should publish 3 discovery configs (temperature, humidity, battery)
        assert mock_mqtt_client.publish.call_count == 3
        
        # Verify device is marked as discovered
        assert "A4C1384B1234" in publisher._discovered_devices
        
        # Verify discovery topics
        calls = mock_mqtt_client.publish.call_args_list
        topics = [call[1]["topic"] for call in calls]
        
        expected_topics = [
            "homeassistant/sensor/mijiableht_A4C1384B1234_temperature/config",
            "homeassistant/sensor/mijiableht_A4C1384B1234_humidity/config",
            "homeassistant/sensor/mijiableht_A4C1384B1234_battery/config"
        ]
        
        for expected_topic in expected_topics:
            assert expected_topic in topics
            
    @pytest.mark.asyncio
    async def test_setup_discovery_already_discovered(self, mqtt_config, mock_mqtt_client):
        """Test setting up discovery for already discovered device."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._discovered_devices.add("A4C1384B1234")
        
        await publisher._setup_discovery("A4C1384B1234")
        
        # Should not publish any discovery configs
        mock_mqtt_client.publish.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_setup_discovery_config_content(self, mqtt_config, mock_mqtt_client):
        """Test discovery configuration content."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._is_connected = True
        
        await publisher._setup_discovery("A4C1384B1234")
        
        # Get temperature sensor config
        temp_call = None
        for call in mock_mqtt_client.publish.call_args_list:
            if "temperature" in call[1]["topic"]:
                temp_call = call
                break
                
        assert temp_call is not None
        
        config = json.loads(temp_call[1]["payload"])
        
        # Verify config structure
        assert config["name"] == "Mijia Thermometer 1234 Temperature"
        assert config["unique_id"] == "mijiableht_A4C1384B1234_temperature"
        assert config["state_topic"] == "mijiableht/A4C1384B1234/state"
        assert config["value_template"] == "{{ value_json.temperature }}"
        assert config["unit_of_measurement"] == "°C"
        assert config["device_class"] == "temperature"
        assert config["icon"] == "mdi:thermometer"
        assert config["expire_after"] == 900
        
        # Verify device info
        device_info = config["device"]
        assert device_info["identifiers"] == ["mijiableht_A4C1384B1234"]
        assert device_info["manufacturer"] == "Xiaomi"
        assert device_info["model"] == "Mijia BLE Thermometer"
        assert device_info["name"] == "Mijia Thermometer 1234"
        
    @pytest.mark.asyncio
    async def test_remove_device_discovery(self, mqtt_config, mock_mqtt_client):
        """Test removing device discovery."""
        publisher = MQTTPublisher(mqtt_config)
        await publisher.start()
        publisher._is_connected = True
        publisher._discovered_devices.add("A4C1384B1234")
        
        await publisher.remove_device_discovery("A4C1384B1234")
        
        # Should publish 3 empty payloads to remove discovery
        assert mock_mqtt_client.publish.call_count == 3
        
        # Verify all payloads are empty
        for call in mock_mqtt_client.publish.call_args_list:
            assert call[1]["payload"] == ""
            
        # Verify device is removed from discovered devices
        assert "A4C1384B1234" not in publisher._discovered_devices
        
    @pytest.mark.asyncio
    async def test_remove_device_discovery_not_connected(self, mqtt_config):
        """Test removing device discovery when not connected."""
        publisher = MQTTPublisher(mqtt_config)
        
        await publisher.remove_device_discovery("A4C1384B1234")
        
        # Should do nothing when not connected
        # No way to verify this without accessing internal state
        
    def test_get_stats(self, mqtt_config):
        """Test getting publisher statistics."""
        publisher = MQTTPublisher(mqtt_config)
        publisher._is_connected = True
        publisher._discovered_devices.add("A4C1384B1234")
        publisher._discovered_devices.add("A4C1384B5678")
        
        stats = publisher.get_stats()
        
        expected_stats = {
            "connected": True,
            "broker": "localhost:1883",
            "discovered_devices": 2,
            "device_list": ["A4C1384B1234", "A4C1384B5678"]
        }
        
        assert stats["connected"] == expected_stats["connected"]
        assert stats["broker"] == expected_stats["broker"]
        assert stats["discovered_devices"] == expected_stats["discovered_devices"]
        assert set(stats["device_list"]) == set(expected_stats["device_list"])


@pytest.mark.asyncio
async def test_integration_publish_flow(mqtt_config, mock_mqtt_client, sample_sensor_data):
    """Test complete integration flow of publishing sensor data."""
    publisher = MQTTPublisher(mqtt_config)
    
    # Start publisher
    await publisher.start()
    publisher._is_connected = True
    
    # Publish data for new device
    result = await publisher.publish_sensor_data("A4C1384B1234", sample_sensor_data)
    
    assert result is True
    
    # Verify discovery was set up (3 discovery configs + 1 state message)
    assert mock_mqtt_client.publish.call_count == 4
    
    # Publish data for same device again
    mock_mqtt_client.reset_mock()
    result = await publisher.publish_sensor_data("A4C1384B1234", sample_sensor_data)
    
    assert result is True
    
    # Should only publish state (no discovery setup)
    assert mock_mqtt_client.publish.call_count == 1
    
    # Stop publisher
    await publisher.stop()
    
    assert publisher._client is None
    assert publisher._is_connected is False