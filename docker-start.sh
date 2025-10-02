#!/bin/bash
# Quick Start Script for Docker Deployment

set -e

echo "========================================="
echo "Xiaomi Mijia Bluetooth Daemon"
echo "Docker Quick Start"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose not found, trying docker compose..."
    if ! docker compose version &> /dev/null; then
        echo "❌ Docker Compose is not installed!"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✓ Docker is installed"
echo "✓ Docker Compose is installed"
echo ""

# Check if config file exists
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️  Config file not found, creating from example..."
    if [ -f "config/config.yaml.example" ]; then
        cp config/config.yaml.example config/config.yaml
        echo "✓ Created config/config.yaml"
        echo ""
        echo "⚠️  IMPORTANT: Edit config/config.yaml with your settings:"
        echo "   - MQTT broker credentials"
        echo "   - Device MAC addresses and friendly names"
        echo ""
        read -p "Press Enter to continue after editing config.yaml, or Ctrl+C to exit..."
    else
        echo "❌ config/config.yaml.example not found!"
        exit 1
    fi
else
    echo "✓ Config file exists"
fi

echo ""
echo "========================================="
echo "Building Docker Image"
echo "========================================="
echo ""

docker build -t mijia-bluetooth-daemon:latest .

echo ""
echo "✓ Docker image built successfully!"
echo ""

echo "========================================="
echo "Starting Container"
echo "========================================="
echo ""
echo "Select network mode:"
echo "  1) Host network (recommended for Bluetooth)"
echo "  2) Bridge network (if you need network isolation)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo "Starting with host network mode..."
        $DOCKER_COMPOSE -f docker-compose.host-network.yml up -d
        ;;
    2)
        echo "Starting with bridge network mode..."
        $DOCKER_COMPOSE up -d
        ;;
    *)
        echo "Invalid choice, using host network (default)..."
        $DOCKER_COMPOSE -f docker-compose.host-network.yml up -d
        ;;
esac

echo ""
echo "========================================="
echo "✓ Daemon Started Successfully!"
echo "========================================="
echo ""
echo "Useful commands:"
echo "  View logs:     $DOCKER_COMPOSE logs -f mijia-daemon"
echo "  Stop daemon:   $DOCKER_COMPOSE down"
echo "  Restart:       $DOCKER_COMPOSE restart"
echo "  Status:        docker ps"
echo ""
echo "Checking logs (press Ctrl+C to exit)..."
echo ""

sleep 2
$DOCKER_COMPOSE logs -f mijia-daemon
