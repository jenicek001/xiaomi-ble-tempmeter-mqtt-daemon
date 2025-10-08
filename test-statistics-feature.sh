#!/bin/bash
# Test script for statistics feature

echo "=== Testing Live Data Statistics Feature ==="
echo ""

echo "1. Building Docker image with new feature..."
docker build -t mijia-bluetooth-daemon:statistics-test .

echo ""
echo "2. Stopping current daemon..."
docker stop mijia-daemon

echo ""
echo "3. Starting daemon with statistics feature..."
docker run --rm --name mijia-daemon-test \
  --network host \
  --privileged \
  -v /run/dbus:/run/dbus:ro \
  -v $(pwd)/config:/config \
  mijia-bluetooth-daemon:statistics-test \
  python -m src.main --config /config/config.yaml --log-level DEBUG &

DAEMON_PID=$!
echo "Daemon started with PID: $DAEMON_PID"

echo ""
echo "4. Waiting 10 seconds for daemon to initialize..."
sleep 10

echo ""
echo "5. Subscribing to MQTT to see statistics (will show next 5 messages)..."
mosquitto_sub -h localhost -u openhabian -P M30ZeZuQo1bHjrn7g93k \
  -t "mijiableht/+/state" -v -C 5 | jq -R 'fromjson?'

echo ""
echo "6. Stopping test daemon..."
docker stop mijia-daemon-test

echo ""
echo "7. Restarting original daemon..."
docker start mijia-daemon

echo ""
echo "=== Test Complete ==="
