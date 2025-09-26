# Attribution and Acknowledgments

## Primary Attribution

This project is derived from the **mitemp_bt2** Home Assistant integration.

**Original Work:**
- Repository: https://github.com/leonxi/mitemp_bt2
- Author: [@leonxi](https://github.com/leonxi)
- License: MIT License (see [LICENSE-ORIGINAL](./LICENSE-ORIGINAL))
- Original Description: Home Assistant custom component for Xiaomi Mijia BLE Temperature Hygrometer

## Key Contributions from Original Work

The following components and concepts are directly derived from or inspired by the original work:

### Core BLE Communication Protocol
- Bluetooth device discovery methods (from `custom_components/mitemp_bt2/common.py`)
- BLE characteristic handles and data parsing (from `custom_components/mitemp_bt2/sensor.py`)
- Device type detection and mode handling (from `custom_components/mitemp_bt2/const.py`)
- Configuration flow implementation (from `custom_components/mitemp_bt2/config_flow.py`)

### Device Support
- **LYWSD03MMC** protocol implementation
- **LYWSDCGQ/01ZM** protocol implementation  
- Battery level calculation algorithm
- Temperature and humidity data parsing
- BLE notification handling for handles 0x0038 and 0x0046

### Configuration Structure
- Device configuration schema
- Polling interval management
- Multi-device support architecture
- Integration manifest structure

## Modifications and Enhancements

### New Components (Original Work)
- **MQTT client integration** - Complete rewrite for standalone operation
- **Docker containerization** - New deployment method
- **Standalone daemon architecture** - Independent of Home Assistant
- **Configuration management system** - Enhanced YAML/environment variable support
- **Web dashboard and monitoring** - New observability features
- **Health check endpoints** - Production monitoring capabilities
- **Prometheus metrics export** - Performance monitoring
- **Async/await modernization** - Updated to modern Python patterns

### Modified Components
- **Bluetooth manager** (adapted from `SingletonBLEScanner`)
- **Device manager** (extended from original device handling)
- **Configuration system** (expanded from original config flow)
- **Logging system** (enhanced for daemon operation)

## Dependencies Attribution

### From Original Project
- **bluepy**: Bluetooth Low Energy library for Linux
- Device protocol specifications and BLE communication patterns
- Error handling and retry logic patterns

### New Dependencies
- **bleak**: Modern async BLE library (replacement for bluepy)
- **paho-mqtt**: MQTT client library
- **PyYAML**: Configuration file parsing
- **aiohttp**: Web server components
- **prometheus_client**: Metrics collection
- **pydantic**: Configuration validation

## License Compliance

This derivative work:
1. ✅ Maintains all original copyright notices
2. ✅ Clearly identifies modifications and additions
3. ✅ Provides proper attribution to original authors
4. ✅ Complies with MIT license terms
5. ✅ Does not claim ownership of original work
6. ✅ Preserves original license file as LICENSE-ORIGINAL

## Contributing

When contributing to this project:
1. **Respect the original work's attribution** - Do not remove or modify attribution
2. **Clearly mark new contributions** - Distinguish new work from original
3. **Maintain license compliance** - Follow MIT license requirements
4. **Update this attribution file** when adding significant original work
5. **Consider contributing back** - Share improvements with original project when applicable

## Changelog from Original

### Removed Components
- Home Assistant integration files (`__init__.py`, `config_flow.py`, `strings.json`)
- HACS configuration (`hacs.json`, `manifest.json`)
- Home Assistant specific dependencies and imports
- Configuration UI components

### Architecture Changes
- **From**: Home Assistant custom component
- **To**: Standalone Linux daemon
- **Runtime**: Independent process vs HA integration
- **Configuration**: YAML/ENV files vs HA config flow
- **Dependencies**: Direct system dependencies vs HA managed

## Contact and Support

For questions about:
- **Original work**: Contact [@leonxi](https://github.com/leonxi) or create issues at [mitemp_bt2](https://github.com/leonxi/mitemp_bt2)
- **This derivative work**: Create issues at [xiaomi-ble-tempmeter-mqtt-daemon](https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon)

## Upstream Contributions

Improvements made in this project that could benefit the original work:
- Enhanced error handling and retry logic
- Better async/await patterns
- Improved device discovery reliability
- Battery calculation optimizations

These will be offered back to the original project via pull requests when applicable.