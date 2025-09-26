"""MQTT publisher for Xiaomi BLE temperature sensors with Home Assistant discovery."""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .bluetooth_manager import SensorData
from .constants import MQTT_TOPICS, HA_DEVICE_CLASSES


logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """MQTT connection configuration."""
    broker_host: str
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "mijia-ble-daemon"
    keepalive: int = 60
    qos: int = 0
    retain: bool = True
    discovery_prefix: str = "homeassistant"


class MQTTPublisher:
    """Publishes sensor data to MQTT with Home Assistant discovery support."""
    
    def __init__(self, config: MQTTConfig, on_connect: Optional[Callable] = None):
        """Initialize MQTT publisher.
        
        Args:
            config: MQTT connection configuration
            on_connect: Optional callback when MQTT connects
        """
        self.config = config
        self._on_connect_callback = on_connect
        self._client: Optional[mqtt.Client] = None
        self._is_connected = False
        self._discovered_devices = set()
        
    async def start(self) -> None:
        """Start MQTT connection."""
        logger.info(f"Starting MQTT publisher, connecting to {self.config.broker_host}:{self.config.broker_port}")
        
        # Create MQTT client with callback API version 2
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self.config.client_id
        )
        
        # Set up authentication if provided
        if self.config.username and self.config.password:
            self._client.username_pw_set(self.config.username, self.config.password)
            
        # Configure callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
        
        try:
            # Connect to broker
            self._client.connect(
                host=self.config.broker_host,
                port=self.config.broker_port,
                keepalive=self.config.keepalive
            )
            
            # Start network loop in background
            self._client.loop_start()
            
            # Wait a bit for connection to establish
            import asyncio
            await asyncio.sleep(1)
            
            if not self._is_connected:
                logger.warning("MQTT connection not established immediately, continuing anyway")
                
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
            
    async def stop(self) -> None:
        """Stop MQTT connection."""
        if self._client:
            logger.info("Stopping MQTT publisher")
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._is_connected = False
            
    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        """Callback when MQTT connects."""
        if reason_code == 0:
            self._is_connected = True
            logger.info("Connected to MQTT broker")
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            logger.error(f"Failed to connect to MQTT broker: {reason_code}")
            
    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        """Callback when MQTT disconnects."""
        self._is_connected = False
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")
        
    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None) -> None:
        """Callback when message is published."""
        logger.debug(f"Published message {mid}")
        
    @property
    def is_connected(self) -> bool:
        """Check if MQTT is connected."""
        return self._is_connected
        
    async def publish_sensor_data(self, device_id: str, data: SensorData) -> bool:
        """Publish sensor data for a device.
        
        Args:
            device_id: Unique device identifier (MAC address without colons)
            data: Sensor data to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self._client or not self._is_connected:
            logger.warning("MQTT not connected, cannot publish data")
            return False
            
        try:
            # Ensure Home Assistant discovery is set up for this device
            await self._setup_discovery(device_id)
            
            # Publish state data as single JSON message
            state_topic = MQTT_TOPICS["state"].format(device_id=device_id)
            payload = json.dumps(data.to_dict())
            
            result = self._client.publish(
                topic=state_topic,
                payload=payload,
                qos=self.config.qos,
                retain=self.config.retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published data for {device_id}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish data for {device_id}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing data for {device_id}: {e}")
            return False
            
    async def _setup_discovery(self, device_id: str) -> None:
        """Set up Home Assistant MQTT discovery for a device.
        
        Args:
            device_id: Unique device identifier
        """
        if device_id in self._discovered_devices:
            return
            
        logger.info(f"Setting up Home Assistant discovery for device {device_id}")
        
        # Base device info
        device_info = {
            "identifiers": [f"mijiableht_{device_id}"],
            "manufacturer": "Xiaomi",
            "model": "Mijia BLE Thermometer",
            "name": f"Mijia Thermometer {device_id[-4:]}",  # Last 4 chars of MAC
            "via_device": "mijia-ble-daemon"
        }
        
        # State topic where all sensor data is published
        state_topic = MQTT_TOPICS["state"].format(device_id=device_id)
        
        # Create discovery configs for each sensor type
        sensors = [
            {
                "type": "temperature",
                "name": "Temperature",
                "unit": "°C",
                "device_class": HA_DEVICE_CLASSES["temperature"],
                "value_template": "{{ value_json.temperature }}",
                "icon": "mdi:thermometer"
            },
            {
                "type": "humidity", 
                "name": "Humidity",
                "unit": "%",
                "device_class": HA_DEVICE_CLASSES["humidity"],
                "value_template": "{{ value_json.humidity }}",
                "icon": "mdi:water-percent"
            },
            {
                "type": "battery",
                "name": "Battery",
                "unit": "%", 
                "device_class": HA_DEVICE_CLASSES["battery"],
                "value_template": "{{ value_json.battery }}",
                "icon": "mdi:battery"
            }
        ]
        
        # Publish discovery config for each sensor
        for sensor in sensors:
            config_topic = MQTT_TOPICS["discovery"].format(
                discovery_prefix=self.config.discovery_prefix,
                device_id=device_id,
                sensor_type=sensor["type"]
            )
            
            config = {
                "name": f"{device_info['name']} {sensor['name']}",
                "unique_id": f"mijiableht_{device_id}_{sensor['type']}",
                "state_topic": state_topic,
                "value_template": sensor["value_template"],
                "unit_of_measurement": sensor["unit"],
                "device_class": sensor["device_class"],
                "icon": sensor["icon"],
                "device": device_info,
                "availability": {
                    "topic": state_topic,
                    "value_template": "{{ 'online' if value_json.last_seen else 'offline' }}"
                },
                "expire_after": 900  # 15 minutes
            }
            
            result = self._client.publish(
                topic=config_topic,
                payload=json.dumps(config),
                qos=self.config.qos,
                retain=True
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published discovery config for {device_id} {sensor['type']}")
            else:
                logger.error(f"Failed to publish discovery config for {device_id} {sensor['type']}: {result.rc}")
                
        # Mark device as discovered
        self._discovered_devices.add(device_id)
        
    async def remove_device_discovery(self, device_id: str) -> None:
        """Remove Home Assistant discovery for a device.
        
        Args:
            device_id: Unique device identifier
        """
        if not self._client or not self._is_connected:
            return
            
        logger.info(f"Removing Home Assistant discovery for device {device_id}")
        
        # Remove discovery configs for each sensor type
        for sensor_type in ["temperature", "humidity", "battery"]:
            config_topic = MQTT_TOPICS["discovery"].format(
                discovery_prefix=self.config.discovery_prefix,
                device_id=device_id,
                sensor_type=sensor_type
            )
            
            # Publish empty payload to remove discovery
            self._client.publish(
                topic=config_topic,
                payload="",
                qos=self.config.qos,
                retain=True
            )
            
        # Remove from discovered devices
        self._discovered_devices.discard(device_id)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics.
        
        Returns:
            Dictionary with publisher stats
        """
        return {
            "connected": self._is_connected,
            "broker": f"{self.config.broker_host}:{self.config.broker_port}",
            "discovered_devices": len(self._discovered_devices),
            "device_list": list(self._discovered_devices)
        }