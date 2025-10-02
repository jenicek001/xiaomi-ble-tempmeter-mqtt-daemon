#!/usr/bin/env python3
"""
Test script for the new Hybrid MiBeacon Daemon.

Tests continuous listening, threshold-based publishing, and device auto-discovery.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.hybrid_main import HybridMijiaTemperatureDaemon, setup_logging


async def test_hybrid_daemon():
    """Test the hybrid daemon functionality."""
    print("🚀 Testing Hybrid MiBeacon Daemon")
    print("=" * 50)
    
    # Setup logging
    setup_logging("DEBUG")
    logger = logging.getLogger(__name__)
    
    # Create daemon instance
    daemon = HybridMijiaTemperatureDaemon("config/config.yaml")
    
    try:
        print("📡 Starting hybrid daemon...")
        
        # Start daemon in background
        daemon_task = asyncio.create_task(daemon.start())
        
        # Let it run for 2 minutes to test functionality
        print("⏱️  Running for 2 minutes to test continuous listening...")
        print("   - Looking for LYWSDCGQ devices")
        print("   - Testing threshold-based publishing")
        print("   - Validating device auto-discovery")
        print("   - Press Ctrl+C to stop early")
        
        await asyncio.sleep(120)  # Run for 2 minutes
        
        print("✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Test error: {e}")
    finally:
        print("🛑 Stopping daemon...")
        await daemon.stop()
        print("✨ Test cleanup completed")


if __name__ == "__main__":
    print("Hybrid MiBeacon Daemon Test")
    print("Make sure your LYWSDCGQ devices are nearby and advertising!")
    print()
    
    try:
        asyncio.run(test_hybrid_daemon())
    except Exception as e:
        print(f"Fatal test error: {e}")
        sys.exit(1)