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
from .continuous_bluetooth_manager import ContinuousBluetoothManager
from .sensor_cache import SensorCache
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
        self.continuous_bluetooth_manager = None
        self.sensor_cache = None
        self.device_manager = None
        self.mqtt_publisher = None
        
    async def start(self) -> None:
        """Start the daemon and all its components."""
        logger.info("Starting Xiaomi Mijia Bluetooth Daemon...")
        try:
            # Load and validate config
            config = self.config_manager.get_config()

            # Initialize Bluetooth manager for discovery
            bluetooth_config = config.bluetooth.model_dump()
            bluetooth_config['static_devices'] = config.devices.static_devices
            self.bluetooth_manager = BluetoothManager(bluetooth_config)
            logger.info("Bluetooth manager initialized")

            # Initialize sensor cache for data accumulation
            cache_config = bluetooth_config.copy()
            cache_config.update({
                'temperature_threshold': config.thresholds.temperature,
                'humidity_threshold': config.thresholds.humidity,
                'publish_interval': config.mqtt.publish_interval
            })
            self.sensor_cache = SensorCache(cache_config)
            logger.info("Sensor cache initialized")

            # Initialize continuous Bluetooth manager for real-time scanning
            self.continuous_bluetooth_manager = ContinuousBluetoothManager(
                bluetooth_config, 
                data_callback=self._handle_sensor_data
            )
            logger.info("Continuous Bluetooth manager initialized")

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
            if self.continuous_bluetooth_manager:
                logger.debug("Stopping continuous Bluetooth manager...")
                await self.continuous_bluetooth_manager.cleanup()
                
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
        """Main daemon execution loop with continuous MiBeacon scanning."""
        # Initial device discovery to populate the cache
        logger.info("Performing initial device discovery...")
        discovered_devices = await self.bluetooth_manager.discover_devices()
        if discovered_devices:
            logger.info(f"Found {len(discovered_devices)} Xiaomi devices during initial scan")
            # Register discovered devices in the sensor cache
            for device_info in discovered_devices:
                self.sensor_cache.discover_device(device_info['mac'])
        else:
            logger.warning("No Xiaomi devices found during initial scan")

        # Start continuous MiBeacon advertisement scanning
        logger.info("Starting continuous MiBeacon advertisement scanning...")
        scanning_started = await self.continuous_bluetooth_manager.start_continuous_scanning()
        
        if not scanning_started:
            logger.error("Failed to start continuous scanning - daemon cannot proceed")
            return
            
        logger.info("Continuous MiBeacon scanning active - daemon ready")
        
        # Run continuous scanning until shutdown
        try:
            while self.running:
                # The real work happens in advertisement callbacks
                # We just need to keep the daemon alive and handle periodic cleanup
                # Sleep in smaller chunks for faster shutdown response
                await asyncio.sleep(10)  # Check every 10 seconds for shutdown signal
                
                # Optional: Log cache status periodically (every 6 iterations = 60s)
                if self.sensor_cache and (asyncio.get_event_loop().time() % 60 < 10):
                    device_count = self.sensor_cache.get_device_count()
                    logger.debug(f"Sensor cache tracking {device_count} devices")
                    
        except asyncio.CancelledError:
            logger.info("Main loop cancelled - shutting down")
            raise  # Re-raise to propagate cancellation
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            logger.info("Stopping continuous scanning...")
            if self.continuous_bluetooth_manager:
                await self.continuous_bluetooth_manager.stop_continuous_scanning()
    
    async def _handle_sensor_data(self, mac_address: str, parsed_data: dict, rssi: Optional[int]):
        """
        Handle new sensor data from continuous MiBeacon scanning.
        
        This callback is invoked by ContinuousBluetoothManager when MiBeacon
        advertisements are received. It updates the sensor cache and triggers
        MQTT publishing when appropriate.
        """
        try:
            logger.debug(f"Processing sensor data from {mac_address}: {parsed_data}")
            
            # Update sensor cache with partial data
            should_publish_immediate, should_publish_periodic = self.sensor_cache.update_partial_sensor_data(
                mac_address, parsed_data, rssi
            )
            
            # Get device record for publishing
            device = self.sensor_cache.devices.get(mac_address.upper())
            
            if should_publish_immediate or should_publish_periodic:
                if device and device.current_data:
                    # Publish complete sensor data to MQTT
                    logger.info(f"Publishing sensor data for {mac_address} "
                              f"({'immediate' if should_publish_immediate else 'periodic'})")
                    
                    if self.mqtt_publisher:
                        # Convert MAC address to device_id format (remove colons)
                        device_id = mac_address.replace(':', '').upper()
                        await self.mqtt_publisher.publish_sensor_data(device_id, device.current_data)
                        
                        # Mark as published in cache
                        self.sensor_cache.mark_device_published(mac_address)
                        
                        logger.debug(f"Successfully published data for {mac_address}")
                    else:
                        logger.warning("MQTT publisher not available")
                else:
                    logger.warning(f"No complete sensor data available for {mac_address}")
            else:
                # Partial data cached, waiting for more MiBeacon packets
                logger.debug(f"Cached partial data for {mac_address}, waiting for complete reading")
                
        except Exception as e:
            logger.error(f"Error handling sensor data for {mac_address}: {e}")


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
    
    # Setup asyncio-compatible signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal (Ctrl-C), initiating graceful shutdown...")
        daemon.running = False
        # Cancel all running tasks to break out of sleep/wait operations
        for task in asyncio.all_tasks(loop):
            task.cancel()
    
    # Register signal handlers using asyncio
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    
    try:
        await daemon.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown initiated")
        daemon.running = False
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        daemon.running = False
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())