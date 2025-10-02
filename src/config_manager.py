
"""
Configuration Management for Xiaomi Mijia Daemon.

Loads and validates configuration from:
- YAML config file
- Environment variables (.env)
- Docker secrets (if present)
- Command line arguments (future)
"""


import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any, List

import yaml
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class MQTTConfigModel(BaseModel):
    broker_host: str
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "mijia-ble-daemon"
    keepalive: int = 60
    qos: int = 0
    retain: bool = True
    discovery_prefix: str = "homeassistant"
    publish_interval: int = 300  # Fixed interval publishing in seconds

class BluetoothConfigModel(BaseModel):
    adapter: int = 0
    connection_timeout: int = 10
    retry_attempts: int = 3

class ThresholdsConfigModel(BaseModel):
    temperature: float = 0.2  # °C threshold for immediate publishing
    humidity: float = 1.0     # % RH threshold for immediate publishing

class StaticDeviceModel(BaseModel):
    mac: str  # Device MAC address
    friendly_name: Optional[str] = None  # Optional friendly name for the device

class DevicesConfigModel(BaseModel):
    auto_discovery: bool = True
    static_devices: List[StaticDeviceModel] = Field(default_factory=list)

class LoggingConfigModel(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None

class DaemonConfigModel(BaseModel):
    mqtt: MQTTConfigModel
    bluetooth: BluetoothConfigModel
    devices: DevicesConfigModel
    thresholds: ThresholdsConfigModel
    logging: LoggingConfigModel

class ConfigManager:
    """Manages daemon configuration from multiple sources."""

    def __init__(self, config_file: Optional[str] = None, dotenv_path: Optional[str] = None):
        self.config_file = config_file or "config/config.yaml"
        self.dotenv_path = dotenv_path or ".env"
        self._config: Optional[DaemonConfigModel] = None

    def get_config(self) -> DaemonConfigModel:
        """
        Load and validate configuration from all sources.
        Returns:
            Validated configuration object
        """
        # 1. Load .env if present
        if Path(self.dotenv_path).exists():
            load_dotenv(self.dotenv_path, override=True)

        # 2. Load YAML config
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        with open(self.config_file, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # 3. Load Docker secrets (if any)
        self._load_docker_secrets(yaml_config)

        # 4. Manually override with environment variables (Pydantic v2 does not support env=...)
        yaml_config = self._apply_env_overrides(yaml_config)
        try:
            config = DaemonConfigModel(**yaml_config)
        except ValidationError as e:
            raise RuntimeError(f"Configuration validation error: {e}")

        self._config = config
        return config

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Override config dict with environment variables if set."""
        env_map = {
            ("mqtt", "broker_host"): "MIJIA_MQTT_BROKER_HOST",
            ("mqtt", "broker_port"): "MIJIA_MQTT_BROKER_PORT",
            ("mqtt", "username"): "MIJIA_MQTT_USERNAME",
            ("mqtt", "password"): "MIJIA_MQTT_PASSWORD",
            ("mqtt", "client_id"): "MIJIA_MQTT_CLIENT_ID",
            ("mqtt", "keepalive"): "MIJIA_MQTT_KEEPALIVE",
            ("mqtt", "qos"): "MIJIA_MQTT_QOS",
            ("mqtt", "retain"): "MIJIA_MQTT_RETAIN",
            ("mqtt", "discovery_prefix"): "MIJIA_MQTT_DISCOVERY_PREFIX",
            ("mqtt", "publish_interval"): "MIJIA_MQTT_PUBLISH_INTERVAL",
            ("bluetooth", "adapter"): "MIJIA_BLUETOOTH_ADAPTER",
            ("bluetooth", "connection_timeout"): "MIJIA_BLUETOOTH_CONNECTION_TIMEOUT",
            ("bluetooth", "retry_attempts"): "MIJIA_BLUETOOTH_RETRY_ATTEMPTS",
            ("devices", "auto_discovery"): "MIJIA_DEVICES_AUTO_DISCOVERY",
            ("thresholds", "temperature"): "MIJIA_TEMPERATURE_THRESHOLD",
            ("thresholds", "humidity"): "MIJIA_HUMIDITY_THRESHOLD",
            ("logging", "level"): "MIJIA_LOG_LEVEL",
            ("logging", "format"): "MIJIA_LOG_FORMAT",
            ("logging", "file"): "MIJIA_LOG_FILE",
        }
        for (section, key), env_var in env_map.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Convert types for int/bool fields
                if section in config and key in config[section]:
                    orig = config[section][key]
                    if isinstance(orig, bool):
                        value = value.lower() in ("1", "true", "yes", "on")
                    elif isinstance(orig, int):
                        try:
                            value = int(value)
                        except Exception:
                            pass
                config.setdefault(section, {})[key] = value
        return config

    def _load_docker_secrets(self, config: Dict[str, Any]) -> None:
        """Load Docker secrets from /run/secrets if present and override config dict."""
        secrets_dir = Path("/run/secrets")
        if not secrets_dir.exists():
            return
        # Map secret files to config keys (example: mqtt_password)
        secret_map = {
            "mqtt_password": ("mqtt", "password"),
        }
        for secret_file, (section, key) in secret_map.items():
            secret_path = secrets_dir / secret_file
            if secret_path.exists():
                with open(secret_path, "r", encoding="utf-8") as f:
                    secret_value = f.read().strip()
                config.setdefault(section, {})[key] = secret_value

    def reload_config(self) -> None:
        """Reload configuration from sources."""
        self._config = None
        self.get_config()

    def validate_config(self, config: DaemonConfigModel) -> bool:
        """
        Validate configuration using Pydantic models.
        Args:
            config: Configuration object to validate
        Returns:
            True if valid, raises exception if invalid
        """
        try:
            config = DaemonConfigModel(**config.dict())
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        return True
        
    def reload_config(self) -> None:
        """Reload configuration from sources."""
        # TODO: Implement hot-reload capability
        logger.info("Configuration reload not yet implemented")
        
    def validate_config(self, config: Dict) -> bool:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, raises exception if invalid
        """
        # TODO: Implement Pydantic validation
        logger.info("Configuration validation not yet implemented")
        return True