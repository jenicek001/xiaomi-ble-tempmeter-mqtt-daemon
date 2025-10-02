# Docker Compose: MQTT Broker Service Removal

## Summary
Removed the optional Mosquitto MQTT broker service from docker-compose.yml as it's unnecessary for the typical use case of this daemon on smart home systems (Raspberry Pi with Home Assistant, OpenHAB, etc.), which already have their own MQTT brokers running.

## Rationale

This daemon is intended for:
- 🏠 Smart home systems (Home Assistant, OpenHAB)
- 🥧 Raspberry Pi deployments
- 🔌 Existing MQTT infrastructure

Users in these environments **already have** an MQTT broker running, so including an optional Mosquitto service was:
- ❌ Redundant
- ❌ Confusing (two MQTT brokers?)
- ❌ Resource-wasteful on low-power devices
- ❌ Adds unnecessary complexity

## Changes Made

### 1. docker-compose.yml
**Removed:**
- `mosquitto` service with profiles
- Named volumes for Mosquitto data

**Result:** Clean, single-service compose file focused on the daemon only.

### 2. .env.example
**Updated:**
```bash
# Before
MIJIA_MQTT_BROKER_HOST=localhost

# After
MIJIA_MQTT_BROKER_HOST=192.168.1.100     # Change to your MQTT broker IP/hostname
```

**Added:**
- Clear comments that MQTT broker settings are REQUIRED
- Example IP address instead of localhost
- Emphasis that users need to configure their existing broker

### 3. docs/DOCKER.md
**Removed:**
- References to `--profile mqtt` flag
- Instructions for starting optional MQTT broker
- Mosquitto-related troubleshooting

**Added:**
- Prerequisites section emphasizing existing MQTT broker requirement
- Instructions for testing MQTT broker connectivity
- Clearer setup flow

### 4. Makefile
**Removed:**
- `docker-run-with-mqtt` target

**Updated:**
- `docker-run` now includes warning to ensure MQTT broker is running
- Help text cleaned up

### 5. README.md
**Updated:**
- Quick Start section now emphasizes MQTT broker prerequisite
- Added clear "Prerequisites" subsection
- Instructions to configure both `.env` AND `config.yaml`

### 6. DOCKER_IMPROVEMENTS.md
**Updated:**
- Removed references to Compose profiles for optional services
- Clarified that single compose file is focused on daemon only

## Migration Guide

### For New Users:
No change - you already need an MQTT broker, and now it's clearer!

### For Existing Users:
If you were using the optional Mosquitto service:

1. **You probably weren't!** Most users have their own broker.
2. If you were, simply run Mosquitto separately:
   ```bash
   docker run -d -p 1883:1883 eclipse-mosquitto:2
   ```

## Expected User Setup

Typical smart home user has:
```
[Raspberry Pi]
├── Home Assistant (with built-in MQTT broker)
│   OR
├── Mosquitto MQTT Broker (standalone)
└── This Daemon (docker-compose up -d)
    └── Connects to existing MQTT broker via .env config
```

## Configuration Required

Users must configure in `.env`:
```bash
MIJIA_MQTT_BROKER_HOST=192.168.1.100    # Their broker's IP
MIJIA_MQTT_BROKER_PORT=1883             # Standard MQTT port
MIJIA_MQTT_USERNAME=their_username      # Their credentials
MIJIA_MQTT_PASSWORD=their_password      # Their credentials
```

## Benefits

✅ **Simpler:** One service, one purpose
✅ **Clearer:** No confusion about which MQTT broker to use
✅ **Realistic:** Matches actual deployment scenarios
✅ **Efficient:** No duplicate MQTT broker on resource-constrained devices
✅ **Best Practice:** Services should be single-purpose

## Testing

Users can verify their MQTT broker connection before starting the daemon:

```bash
# Test MQTT connectivity
mosquitto_pub -h 192.168.1.100 -p 1883 -u username -P password -t test -m "hello"

# If successful, daemon will work
docker compose up -d
```

---

**Conclusion:** This change aligns the Docker deployment with real-world smart home usage patterns where MQTT infrastructure already exists.
