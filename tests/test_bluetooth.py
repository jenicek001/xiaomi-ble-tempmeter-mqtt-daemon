"""
Tests for Bluetooth Manager.

Tests the BluetoothManager class with mocked bleak components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.bluetooth_manager import BluetoothManager, SensorData, SUPPORTED_DEVICES
from src.constants import DEFAULT_CONFIG


class TestBluetoothManager:
    """Test cases for BluetoothManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bt_manager = BluetoothManager(DEFAULT_CONFIG["bluetooth"])
        
    @pytest.mark.asyncio
    async def test_device_discovery(self):
        """Test BLE device discovery."""
        # Mock BLE device
        mock_device = Mock()
        mock_device.name = "LYWSD03MMC"
        mock_device.address = "A4:C1:38:AA:AA:AA"
        mock_device.rssi = -45
        
        with patch('src.bluetooth_manager.BleakScanner.discover') as mock_discover:
            mock_discover.return_value = [mock_device]
            
            devices = await self.bt_manager.discover_devices()
            
            assert len(devices) == 1
            assert devices[0]["mac"] == "A4:C1:38:AA:AA:AA"
            assert devices[0]["name"] == "LYWSD03MMC"
            assert devices[0]["mode"] == "LYWSD03MMC"
        
    @pytest.mark.asyncio  
    async def test_device_connection_success(self):
        """Test successful device connection and data reading."""
        # Mock notification data (5 bytes: temp, humidity, voltage)
        test_data = bytearray([0x5C, 0x09, 0x3C, 0x0B, 0x0C])  # 23.8°C, 60%, 3.083V
        
        with patch('src.bluetooth_manager.BleakClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_connected = True
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Simulate notification callback
            async def mock_start_notify(handle, callback):
                callback(handle, test_data)
                
            mock_client.start_notify = mock_start_notify
            mock_client.stop_notify = AsyncMock()
            mock_client.write_gatt_char = AsyncMock()
            
            result = await self.bt_manager.read_device_data("A4:C1:38:AA:AA:AA", "LYWSD03MMC")
            
            assert result is not None
            assert result.temperature == 23.8
            assert result.humidity == 60
            assert result.voltage == 3.083
        
    @pytest.mark.asyncio
    async def test_data_parsing(self):
        """Test parsing sensor data from notifications."""
        # Test data: temp=23.8°C (0x095C), humidity=60% (0x3C), voltage=3.083V (0x0C0B)
        test_data = bytearray([0x5C, 0x09, 0x3C, 0x0B, 0x0C])
        
        result = self.bt_manager._parse_notification_data(test_data)
        
        assert result.temperature == 23.8
        assert result.humidity == 60
        assert result.voltage == 3.083
        assert result.battery == 98  # (3.083 - 2.1) * 100 = 98%
        assert isinstance(result.timestamp, datetime)
        
    def test_data_parsing_invalid_length(self):
        """Test parsing with invalid data length."""
        test_data = bytearray([0x5C, 0x09, 0x3C])  # Only 3 bytes
        
        with pytest.raises(ValueError, match="Invalid data length"):
            self.bt_manager._parse_notification_data(test_data)
            
    def test_battery_calculation(self):
        """Test battery percentage calculation."""
        # Test various voltage levels
        test_cases = [
            (bytearray([0x00, 0x00, 0x00, 0x34, 0x08]), 2.1, 0),    # 2.1V = 0%
            (bytearray([0x00, 0x00, 0x00, 0x1E, 0x0C]), 3.1, 100),  # 3.1V = 100%
            (bytearray([0x00, 0x00, 0x00, 0xA9, 0x0A]), 2.6, 50),   # 2.6V = 50%
        ]
        
        for data, expected_voltage, expected_battery in test_cases:
            result = self.bt_manager._parse_notification_data(data)
            assert result.voltage == expected_voltage
            assert result.battery == expected_battery
            
    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout handling."""
        with patch('src.bluetooth_manager.BleakClient') as mock_client_class:
            mock_client_class.side_effect = asyncio.TimeoutError("Connection timeout")
            
            result = await self.bt_manager.read_device_data("A4:C1:38:AA:AA:AA", "LYWSD03MMC")
            
            assert result is None
            
    @pytest.mark.asyncio
    async def test_test_device_connection(self):
        """Test device connectivity check."""
        with patch('src.bluetooth_manager.BleakClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_connected = True
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await self.bt_manager.test_device_connection("A4:C1:38:AA:AA:AA")
            
            assert result is True
            
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test resource cleanup."""
        # Add some discovered devices
        self.bt_manager._discovered_devices.add("A4:C1:38:AA:AA:AA")
        
        await self.bt_manager.cleanup()
        
        assert len(self.bt_manager._discovered_devices) == 0