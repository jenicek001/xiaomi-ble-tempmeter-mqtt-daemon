#!/usr/bin/env python3
"""Setup configuration for Xiaomi Mijia Bluetooth Daemon."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
requirements = []
with open("requirements.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            # Remove version constraints for setup.py
            req = line.split(">=")[0].split("==")[0].split("~=")[0]
            requirements.append(req)

setup(
    name="xiaomi-mijia-bluetooth-daemon",
    version="1.0.0-dev",
    description="Standalone Linux daemon for Xiaomi Mijia Bluetooth thermometers with MQTT support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="jenicek001",
    author_email="",
    url="https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "aiohttp>=3.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mijia-daemon=mijia_daemon.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators", 
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Home Automation",
        "Topic :: System :: Hardware",
        "Topic :: Communications",
    ],
    keywords="xiaomi mijia bluetooth ble thermometer mqtt raspberry-pi iot home-assistant",
    project_urls={
        "Bug Reports": "https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/issues",
        "Source": "https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon",
        "Documentation": "https://github.com/jenicek001/xiaomi-ble-tempmeter-mqtt-daemon/blob/main/README.md",
        "Original Work": "https://github.com/leonxi/mitemp_bt2",
    },
)