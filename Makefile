# Makefile for Xiaomi Mijia Bluetooth Daemon

.PHONY: help install install-dev test lint format clean docker-build docker-run docker-stop docker-logs

# Default target
help:
	@echo "Available targets:"
	@echo ""
	@echo "  === Python Development ==="
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  run-dev      - Run daemon in development mode"
	@echo ""
	@echo "  === Testing ==="
	@echo "  test         - Run test suite"
	@echo "  test-cov     - Run tests with coverage"
	@echo ""
	@echo "  === Code Quality ==="
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black"
	@echo ""
	@echo "  === Docker Operations ==="
	@echo "  docker-build         - Build Docker image"
	@echo "  docker-build-multiarch - Build for multiple architectures"
	@echo "  docker-run           - Run daemon in Docker (host network)"
	@echo "  docker-stop          - Stop Docker container"
	@echo "  docker-restart       - Restart Docker container"
	@echo "  docker-logs          - View Docker container logs"
	@echo "  docker-shell         - Open shell in running container"
	@echo "  docker-stats         - Show container resource usage"
	@echo "  docker-health        - Check container health status"
	@echo "  docker-rebuild       - Rebuild and restart from scratch"
	@echo "  docker-clean         - Remove Docker images and containers"
	@echo "  docker-prune         - Prune all unused Docker resources"
	@echo ""
	@echo "  === Cleanup ==="
	@echo "  clean        - Clean build artifacts"

# Python environment setup
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

# Testing and code quality
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	pylint src/
	mypy src/
	flake8 src/

format:
	black src/ tests/
	isort src/ tests/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/ .coverage .pytest_cache/

# Docker operations
docker-build:
	@echo "Building Docker image..."
	docker build -t mijia-bluetooth-daemon:latest .
	@echo "✓ Build complete!"

docker-build-multiarch:
	@echo "Building multi-architecture Docker image..."
	docker buildx build --platform linux/amd64,linux/arm64 -t mijia-bluetooth-daemon:latest .
	@echo "✓ Multi-arch build complete!"

docker-run:
	@echo "Starting daemon with Docker Compose (host network)..."
	@echo "⚠️  Ensure .env file exists with MQTT broker credentials!"
	@echo "⚠️  Ensure your MQTT broker is running and accessible!"
	docker compose up -d
	@echo "✓ Daemon started!"
	@echo "Use 'make docker-logs' to view logs"

docker-stop:
	@echo "Stopping daemon..."
	docker compose down
	@echo "✓ Daemon stopped!"

docker-restart:
	@echo "Restarting daemon..."
	docker compose restart mijia-daemon
	@echo "✓ Daemon restarted!"

docker-logs:
	docker compose logs -f mijia-daemon

docker-shell:
	docker compose exec mijia-daemon /bin/bash

docker-stats:
	docker stats mijia-daemon

docker-health:
	@echo "Container health status:"
	@docker inspect --format='{{.State.Health.Status}}' mijia-daemon || echo "No health check configured"

docker-clean:
	@echo "Cleaning Docker resources..."
	docker compose down -v
	docker rmi mijia-bluetooth-daemon:latest || true
	@echo "✓ Cleanup complete!"

docker-rebuild:
	@echo "Rebuilding and restarting..."
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "✓ Rebuild complete!"

docker-prune:
	@echo "Pruning unused Docker resources..."
	docker system prune -af --volumes
	@echo "✓ Prune complete!"

# Development helpers
run-dev:
	uvx --from . python -m src.main --config config/config.yaml --log-level DEBUG

run-dev-info:
	uvx --from . python -m src.main --config config/config.yaml --log-level INFO

check-deps:
	pip-audit

# Release tasks (TODO: implement in CI/CD phase)
release-test:
	python setup.py sdist bdist_wheel
	twine check dist/*

# Documentation (TODO: implement in later phases)
docs:
	@echo "Documentation generation not yet implemented"