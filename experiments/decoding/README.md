# Decoding Scripts

This directory contains experimental scripts for analyzing and decoding the Xiaomi MiBeacon protocol.

## Scripts

- **analyze_xiaomi_format.py** - Analysis of Xiaomi data format structure
- **capture_humidity_pattern.py** - Capture and analyze humidity data patterns
- **decode_manual.py** - Manual decoding experiments
- **decode_xiaomi.py** - Xiaomi protocol decoder
- **decode_xiaomi_messages.py** - MiBeacon message decoding

## Usage

These scripts were used to:
- Reverse-engineer the Xiaomi MiBeacon protocol
- Understand temperature and humidity encoding
- Decode battery level information
- Analyze advertisement packet structures
- Validate data parsing logic

## Note

These are research/development tools and are not part of the production daemon. They document the protocol understanding process and can be useful for:
- Adding support for new Xiaomi devices
- Debugging protocol changes
- Understanding the raw data format
