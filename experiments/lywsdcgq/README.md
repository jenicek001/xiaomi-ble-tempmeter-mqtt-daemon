# LYWSDCGQ Device-Specific Experiments

This directory contains experimental scripts specifically for the LYWSDCGQ/01ZM (Original Mijia BLE Temperature Hygrometer) device model.

## Scripts

- **lywsdcgq_advertisement_scanner.py** - Advertisement packet scanner for LYWSDCGQ
- **lywsdcgq_servicedata_analyzer.py** - Service data analysis tool
- **lywsdcgq_servicedata_parser.py** - Service data parser implementation

## Purpose

The LYWSDCGQ model uses a different advertisement format compared to LYWSD03MMC. These scripts were created to:
- Analyze LYWSDCGQ-specific advertisement packets
- Parse service data format unique to this model
- Understand the differences from LYWSD03MMC
- Develop advertisement-based reading (without GATT connection)

## Device Information

**Model**: LYWSDCGQ/01ZM  
**Name**: Original Mijia BLE Temperature Hygrometer  
**Features**: Temperature, Humidity, Battery  
**Protocol**: MiBeacon via BLE advertisements

## Implementation Notes

The research from these scripts led to the advertisement-based implementation in the main daemon, which allows reading sensor data without establishing GATT connections.

## Note

These are research/development tools preserved for reference when:
- Debugging LYWSDCGQ-specific issues
- Adding support for similar device variants
- Understanding the advertisement-based approach
