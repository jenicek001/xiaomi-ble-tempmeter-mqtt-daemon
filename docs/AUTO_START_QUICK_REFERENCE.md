# Quick Auto-Start Setup Summary

## ✅ Your Current Status

**Good news!** Your daemon is already configured for automatic restart:

```
✅ Docker service: enabled (starts on boot)
✅ Restart policy: unless-stopped
✅ Current status: running
✅ Restart count: 0 (no crashes yet)
```

## What This Means

Your daemon will **automatically start** in these scenarios:

1. **After system reboot** - Docker starts on boot, then starts your daemon
2. **After crash** - Container automatically restarts within seconds
3. **After Docker service restart** - Daemon comes back up automatically
4. **After power loss** - When system boots, everything starts automatically

The only time it **won't** automatically restart is if you manually stop it with:
- `docker compose stop`
- `docker stop mijia-daemon`

## Quick Test Commands

### Test Auto-Restart After Crash
```bash
# Simulate a crash by killing the Python process
docker exec mijia-daemon pkill -9 python

# Wait 10 seconds
sleep 10

# Check if it restarted (should show "running")
docker compose ps
```

### Test After Reboot
```bash
# Reboot the system
sudo reboot

# After system comes back up, check status
docker compose ps

# Should show "running" with uptime starting from boot time
```

### Check How Many Times It Has Restarted
```bash
docker inspect mijia-daemon --format='{{.RestartCount}}'
```

## Monitoring Commands

```bash
# Quick status check
docker compose ps

# View last 50 log lines
docker compose logs --tail=50 mijia-daemon

# Follow logs in real-time
docker compose logs -f mijia-daemon

# Check restart count and uptime
docker ps --filter name=mijia-daemon --format "table {{.Names}}\t{{.Status}}"
```

## If You Need to Manually Start/Stop

```bash
# Start (if stopped)
docker compose start mijia-daemon

# Stop (prevents auto-restart until you start it again)
docker compose stop mijia-daemon

# Restart (useful for applying configuration changes)
docker compose restart mijia-daemon

# Full rebuild and restart
docker compose up -d --build
```

## Verifying Everything After Reboot

After any system reboot, run these commands to verify:

```bash
cd /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon

# 1. Check Docker is running
sudo systemctl status docker

# 2. Check daemon is running
docker compose ps

# 3. Check daemon logs for any errors
docker compose logs --tail=100 mijia-daemon

# 4. Check health status
make docker-health
```

## Complete Monitoring Script

I've created a monitoring script for you:

```bash
# Create the script
cat > ~/check-mijia-status.sh << 'EOF'
#!/bin/bash
echo "=== Xiaomi Mijia Daemon Status ==="
echo
echo "Docker Service: $(sudo systemctl is-active docker)"
echo
echo "Container Status:"
docker compose -f /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon/docker-compose.yml ps
echo
echo "Restart Count: $(docker inspect mijia-daemon --format='{{.RestartCount}}')"
echo "Health: $(docker inspect mijia-daemon --format='{{.State.Health.Status}}')"
echo
echo "Last 5 log lines:"
docker compose -f /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon/docker-compose.yml logs --tail=5 mijia-daemon
EOF

# Make it executable
chmod +x ~/check-mijia-status.sh

# Run it anytime to check status
~/check-mijia-status.sh
```

## Troubleshooting

### Daemon Not Running After Reboot?

```bash
# Check if Docker started
sudo systemctl status docker

# If Docker didn't start, enable it
sudo systemctl enable docker
sudo systemctl start docker

# Start the daemon
cd /home/honzik/xiaomi-ble-tempmeter-mqtt-daemon
docker compose up -d
```

### Daemon Keeps Crashing?

```bash
# Check logs for errors
docker compose logs --tail=200 mijia-daemon

# Common issues:
# - MQTT broker not reachable
# - Bluetooth adapter problems
# - Configuration errors

# Check restart count
docker inspect mijia-daemon --format='{{.RestartCount}}'
```

## Summary

**You don't need to do anything!** Your setup is already configured correctly:

1. ✅ Docker starts on boot
2. ✅ Daemon has `restart: unless-stopped` policy
3. ✅ Currently running healthy

The daemon will automatically:
- Start after system reboots
- Restart after crashes
- Recover from temporary failures

Just use `docker compose stop` when you intentionally want to stop it, and `docker compose start` or `docker compose up -d` to start it again.
