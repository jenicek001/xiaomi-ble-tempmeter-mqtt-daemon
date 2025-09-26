#!/usr/bin/env python3
"""
Main entry point for Xiaomi Mijia Bluetooth Daemon.

This daemon connects to Xiaomi Mijia Bluetooth thermometers and publishes
sensor data to MQTT brokers with Home Assistant discovery support.

Original work based on mitemp_bt2 by @leonxi:
https://github.com/leonxi/mitemp_bt2
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Import implemented components
from .bluetooth_manager import BluetoothManager
from .mqtt_publisher import MQTTPublisher, MQTTConfig
# from .device_manager import DeviceManager  # TODO: Step 5
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class MijiaTemperatureDaemon:
    """Main daemon class that orchestrates all components."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the daemon with configuration."""
        self.config_file = config_file or "config/config.yaml"
        self.running = False
        # Component placeholders - will be initialized in setup phase
        self.config_manager = ConfigManager(self.config_file)
        self.bluetooth_manager = None
        self.device_manager = None
        self.mqtt_publisher = None
        
    async def start(self) -> None:
        """Start the daemon and all its components."""
        logger.info("Starting Xiaomi Mijia Bluetooth Daemon...")
        try:
            # Load and validate config
            config = self.config_manager.get_config()

            # Initialize Bluetooth manager
            bluetooth_config = config.bluetooth.model_dump()
            bluetooth_config['static_devices'] = config.devices.static_devices
            self.bluetooth_manager = BluetoothManager(bluetooth_config)
            logger.info("Bluetooth manager initialized")

            # Initialize MQTT publisher
            mqtt_config = MQTTConfig(
                broker_host=config.mqtt.broker_host,
                broker_port=config.mqtt.broker_port,
                username=config.mqtt.username,
                password=config.mqtt.password,
                client_id=config.mqtt.client_id,
                qos=config.mqtt.qos,
                retain=config.mqtt.retain,
                discovery_prefix=config.mqtt.discovery_prefix
            )
            self.mqtt_publisher = MQTTPublisher(mqtt_config)
            await self.mqtt_publisher.start()
            logger.info("MQTT publisher initialized")

            # TODO: Implement in step 5 (device manager)
            # self.device_manager = DeviceManager(config.devices.model_dump())

            self.running = True
            logger.info("Daemon started successfully")

            # Main daemon loop
            await self._main_loop()

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            raise
            
    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        logger.info("Stopping Xiaomi Mijia Bluetooth Daemon...")
        self.running = False
        
        try:
            # Cleanup components in reverse order
            if self.mqtt_publisher:
                logger.debug("Stopping MQTT publisher...")
                await self.mqtt_publisher.stop()
                
            if self.bluetooth_manager:
                logger.debug("Cleaning up Bluetooth manager...")
                await self.bluetooth_manager.cleanup()
                
            logger.info("Daemon stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            logger.info("Daemon stopped with errors")
        
    async def _main_loop(self) -> None:
        """Main daemon execution loop."""
        # Perform initial device discovery
        logger.info("Performing initial device discovery...")
        discovered_devices = await self.bluetooth_manager.discover_devices()

        if not discovered_devices:
            logger.warning("No Xiaomi devices found during initial scan")

        # For now, demonstrate reading from discovered devices
        poll_interval = 300
        if self.config_manager and self.config_manager._config:
            poll_interval = self.config_manager._config.devices.poll_interval

        while self.running:
            try:
                # Test reading data from discovered devices
                for device in discovered_devices:
                    if not self.running:  # Check running state between devices
                        break
                        
                    mac = device["mac"]
                    mode = device["mode"]
                    logger.info(f"Reading data from {device['name']} ({mac})")

                    try:
                        sensor_data = await self.bluetooth_manager.read_device_data(mac, mode)
                        if sensor_data:
                            logger.info(f"Device {mac}: {sensor_data.to_dict()}")

                            # Publish to MQTT (Step 3 - completed)
                            device_id = mac.replace(":", "").replace("-", "")  # Clean MAC for device ID
                            success = await self.mqtt_publisher.publish_sensor_data(device_id, sensor_data)
                            if success:
                                logger.debug(f"Published data for {mac} to MQTT")
                            else:
                                logger.warning(f"Failed to publish data for {mac} to MQTT")
                        else:
                            logger.warning(f"Failed to read data from {mac}")
                    except Exception as e:
                        logger.error(f"Error reading from device {mac}: {e}")

                if not self.running:
                    break

                # Sleep for polling interval with periodic checks
                logger.debug(f"Sleeping for {poll_interval} seconds...")
                for _ in range(poll_interval):
                    if not self.running:
                        break
                    await asyncio.sleep(1)  # Sleep 1 second at a time for responsiveness

            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                if self.running:  # Only sleep if we're still supposed to be running
                    for _ in range(30):  # Brief pause before retry
                        if not self.running:
                            break
                        await asyncio.sleep(1)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the daemon."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    # Tone down very chatty bleak/bluez debug logs unless user explicitly asked for DEBUG globally
    if log_level.upper() != "DEBUG":
        for noisy in [
            "bleak.backends.bluezdbus.manager",
            "bleak.backends.bluezdbus.scanner",
            "bleak.backends.bluezdbus.client",
        ]:
            logging.getLogger(noisy).setLevel(logging.WARNING)


def setup_signal_handlers(daemon: MijiaTemperatureDaemon) -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        daemon.running = False
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Xiaomi Mijia Bluetooth Daemon")
    parser.add_argument(
        "--config", 
        default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create daemon
    daemon = MijiaTemperatureDaemon(args.config)
    
    # Setup signal handlers
    setup_signal_handlers(daemon)
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        daemon.running = False
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        daemon.running = False
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())