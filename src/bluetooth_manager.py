#!/usr/bin/env python3
"""Bluetooth Manager - GATT connection-based implementation.

Provides:
 - Device discovery (BleakScanner)
 - Per-device GATT read with notification parsing (ASCII or binary)
 - RSSI capture (from advertisements or pre-connect refresh)
 - Battery estimation with simple chemistry mapping
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)


@dataclass
class SensorData:
    temperature: float
    humidity: float
    battery: int  # -1 if unknown
    voltage: float  # 0 if unknown
    timestamp: datetime
    rssi: Optional[int] = None

    def to_dict(self):
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "voltage": self.voltage,
            "timestamp": self.timestamp.isoformat(),
            "rssi": self.rssi
        }


def estimate_battery_percent(voltage: float, chemistry: str = "CR2032") -> int:
    """Estimate battery percentage from voltage.

    Supports rough mapping for CR2032 coin cells and AAA NiMH.
    Returns 0-100.
    """
    if voltage <= 0:
        return -1
    chemistry = chemistry.upper()
    tables: Dict[str, Tuple[Tuple[float, int], ...]] = {
        # (voltage, percent) sorted descending
        "CR2032": (
            (3.00, 100), (2.95, 95), (2.90, 90), (2.85, 85), (2.80, 75), (2.75, 65),
            (2.70, 55), (2.65, 45), (2.60, 35), (2.55, 25), (2.50, 15), (2.45, 10),
            (2.40, 7), (2.35, 5), (2.30, 3), (2.25, 2), (2.20, 1), (2.10, 0)
        ),
        "AAA_NIMH": (
            (1.35, 100), (1.32, 95), (1.30, 90), (1.28, 85), (1.26, 80), (1.24, 75),
            (1.22, 70), (1.20, 60), (1.18, 50), (1.16, 45), (1.14, 40), (1.12, 30),
            (1.10, 25), (1.08, 20), (1.06, 15), (1.04, 10), (1.02, 5), (1.00, 3), (0.98, 1), (0.95, 0)
        )
    }
    table = tables.get(chemistry, tables["CR2032"])
    for v, p in table:
        if voltage >= v:
            return p
    return 0


class BluetoothManager:
    def __init__(self, config: dict):
        self.config = config
        self.retry_attempts = config.get('retry_attempts', 3)
        self.connection_timeout = config.get('connection_timeout', 10)
        self.battery_chemistry = config.get('battery_chemistry', 'CR2032')
        self._last_discovery_rssi: Dict[str, int] = {}
        logger.debug(f"Initializing BluetoothManager with config: {config}")

    async def read_sensor_data(self, mac_address: str, scan_timeout: int = 10) -> Optional[SensorData]:
        logger.info(f"Reading sensor data from {mac_address}")

        # Try a short pre-connect lookup for fresh RSSI
        try:
            fresh = await BleakScanner.find_device_by_address(mac_address, timeout=3.0)
            if fresh and getattr(fresh, 'rssi', None) is not None:
                self._last_discovery_rssi[mac_address] = fresh.rssi
                logger.debug(f"Pre-connect RSSI for {mac_address}: {fresh.rssi}")
        except Exception as e:
            logger.debug(f"RSSI pre-scan failed for {mac_address}: {e}")

        for attempt in range(self.retry_attempts):
            try:
                if attempt > 0:
                    logger.info(f"Connection attempt {attempt + 1} for device {mac_address}")
                    await asyncio.sleep(5)

                async with BleakClient(mac_address, timeout=scan_timeout) as client:
                    logger.debug(f"Connected to {mac_address}")

                    notify_char = None
                    for service in client.services:
                        if service.uuid.lower() == "226c0000-6476-4566-7562-66734470666d":
                            for char in service.characteristics:
                                if char.uuid.lower() == "226caa55-6476-4566-7562-66734470666d":
                                    notify_char = char
                                    break
                            if notify_char:
                                break
                    if not notify_char:
                        raise RuntimeError("Temperature/Humidity notification characteristic not found")

                    logger.debug(f"Notification characteristic: {notify_char.uuid} handle {notify_char.handle}")
                    await client.write_gatt_char(notify_char, b"\x01\x00")
                    logger.debug("Notifications enabled")

                    received_data: Optional[SensorData] = None
                    ascii_parsed: Optional[Tuple[float, float]] = None

                    def notification_handler(_, data: bytearray):
                        nonlocal received_data, ascii_parsed
                        logger.debug(f"Notification ({len(data)} bytes): {data.hex()}")
                        try:
                            # Attempt ASCII parse first
                            try:
                                text = data.decode('ascii', errors='strict').rstrip('\x00')
                                import re
                                t_m = re.search(r'T=(-?\d+\.?\d*)', text)
                                h_m = re.search(r'H=(-?\d+\.?\d*)', text)
                                if t_m and h_m:
                                    ascii_parsed = (round(float(t_m.group(1)), 1), round(float(h_m.group(1)), 1))
                                    logger.debug(f"Parsed ASCII partial: T={ascii_parsed[0]} H={ascii_parsed[1]}")
                                    return  # Wait for binary for voltage/battery if it comes
                            except Exception:
                                pass

                            # Binary format (5 bytes expected)
                            if len(data) >= 5:
                                temp_raw = int.from_bytes(data[0:2], 'little', signed=True)
                                temperature = round(temp_raw / 100.0, 1)
                                humidity = round(data[2], 1)
                                voltage_raw = int.from_bytes(data[3:5], 'little')
                                voltage = voltage_raw / 1000.0
                                battery = estimate_battery_percent(voltage, self.battery_chemistry)
                                received_data = SensorData(
                                    temperature=temperature,
                                    humidity=humidity,
                                    battery=battery,
                                    voltage=voltage,
                                    timestamp=datetime.now(),
                                    rssi=self._last_discovery_rssi.get(mac_address)
                                )
                                logger.debug(f"Parsed binary frame: T={temperature} H={humidity} V={voltage:.3f} B={battery}%")
                            else:
                                logger.warning(f"Unexpected notification length {len(data)} from {mac_address}")
                        except Exception as parse_err:
                            logger.error(f"Parse error for {mac_address}: {parse_err}")

                    await client.start_notify(notify_char, notification_handler)
                    logger.debug(f"Waiting (up to {scan_timeout}s) for notification from {mac_address}")

                    start_t = asyncio.get_event_loop().time()
                    while received_data is None and (asyncio.get_event_loop().time() - start_t) < scan_timeout:
                        await asyncio.sleep(0.1)

                    await client.stop_notify(notify_char)

                    # Fallback to ASCII-only partial if we got that but no binary
                    if received_data is None and ascii_parsed is not None:
                        t, h = ascii_parsed
                        received_data = SensorData(
                            temperature=t,
                            humidity=h,
                            battery=-1,
                            voltage=0.0,
                            timestamp=datetime.now(),
                            rssi=self._last_discovery_rssi.get(mac_address)
                        )
                        logger.debug("Using ASCII-only partial data (no binary frame)")

                    if received_data:
                        logger.info(
                            f"Result {mac_address}: T={received_data.temperature}°C H={received_data.humidity}% "
                            f"V={received_data.voltage:.3f}V B={received_data.battery}% RSSI={received_data.rssi}"
                        )
                        return received_data
                    else:
                        logger.warning(f"No data received from {mac_address} (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed for {mac_address}: {e}")
                if attempt == self.retry_attempts - 1:
                    logger.error(f"All {self.retry_attempts} attempts failed for {mac_address}")

        return None

    async def discover_devices(self) -> list:
        logger.info("Discovering Xiaomi temperature sensors...")
        discovered = []
        try:
            devices = await BleakScanner.discover(timeout=10.0)
            for d in devices:
                if d.name and d.name in ["MJ_HT_V1", "LYWSD03MMC", "LYWSDCGQ/01ZM"]:
                    info = {
                        "mac": d.address,
                        "name": d.name,
                        "mode": "LYWSDCGQ",
                        "rssi": getattr(d, 'rssi', None)
                    }
                    discovered.append(info)
                    if info["rssi"] is not None:
                        self._last_discovery_rssi[info["mac"]] = info["rssi"]
                    logger.info(f"Found Xiaomi device: {info}")
        except Exception as e:
            logger.error(f"Discovery scan failed: {e}")

        # Merge static devices
        for static_dev in self.config.get('static_devices', []):
            if not static_dev.get('enabled', True):
                continue
            if any(d['mac'] == static_dev['mac'] for d in discovered):
                continue
            info = {
                "mac": static_dev['mac'],
                "name": static_dev.get('name', 'Unknown'),
                "mode": static_dev.get('mode', 'LYWSDCGQ'),
                "rssi": self._last_discovery_rssi.get(static_dev['mac'])
            }
            discovered.append(info)
            logger.info(f"Added static device: {info}")

        logger.info(f"Discovery complete. Found {len(discovered)} devices")
        return discovered

    async def cleanup(self):
        logger.info("Bluetooth cleanup completed")


def read_device_data(self, mac_address: str, device_mode: str = "LYWSDCGQ/01ZM", scan_timeout: int = 30):
    return self.read_sensor_data(mac_address, scan_timeout)

BluetoothManager.read_device_data = read_device_data