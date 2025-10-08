# Pull Request: Major repository restructuring, timezone fix, and documentation improvements

## Overview
This PR includes comprehensive improvements to repository structure, timezone handling, and documentation.

## 📁 Restructuring Changes
- **Organized 42+ Python files** from root into structured directories
- Created `experiments/` directory with 4 subdirectories:
  - `discovery/` - BLE device discovery scripts (3 files)
  - `debugging/` - Debugging and diagnostic tools (3 files)
  - `decoding/` - Data parsing and format analysis (5 files)
  - `lywsdcgq/` - LYWSDCGQ-specific experiments (3 files)
- Created `tests/` directory structure:
  - `unit/` - Unit tests (4 files)
  - `integration/` - Integration tests (4 files)
  - `obsolete/` - Archived tests for reference (30 files)
- Moved 5 documentation files to `docs/` directory
- Added README.md files to each experiment subdirectory
- Removed unused source files and obsolete documentation
- Updated .gitignore with project-specific patterns
- **Root directory cleaned**: 50+ files → 13 essential files

## 🕐 Timezone Fix
- Added `TZ` environment variable support to docker-compose.yml
- Configured timezone in .env and .env.example (default: Europe/Prague)
- Fixed MQTT message timestamps to show **local time instead of UTC**
- Python datetime.now().astimezone() now respects container timezone
- ✅ Validated: Container time, Python datetimes, and daemon logs all use correct timezone

## 📖 Documentation Improvements
- Updated README.md with Docker build process clarification
- **Added comprehensive Docker installation instructions for Raspberry Pi**
- Documented timezone configuration in .env.example
- Created detailed documentation in docs/:
  - RESTRUCTURING_PROPOSAL.md - Initial analysis and plan
  - RESTRUCTURING_SUMMARY.md - Completed changes summary
  - TIMEZONE_FIX_PROPOSAL.md - Timezone issue analysis
  - TIMEZONE_FIX_COMPLETED.md - Timezone fix validation
  - FINAL_COMMIT_SUMMARY.md - Complete session summary

## ✅ Validation
- Docker builds successfully
- Daemon runs healthy with correct timezone
- All file moves preserve git history
- No breaking changes to functionality

## 📊 Changes Summary
- **71 files changed**: 1,419 insertions(+), 1,359 deletions(-)
- File operations: 57 renames, 8 new files, 6 deletions, 5 modifications

## Testing Done
- ✅ Docker image builds successfully on Raspberry Pi
- ✅ Daemon starts and runs healthy
- ✅ Timezone displays correctly in all MQTT messages
- ✅ BLE sensor discovery and data collection working
- ✅ MQTT publishing with Home Assistant discovery functional
