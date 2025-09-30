#!/usr/bin/env python3
"""
New Hybrid Main Daemon for Xiaomi Mijia Bluetooth Temperature Sensors.

Provides continuous MiBeacon listening with intelligent MQTT publishing
based on configurable thresholds and periodic intervals.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict

# Import new hybrid components
from .continuous_bluetooth_manager import ContinuousBluetoothManager  
from .sensor_cache import SensorCache
from .mqtt_publisher import MQTTPublisher, MQTTConfig
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class HybridMijiaTemperatureDaemon:
    """
    Hybrid daemon with continuous MiBeacon listening and intelligent MQTT publishing.
    
    Architecture:
    - Continuous BLE advertisement scanning
    - Real-time device discovery and data caching
    - Immediate MQTT publishing on threshold breaches  
    - Periodic MQTT publishing with deduplication
    - Friendly name support from static configuration
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the hybrid daemon with configuration."""
        self.config_file = config_file or "config/config.yaml"
        self.running = False
        
        # Initialize components
        self.config_manager = ConfigManager(self.config_file)
        self.bluetooth_manager = None
        self.sensor_cache = None
        self.mqtt_publisher = None
        self.periodic_task = None
        
    async def start(self) -> None:
        """Start the hybrid daemon and all its components."""
        logger.info("Starting Hybrid Xiaomi Mijia Bluetooth Daemon...")
        
        try:
            # Load configuration
            config = self.config_manager.get_config()
            
            # Initialize sensor cache with thresholds and static devices
            cache_config = {
                'temperature_threshold': config.thresholds.temperature,
                'humidity_threshold': config.thresholds.humidity,
                'publish_interval': config.mqtt.publish_interval,
                'static_devices': config.devices.static_devices
            }
            self.sensor_cache = SensorCache(cache_config)
            logger.info("Sensor cache initialized")
            
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
            
            # Initialize continuous Bluetooth manager with data callback
            bluetooth_config = config.bluetooth.model_dump()
            self.bluetooth_manager = ContinuousBluetoothManager(
                bluetooth_config, 
                data_callback=self._on_sensor_data_received
            )
            logger.info("Continuous Bluetooth manager initialized")
            
            # Start continuous BLE scanning
            success = await self.bluetooth_manager.start_continuous_scanning()
            if not success:
                raise RuntimeError("Failed to start continuous BLE scanning")
            
            # Start periodic publishing task
            self.periodic_task = asyncio.create_task(self._periodic_publish_loop())
            logger.info("Periodic publish task started")
            
            self.running = True
            logger.info("Hybrid daemon started successfully - listening for MiBeacon advertisements...")
            
            # Main daemon loop - just wait and handle signals
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start hybrid daemon: {e}")
            raise
            
    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        logger.info("Stopping Hybrid Xiaomi Mijia Bluetooth Daemon...")
        self.running = False
        
        try:
            # Stop periodic task
            if self.periodic_task and not self.periodic_task.done():
                logger.debug("Stopping periodic publish task...")
                self.periodic_task.cancel()
                try:
                    await self.periodic_task
                except asyncio.CancelledError:
                    pass
            
            # Stop continuous scanning
            if self.bluetooth_manager:
                logger.debug("Stopping continuous Bluetooth scanning...")
                await self.bluetooth_manager.cleanup()
                
            # Stop MQTT publisher
            if self.mqtt_publisher:
                logger.debug("Stopping MQTT publisher...")
                await self.mqtt_publisher.stop()
                
            logger.info("Hybrid daemon stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during hybrid daemon shutdown: {e}")
            logger.info("Hybrid daemon stopped with errors")
    
    async def _on_sensor_data_received(self, mac_address: str, parsed_data: dict, rssi: Optional[int]):
        """
        Handle incoming sensor data from continuous BLE scanning.
        
        Args:
            mac_address: Device MAC address
            parsed_data: Parsed MiBeacon data dictionary  
            rssi: RSSI value if available
        """
        try:
            # Update partial sensor data in cache
            immediate, periodic = self.sensor_cache.update_partial_sensor_data(mac_address, parsed_data, rssi)
            
            if immediate:
                # Immediate publish due to threshold breach or first complete reading
                await self._publish_device_immediately(mac_address, "threshold")
            elif parsed_data:
                # Log the partial update for debugging
                fields = list(parsed_data.keys())
                logger.debug(f"Cached partial data for {mac_address}: {fields}")
                    
        except Exception as e:
            logger.error(f"Error processing sensor data from {mac_address}: {e}")
    
    async def _publish_device_immediately(self, mac_address: str, reason: str):
        """
        Publish a device's data immediately.
        
        Args:
            mac_address: Device MAC address
            reason: Reason for immediate publish
        """
        try:
            device = self.sensor_cache.devices.get(mac_address.upper())
            if not device or not device.current_data:
                return
                
            device_id = mac_address.replace(":", "").replace("-", "")
            success = await self.mqtt_publisher.publish_sensor_data_with_name(
                device_id, 
                device.current_data, 
                device.friendly_name, 
                f"immediate-{reason}"
            )
            
            if success:
                self.sensor_cache.mark_device_published(mac_address)
                logger.debug(f"Immediate publish successful for {mac_address}")
            else:
                logger.warning(f"Immediate publish failed for {mac_address}")
                
        except Exception as e:
            logger.error(f"Error in immediate publish for {mac_address}: {e}")
    
    async def _periodic_publish_loop(self):
        """
        Periodic publishing loop for devices that haven't been published recently.
        
        Runs every 60 seconds and checks for devices ready for periodic publishing.
        """
        logger.info("Starting periodic publish loop")
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not self.running:
                    break
                    
                # Get devices ready for periodic publishing
                ready_devices = self.sensor_cache.get_devices_for_periodic_publish()
                
                if ready_devices:
                    logger.info(f"Periodic publish cycle: {len(ready_devices)} devices ready")
                    
                    # Prepare batch data
                    batch_data = []
                    for device in ready_devices:
                        if device.current_data:
                            device_id = device.mac_address.replace(":", "").replace("-", "")
                            batch_data.append((
                                device_id,
                                device.current_data,
                                device.friendly_name,
                                "periodic"
                            ))
                    
                    # Publish batch
                    if batch_data:
                        success_count = await self.mqtt_publisher.publish_multiple_devices(batch_data)
                        
                        # Mark published devices
                        for i, (device_id, _, _, _) in enumerate(batch_data):
                            if i < success_count:  # Assuming successful devices are first N
                                mac_with_colons = ":".join([device_id[i:i+2] for i in range(0, 12, 2)])
                                self.sensor_cache.mark_device_published(mac_with_colons)
                else:
                    logger.debug("Periodic publish cycle: no devices ready")
                    
            except asyncio.CancelledError:
                logger.info("Periodic publish loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic publish loop: {e}")
                # Continue running despite errors
                
        logger.info("Periodic publish loop stopped")
    
    async def _main_loop(self):
        """Simple main loop that waits for shutdown signals."""
        try:
            # Log status every 5 minutes
            status_interval = 300
            last_status = 0
            
            while self.running:
                await asyncio.sleep(1)
                
                # Periodic status logging
                now = asyncio.get_event_loop().time()
                if (now - last_status) >= status_interval:
                    device_count = self.sensor_cache.get_device_count()
                    mqtt_stats = self.mqtt_publisher.get_stats()
                    logger.info(f"Status: {device_count} devices discovered, MQTT connected: {mqtt_stats['connected']}")
                    last_status = now
                    
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the daemon."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Reduce noise from bleak debug logs unless DEBUG is explicitly requested
    if log_level.upper() != "DEBUG":
        for noisy in [
            "bleak.backends.bluezdbus.manager",
            "bleak.backends.bluezdbus.scanner", 
            "bleak.backends.bluezdbus.client",
        ]:
            logging.getLogger(noisy).setLevel(logging.WARNING)


def setup_signal_handlers(daemon: HybridMijiaTemperatureDaemon) -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        daemon.running = False
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main() -> None:
    """Main entry point for hybrid daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid Xiaomi Mijia Bluetooth Daemon")
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
    
    # Create hybrid daemon
    daemon = HybridMijiaTemperatureDaemon(args.config)
    
    # Setup signal handlers
    setup_signal_handlers(daemon)
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        daemon.running = False
    except Exception as e:
        logger.error(f"Hybrid daemon error: {e}")
        daemon.running = False
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())