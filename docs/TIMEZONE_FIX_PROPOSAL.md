# Timezone Issue Analysis and Fix Proposal

## Problem Statement

**Current Behavior**:
- Host system timezone: `CEST (UTC+2)`
- Container timezone: `UTC (+00:00)`
- MQTT messages show timestamps in UTC instead of local timezone
- Example: `"last_seen": "2025-10-02T07:42:49.319805+00:00"` instead of `"2025-10-02T09:42:49.319805+02:00"`

**Root Cause**:
The Python code uses `datetime.now(tz=timezone.utc).astimezone()` which converts to the system's local timezone. However, inside the Docker container, the system timezone is UTC, so the conversion does nothing.

## Code Analysis

### Current Implementation

**In `src/sensor_cache.py` and `src/bluetooth_manager.py`**:
```python
from datetime import datetime, timezone

# This gets UTC then converts to "local" timezone
# But inside container, local IS UTC!
current_time = datetime.now(tz=timezone.utc).astimezone()
```

**Key locations**:
1. `src/sensor_cache.py:27` - `first_seen` field initialization
2. `src/sensor_cache.py:69` - `update_partial_data()` 
3. `src/sensor_cache.py:167` - time since publish calculation
4. `src/sensor_cache.py:193` - last publish time
5. `src/sensor_cache.py:331` - periodic check
6. `src/bluetooth_manager.py:174` - device discovery timestamp

## Proposed Solutions

### ✅ Solution 1: Mount Host Timezone (RECOMMENDED)

**Pros**:
- Simple and standard Docker practice
- No code changes needed
- Respects host system timezone
- Automatic DST handling
- Works for any timezone

**Cons**:
- Requires Docker configuration change

**Implementation**:

#### A. Update `docker-compose.yml`:
```yaml
services:
  mijia-daemon:
    volumes:
      # Existing volumes...
      - ./config/config.yaml:/config/config.yaml:ro
      - /var/run/dbus:/var/run/dbus:ro
      - ./logs:/app/logs
      
      # ADD: Mount timezone info (read-only)
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
```

#### B. Optional: Add TZ environment variable in `docker-compose.yml`:
```yaml
    environment:
      - MIJIA_LOG_LEVEL=${MIJIA_LOG_LEVEL:-INFO}
      - MIJIA_BLUETOOTH_ADAPTER=${MIJIA_BLUETOOTH_ADAPTER:-0}
      # ADD: Timezone (backup method)
      - TZ=${TZ:-Europe/Prague}
```

#### C. Update `.env.example`:
```bash
# Add timezone configuration
TZ=Europe/Prague  # or Europe/Berlin, etc.
```

---

### Solution 2: Timezone in Configuration File

**Pros**:
- Explicit configuration
- Can differ from host if needed
- Portable across systems

**Cons**:
- Requires code changes
- Need to handle timezone parsing
- More complex

**Implementation**:

#### A. Add to `config/config.yaml.example`:
```yaml
system:
  timezone: "Europe/Prague"  # IANA timezone name
```

#### B. Code changes needed in `src/config_manager.py`:
```python
from pydantic import BaseModel
import pytz

class SystemConfig(BaseModel):
    timezone: str = "UTC"
    
    @validator('timezone')
    def validate_timezone(cls, v):
        """Validate timezone string."""
        try:
            pytz.timezone(v)
            return v
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {v}")

class Config(BaseModel):
    system: SystemConfig = SystemConfig()
    # ... other configs
```

#### C. Update datetime creation throughout codebase:
```python
import pytz
from config_manager import config

# Get configured timezone
local_tz = pytz.timezone(config.system.timezone)

# Use instead of .astimezone()
current_time = datetime.now(tz=timezone.utc).astimezone(local_tz)
```

---

### Solution 3: Timezone in Dockerfile

**Pros**:
- Baked into image
- No runtime configuration needed

**Cons**:
- Not flexible (requires rebuild for different timezones)
- Not suitable for multi-timezone deployments
- Poor practice (hardcoding location in image)

**Implementation** (NOT RECOMMENDED):

```dockerfile
# In Dockerfile, add before runtime stage
ENV TZ=Europe/Prague
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

---

## Recommended Approach

**Use Solution 1 (Mount Host Timezone)** because:

1. ✅ **Zero code changes** - existing Python code already handles timezones correctly
2. ✅ **Standard Docker practice** - this is the recommended way
3. ✅ **Respects host system** - container matches where it's deployed
4. ✅ **DST automatic** - follows host system's DST rules
5. ✅ **Simple to implement** - just 2-3 lines in docker-compose.yml
6. ✅ **Works immediately** - no need to rebuild image

## Implementation Steps

### Step 1: Update docker-compose.yml

```yaml
volumes:
  - ./config/config.yaml:/config/config.yaml:ro
  - /var/run/dbus:/var/run/dbus:ro
  - ./logs:/app/logs
  # Mount timezone files from host
  - /etc/localtime:/etc/localtime:ro
  - /etc/timezone:/etc/timezone:ro

environment:
  - MIJIA_LOG_LEVEL=${MIJIA_LOG_LEVEL:-INFO}
  - MIJIA_BLUETOOTH_ADAPTER=${MIJIA_BLUETOOTH_ADAPTER:-0}
  # Set TZ environment variable as fallback
  - TZ=${TZ:-Europe/Prague}
```

### Step 2: Update .env.example

```bash
# Timezone configuration (optional, defaults to Europe/Prague)
# Use IANA timezone names: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TZ=Europe/Prague
```

### Step 3: Add to .env (if exists)

```bash
TZ=Europe/Prague
```

### Step 4: Restart daemon

```bash
make docker-stop
make docker-run
```

### Step 5: Verify

Check logs for timestamps with correct timezone:
```bash
make docker-logs
# Should see: "last_seen": "2025-10-02T09:42:49.319805+02:00" (not +00:00)
```

Check inside container:
```bash
docker exec mijia-daemon date
# Should show: Thu  2 Oct 09:53:31 CEST 2025 (not UTC)
```

## Testing

After implementing the fix, verify with:

```bash
# 1. Check container date
docker exec mijia-daemon date

# 2. Check Python timezone inside container
docker exec mijia-daemon python -c "from datetime import datetime, timezone; print(datetime.now(tz=timezone.utc).astimezone())"

# 3. Check MQTT message timestamps
# Look in MQTT broker or logs for "last_seen" field
```

Expected output:
- Container date should match host timezone
- Python datetime should show +02:00 (or your local offset)
- MQTT messages should have correct timezone offset

## Additional Notes

### Alternative: TZ Environment Variable Only

If mounting `/etc/localtime` causes issues, the `TZ` environment variable alone should work:

```yaml
environment:
  - TZ=Europe/Prague
```

This is less "clean" but equally effective for Python applications.

### Timezone Names

Use IANA timezone database names:
- `Europe/Prague` (Czech Republic)
- `Europe/Berlin` (Germany)  
- `Europe/Vienna` (Austria)
- `UTC` (if you want UTC)

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### Docker Compose Host Network Mode

Since you're using `network_mode: host`, timezone handling is even more important as the container should match the host system's expectations.

## Files to Update

1. ✅ `docker-compose.yml` - Add volume mounts and TZ variable
2. ✅ `.env.example` - Document TZ variable  
3. ✅ `.env` - Set your TZ value (if file exists)
4. ✅ `README.md` - Add timezone configuration documentation (optional)

## No Code Changes Required

The existing Python code is **already correct**:
```python
datetime.now(tz=timezone.utc).astimezone()
```

This properly converts UTC to local timezone. The only issue is that "local" inside the container is UTC. Once we fix the container's timezone, this code will work perfectly.

---

**Ready to implement?** This fix is non-breaking and will immediately make all MQTT message timestamps use your local timezone.
