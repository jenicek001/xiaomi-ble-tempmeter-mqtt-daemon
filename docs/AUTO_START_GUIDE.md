# Auto-Start Guide: Making the Daemon Start Automatically

This guide explains how to ensure the Xiaomi BLE daemon starts automatically after system reboot or crashes.

## Method 1: Docker Compose with Auto-Restart (✅ Already Configured)

Your `docker-compose.yml` already includes `restart: unless-stopped`, which provides automatic restart functionality.

### How It Works

```yaml
services:
  mijia-daemon:
    restart: unless-stopped  # ← This is the key setting
```

**Restart Policies Explained:**

| Policy | Behavior |
|--------|----------|
| `no` | Never restart (default) |
| `always` | Always restart, even after manual stop |
| `unless-stopped` | ✅ **Recommended** - Restart unless explicitly stopped |
| `on-failure` | Restart only on error exit codes |

### What `unless-stopped` Does

✅ **Restarts automatically when:**
- System reboots
- Daemon crashes
- Container stops unexpectedly
- Docker daemon restarts

❌ **Does NOT restart when:**
- You manually stop it with `docker compose stop`
- You manually stop it with `docker stop mijia-daemon`

### Enabling Docker to Start on Boot

For the daemon to start after reboot, Docker itself must start on boot:

```bash
# Enable Docker service to start on boot
sudo systemctl enable docker

# Check if it's enabled
sudo systemctl is-enabled docker
# Should output: enabled

# Verify Docker status
sudo systemctl status docker
```

### Testing Auto-Restart

**Test 1: After System Reboot**
```bash
# Reboot the system
sudo reboot

# After reboot, check if daemon is running
docker ps | grep mijia-daemon

# Check logs to see startup time
docker compose logs --tail=50 mijia-daemon
```

**Test 2: After Crash**
```bash
# Simulate a crash by killing the process
docker exec mijia-daemon pkill -9 python

# Wait a few seconds, then check if it restarted
docker compose ps

# Check restart count
docker inspect mijia-daemon --format='{{.RestartCount}}'
```

**Test 3: After Docker Service Restart**
```bash
# Restart Docker service
sudo systemctl restart docker

# Check if daemon came back up
docker compose ps
```

### Current Setup Verification

```bash
# Check current restart policy
docker inspect mijia-daemon --format='{{.HostConfig.RestartPolicy.Name}}'
# Should output: unless-stopped

# View restart count
docker inspect mijia-daemon --format='{{.RestartCount}}'

# Check container uptime
docker ps --filter name=mijia-daemon --format "table {{.Names}}\t{{.Status}}"
```

## Method 2: Systemd Service (Alternative for Manual Installation)

If you're running the daemon without Docker, create a systemd service.

### Create Service File

```bash
sudo nano /etc/systemd/system/mijia-daemon.service
```

```ini
[Unit]
Description=Xiaomi Mijia BLE Temperature Sensor MQTT Daemon
After=network.target bluetooth.service mosquitto.service
Wants=bluetooth.service

[Service]
Type=simple
User=pi
Group=bluetooth
WorkingDirectory=/home/pi/xiaomi-ble-tempmeter-mqtt-daemon
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Using uvx for isolated environment
ExecStart=/usr/local/bin/uvx --from . python -m src.main --log-level INFO

# Restart configuration
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Process management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mijia-daemon

# Security hardening (optional)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Enable and Start Systemd Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable mijia-daemon

# Start the service now
sudo systemctl start mijia-daemon

# Check status
sudo systemctl status mijia-daemon

# View logs
sudo journalctl -u mijia-daemon -f
```

### Systemd Service Management

```bash
# Start service
sudo systemctl start mijia-daemon

# Stop service
sudo systemctl stop mijia-daemon

# Restart service
sudo systemctl restart mijia-daemon

# Check if enabled for auto-start
sudo systemctl is-enabled mijia-daemon

# Disable auto-start
sudo systemctl disable mijia-daemon

# View recent logs
sudo journalctl -u mijia-daemon -n 100 --no-pager

# Follow logs in real-time
sudo journalctl -u mijia-daemon -f
```

## Method 3: Docker Compose Systemd Integration (Advanced)

For more control, you can create a systemd service that manages Docker Compose.

### Create Docker Compose Systemd Service

```bash
sudo nano /etc/systemd/system/mijia-docker.service
```

```ini
[Unit]
Description=Xiaomi Mijia BLE Daemon (Docker Compose)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/xiaomi-ble-tempmeter-mqtt-daemon
User=pi
Group=docker

# Start command
ExecStart=/usr/bin/docker compose up -d

# Stop command
ExecStop=/usr/bin/docker compose down

# Reload command (restart containers)
ExecReload=/usr/bin/docker compose restart

# Don't restart this service, let Docker handle container restarts
Restart=no

# Timeout values
TimeoutStartSec=300
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
```

### Enable Docker Compose Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable mijia-docker

# Start now
sudo systemctl start mijia-docker

# Check status
sudo systemctl status mijia-docker

# Test restart
sudo systemctl restart mijia-docker
```

**Benefits of this approach:**
- Single command to manage all containers
- Integrates with system startup/shutdown
- Can add dependencies on other services
- Provides systemd logging

## Method 4: Cron Job (Last Resort)

If other methods fail, use cron to check and restart the daemon.

### Create Check Script

```bash
nano ~/check-mijia-daemon.sh
```

```bash
#!/bin/bash
# Check if mijia-daemon container is running, start if not

CONTAINER_NAME="mijia-daemon"
COMPOSE_DIR="/home/pi/xiaomi-ble-tempmeter-mqtt-daemon"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "$(date): $CONTAINER_NAME not running, starting..." >> /var/log/mijia-check.log
    cd "$COMPOSE_DIR" || exit 1
    docker compose up -d
else
    echo "$(date): $CONTAINER_NAME is running" >> /var/log/mijia-check.log
fi
```

### Make Executable and Add to Cron

```bash
# Make executable
chmod +x ~/check-mijia-daemon.sh

# Edit crontab
crontab -e

# Add this line to check every 5 minutes
*/5 * * * * /home/pi/check-mijia-daemon.sh

# Add this line to start on reboot
@reboot sleep 60 && cd /home/pi/xiaomi-ble-tempmeter-mqtt-daemon && docker compose up -d
```

## Recommended Setup for Your System

Based on your Docker Compose setup, here's the **recommended configuration**:

### 1. Ensure Docker Starts on Boot
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Verify Restart Policy (Already Set)
Your `docker-compose.yml` already has `restart: unless-stopped` ✅

### 3. Start the Daemon
```bash
cd /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon
docker compose up -d
```

### 4. Test Auto-Restart
```bash
# Test crash recovery
docker exec mijia-daemon pkill -9 python
sleep 10
docker compose ps  # Should show running

# Test reboot (optional)
sudo reboot
# After reboot, check: docker compose ps
```

## Monitoring and Verification

### Check if Everything is Working

```bash
# 1. Check Docker is enabled for boot
sudo systemctl is-enabled docker

# 2. Check daemon restart policy
docker inspect mijia-daemon --format='{{.HostConfig.RestartPolicy.Name}}'

# 3. Check if daemon is running
docker compose ps

# 4. Check restart count (how many times it auto-restarted)
docker inspect mijia-daemon --format='{{.RestartCount}}'

# 5. Check uptime
docker ps --filter name=mijia-daemon --format "table {{.Names}}\t{{.Status}}"

# 6. View recent logs
docker compose logs --tail=100 mijia-daemon
```

### Create Monitoring Script

```bash
nano ~/monitor-mijia.sh
```

```bash
#!/bin/bash
# Monitor Xiaomi Mijia Daemon Status

echo "=== Xiaomi Mijia Daemon Status ==="
echo

echo "Docker Service:"
sudo systemctl is-active docker
echo

echo "Container Status:"
docker compose ps
echo

echo "Restart Count:"
docker inspect mijia-daemon --format='Restarts: {{.RestartCount}}'
echo

echo "Uptime:"
docker ps --filter name=mijia-daemon --format "{{.Status}}"
echo

echo "Health Status:"
docker inspect mijia-daemon --format='Health: {{.State.Health.Status}}'
echo

echo "Recent Logs (last 10 lines):"
docker compose logs --tail=10 mijia-daemon
```

Make it executable:
```bash
chmod +x ~/monitor-mijia.sh
```

## Troubleshooting Auto-Start Issues

### Issue: Daemon doesn't start after reboot

**Check Docker service:**
```bash
sudo systemctl status docker
sudo systemctl enable docker
```

**Check Docker Compose configuration:**
```bash
cd /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon
docker compose config
```

**Check logs:**
```bash
docker compose logs mijia-daemon
sudo journalctl -u docker -n 100
```

### Issue: Daemon keeps restarting (crash loop)

**Check restart count:**
```bash
docker inspect mijia-daemon --format='{{.RestartCount}}'
```

**View logs to find error:**
```bash
docker compose logs --tail=200 mijia-daemon
```

**Check health status:**
```bash
docker inspect mijia-daemon --format='{{.State.Health.Status}}'
```

**Common causes:**
- MQTT broker not available
- Bluetooth adapter issues
- Configuration errors
- Permission problems

### Issue: Daemon won't restart after manual stop

This is expected behavior with `unless-stopped` policy. To restart:
```bash
docker compose start mijia-daemon
```

Or to completely restart everything:
```bash
docker compose restart
```

## Summary

✅ **Your current setup** (Docker Compose with `restart: unless-stopped`) is the **recommended approach**

**What you have:**
- Automatic restart after crashes ✅
- Automatic restart after system reboot ✅
- Manual control when you need it ✅
- No additional setup needed ✅

**Just ensure:**
1. Docker service is enabled: `sudo systemctl enable docker`
2. Daemon is started: `docker compose up -d`

That's it! The daemon will now automatically start after reboots and recover from crashes.
