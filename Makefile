# Makefile for Xiaomi Mijia Bluetooth Daemon

.PHONY: help install install-dev test lint format clean docker-build docker-run

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black"
	@echo "  clean        - Clean build artifacts"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run daemon in Docker container"

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
	docker build -t mijia-bluetooth-daemon .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Development helpers
run-dev:
	python src/main.py --config config/config.yaml --log-level DEBUG

check-deps:
	pip-audit

# Release tasks (TODO: implement in CI/CD phase)
release-test:
	python setup.py sdist bdist_wheel
	twine check dist/*

# Documentation (TODO: implement in later phases)
docs:
	@echo "Documentation generation not yet implemented"