# Codebase Restructuring Proposal

## Current Problems

1. **Root Directory Pollution**: 42 Python files in the root directory
2. **Duplicate Test Files**: Tests scattered between root and `tests/` directory
3. **Orphaned Code**: Unused modules in `src/` directory
4. **Documentation Fragmentation**: 9 markdown files in root, some outdated
5. **Experimental Code**: Discovery and debug scripts mixed with production code

## Proposed Structure

```
xiaomi-ble-tempmeter-mqtt-daemon/
├── .github/
│   └── copilot-instructions.md
├── config/
│   ├── config.yaml.example
│   └── README.md (configuration documentation)
├── docs/
│   ├── 11-minute-production-test.md
│   ├── DOCKER.md
│   ├── friendly-name-feature.md
│   ├── rssi-interpretation-proposal.md
│   ├── step2-ble-implementation.md
│   ├── step3-mqtt-publisher.md
│   ├── DOCKER_IMPROVEMENTS.md (moved from root)
│   ├── DOCKER_TEST_RESULTS.md (moved from root)
│   ├── PRODUCTION_TEST_SUMMARY.md (moved from root)
│   ├── TEST_RESULTS.md (moved from root)
│   └── PLANNING.md (moved from root)
├── experiments/
│   ├── discovery/
│   │   ├── discover_devices.py (moved from root)
│   │   ├── discover_sensors.py (moved from root)
│   │   └── discover_simple.py (moved from root)
│   ├── debugging/
│   │   ├── debug_detailed.py (moved from root)
│   │   ├── debug_humidity.py (moved from root)
│   │   └── debug_parsing.py (moved from root)
│   ├── decoding/
│   │   ├── analyze_xiaomi_format.py (moved from root)
│   │   ├── capture_humidity_pattern.py (moved from root)
│   │   ├── decode_manual.py (moved from root)
│   │   ├── decode_xiaomi.py (moved from root)
│   │   └── decode_xiaomi_messages.py (moved from root)
│   └── lywsdcgq/
│       ├── lywsdcgq_advertisement_scanner.py (already in experiments/)
│       ├── lywsdcgq_servicedata_analyzer.py (already in experiments/)
│       └── lywsdcgq_servicedata_parser.py (already in experiments/)
├── logs/
├── pictures/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── bluetooth_manager.py
│   ├── continuous_bluetooth_manager.py
│   ├── config_manager.py
│   ├── constants.py
│   ├── device_manager.py
│   ├── mqtt_publisher.py
│   ├── sensor_cache.py
│   └── utils/
│       ├── __init__.py
│       ├── health.py
│       └── logger.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_config.py (consolidated from root and tests/)
│   │   ├── test_mqtt_publisher.py (consolidated from root and tests/)
│   │   └── test_bluetooth.py (consolidated from root and tests/)
│   ├── integration/
│   │   ├── test_end_to_end.py (moved from root)
│   │   ├── test_complete_system.py (moved from root)
│   │   ├── test_integration.py (moved from root)
│   │   └── test_daemon_startup.py (moved from root)
│   └── obsolete/ (to be reviewed and deleted)
│       ├── test_alt_parsing.py (moved from root)
│       ├── test_ble_fixed.py (moved from root)
│       ├── test_bleak_api.py (moved from root)
│       ├── test_bluetooth_discovery.py (moved from root)
│       ├── test_bluetooth_manager.py (moved from root)
│       ├── test_bluetooth_simple.py (moved from root)
│       ├── test_correct_parsing.py (moved from root)
│       ├── test_detection.py (moved from root)
│       ├── test_extended_scan.py (moved from root)
│       ├── test_final_parsing.py (moved from root)
│       ├── test_fixed_parsing.py (moved from root)
│       ├── test_friendly_name.py (moved from root)
│       ├── test_full_sensor.py (moved from root)
│       ├── test_gatt.py (moved from root)
│       ├── test_humidity_decode.py (moved from root)
│       ├── test_hybrid_daemon.py (moved from root)
│       ├── test_mqtt_simple.py (moved from root)
│       ├── test_partial_data.py (moved from root)
│       ├── test_pattern_scan.py (moved from root)
│       ├── test_rssi_system.py (moved from root)
│       ├── test_rssi.py (moved from root)
│       └── test_sensor_diagnostics.py (moved from root)
├── .dockerignore
├── .env.example
├── .gitignore
├── ATTRIBUTION.md
├── docker-compose.yml
├── docker-compose.host-network.yml
├── docker-start.sh
├── Dockerfile
├── LICENSE
├── LICENSE-ORIGINAL
├── Makefile
├── README.md
├── requirements.txt
├── requirements-dev.txt
└── setup.py
```

## Files to Remove (Unused/Orphaned)

### From `src/` directory:
- [ ] `bluetooth_manager_advertisements.py` - Not imported anywhere, superseded by current implementation
- [ ] `hybrid_main.py` - Not used, development artifact

### From root directory:
- [ ] `README_OLD.md` - Superseded by current README.md
- [ ] `DOCKER_MQTT_REMOVAL.md` - Development notes, no longer relevant

## Files to Move

### Documentation (root → `docs/`)
- [ ] `PLANNING.md`
- [ ] `DOCKER_IMPROVEMENTS.md`
- [ ] `DOCKER_TEST_RESULTS.md`
- [ ] `PRODUCTION_TEST_SUMMARY.md`
- [ ] `TEST_RESULTS.md`

### Experiments (root → `experiments/`)

#### Discovery Scripts → `experiments/discovery/`
- [ ] `discover_devices.py`
- [ ] `discover_sensors.py`
- [ ] `discover_simple.py`

#### Debug Scripts → `experiments/debugging/`
- [ ] `debug_detailed.py`
- [ ] `debug_humidity.py`
- [ ] `debug_parsing.py`

#### Decoding Scripts → `experiments/decoding/`
- [ ] `analyze_xiaomi_format.py`
- [ ] `capture_humidity_pattern.py`
- [ ] `decode_manual.py`
- [ ] `decode_xiaomi.py`
- [ ] `decode_xiaomi_messages.py`

#### LYWSDCGQ Scripts (reorganize within `experiments/`)
Move existing files into `experiments/lywsdcgq/`:
- [ ] `experiments/lywsdcgq_advertisement_scanner.py` → `experiments/lywsdcgq/lywsdcgq_advertisement_scanner.py`
- [ ] `experiments/lywsdcgq_servicedata_analyzer.py` → `experiments/lywsdcgq/lywsdcgq_servicedata_analyzer.py`
- [ ] `experiments/lywsdcgq_servicedata_parser.py` → `experiments/lywsdcgq/lywsdcgq_servicedata_parser.py`

### Test Files (root → `tests/`)

#### Integration Tests → `tests/integration/`
- [ ] `test_end_to_end.py`
- [ ] `test_complete_system.py`
- [ ] `test_integration.py`
- [ ] `test_daemon_startup.py`

#### Unit Tests → `tests/unit/` (consolidate duplicates)
- [ ] Merge `test_config.py` (root) with `tests/test_config.py`
- [ ] Merge `test_mqtt_publisher.py` (root) with `tests/test_mqtt_publisher.py`
- [ ] Merge `test_mqtt.py` (root) with `tests/test_mqtt.py`
- [ ] Merge `test_bluetooth.py` (root) with `tests/test_bluetooth.py`

#### Obsolete Tests → `tests/obsolete/` (for later review/deletion)
- [ ] `test_alt_parsing.py`
- [ ] `test_ble_fixed.py`
- [ ] `test_bleak_api.py`
- [ ] `test_bluetooth_discovery.py`
- [ ] `test_bluetooth_manager.py`
- [ ] `test_bluetooth_simple.py`
- [ ] `test_correct_parsing.py`
- [ ] `test_detection.py`
- [ ] `test_extended_scan.py`
- [ ] `test_final_parsing.py`
- [ ] `test_fixed_parsing.py`
- [ ] `test_friendly_name.py`
- [ ] `test_full_sensor.py`
- [ ] `test_gatt.py`
- [ ] `test_humidity_decode.py`
- [ ] `test_hybrid_daemon.py`
- [ ] `test_mqtt_simple.py`
- [ ] `test_partial_data.py`
- [ ] `test_pattern_scan.py`
- [ ] `test_rssi_system.py`
- [ ] `test_rssi.py`
- [ ] `test_sensor_diagnostics.py`

## Benefits

1. **Clean Root Directory**: Only essential files (README, LICENSE, Dockerfile, etc.)
2. **Organized Tests**: Clear separation between unit, integration, and obsolete tests
3. **Preserved Experiments**: All experimental code kept in organized subdirectories
4. **Better Documentation**: All docs in one place with clear purpose
5. **Easier Maintenance**: Clear structure makes it obvious what's production vs. development
6. **Improved Discoverability**: New contributors can understand the project structure immediately

## Migration Steps

### Phase 1: Create New Directories
```bash
mkdir -p experiments/{discovery,debugging,decoding,lywsdcgq}
mkdir -p tests/{unit,integration,obsolete}
```

### Phase 2: Move Documentation
```bash
git mv PLANNING.md docs/
git mv DOCKER_IMPROVEMENTS.md docs/
git mv DOCKER_TEST_RESULTS.md docs/
git mv PRODUCTION_TEST_SUMMARY.md docs/
git mv TEST_RESULTS.md docs/
```

### Phase 3: Move Experimental Code
```bash
# Discovery scripts
git mv discover_*.py experiments/discovery/

# Debug scripts
git mv debug_*.py experiments/debugging/

# Decoding scripts
git mv analyze_xiaomi_format.py experiments/decoding/
git mv capture_humidity_pattern.py experiments/decoding/
git mv decode_*.py experiments/decoding/

# Reorganize LYWSDCGQ experiments
git mv experiments/lywsdcgq_*.py experiments/lywsdcgq/
```

### Phase 4: Consolidate Tests
```bash
# Move integration tests
git mv test_end_to_end.py tests/integration/
git mv test_complete_system.py tests/integration/
git mv test_integration.py tests/integration/
git mv test_daemon_startup.py tests/integration/

# Move obsolete tests
git mv test_alt_parsing.py tests/obsolete/
git mv test_ble_fixed.py tests/obsolete/
# ... (all obsolete tests)

# Consolidate unit tests (requires manual merge)
# Review and merge duplicate test files
```

### Phase 5: Remove Unused Files
```bash
# From src/
git rm src/bluetooth_manager_advertisements.py
git rm src/hybrid_main.py

# From root
git rm README_OLD.md
git rm DOCKER_MQTT_REMOVAL.md
```

### Phase 6: Update References
- [ ] Update `.gitignore` if needed
- [ ] Update `Makefile` test paths
- [ ] Update any CI/CD configurations
- [ ] Update README.md if it references moved files
- [ ] Add README.md files to new experiment subdirectories explaining their purpose

## Post-Migration Validation

1. Run all tests to ensure nothing broke: `make test`
2. Build Docker image: `make docker-build`
3. Test daemon startup: `make docker-run`
4. Verify all git history is preserved with `git log --follow`
5. Review and delete `tests/obsolete/` after confirming tests pass

## Timeline Estimate

- **Phase 1-3**: 15 minutes (simple file moves)
- **Phase 4**: 30 minutes (requires careful consolidation of duplicate tests)
- **Phase 5**: 5 minutes (deletions)
- **Phase 6**: 20 minutes (updates and documentation)
- **Validation**: 15 minutes

**Total**: ~1.5 hours

## Notes

- All file moves use `git mv` to preserve history
- Obsolete tests are moved to a temporary location for review rather than immediate deletion
- Unit test consolidation requires manual review to merge any unique test cases
- This restructuring does not change any production code behavior
- The `custom_components/` directory is left untouched (Home Assistant integration)
