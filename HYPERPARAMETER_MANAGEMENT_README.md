# Seat Control Hyperparameter Management

This document describes the current hyperparameter management architecture for the seat control subsystem in this fork. The system is now intentionally minimal: configuration lives in a single JSON file, is edited via a CLI, and is hot‑reloaded by the running service. All legacy messaging-based configuration request/response paths and the Qt UI dialog have been removed to reduce complexity, avoid publisher conflicts, and simplify testing.

## High-Level Goals
- Single source of truth for runtime tunables
- Safe validation + atomic persistence
- Zero messaging dependencies for configuration
- Predictable hot reload without restarting the process
- Easy scripted + interactive modification workflow

## Current Architecture Overview
Component | Role
--------- | ----
`parameter_manager.py` | Validation, defaults, atomic read/write of JSON config
`seat_control_cli.py` | User interface (non-interactive flags + interactive shell)
`seat_control_service_enhanced.py` | Polls config file mtime; restarts internal components when changes detected
`short_control.py` | Decision logic consuming the validated parameter set
`cereal/custom.capnp` | Contains only the `SeatControl` command struct (config structs removed)

## Configuration Data Flow
```
User (CLI) ──> parameter_manager (validate + write JSON) ──> config file
                                                         └── service polls ──> detects change ──> reloads parameters ──> new seatControl outputs
```

## Removed / Simplified Elements
Removed Element | Rationale
--------------- | ---------
`SeatControlConfig` / `SeatControlConfigRequest` capnp structs | Eliminated messaging path; IDs reserved but not reused
Qt configuration dialog (`seat_control_button.*`) | Replaced by CLI; reduces UI maintenance & build surface
Messaging topics `seatControlConfig`, `seatControlConfigRequest` | No longer produced or subscribed; entries removed from `services.py` and `log.capnp`
Ad-hoc test publisher/subscriber for config | Obsolete with file-based approach

## Parameter Set
Name | Default | Range | Meaning
---- | ------- | ----- | -------
`frequency` | 20 | 1–100 (int) | Control loop / command emission frequency (Hz)
`turn_thresh_1` | 1.0 | 0.1–10.0 | Mild lateral acceleration threshold
`turn_thresh_2` | 2.5 | 0.1–15.0 | Hard lateral acceleration threshold
`long_thresh` | 1.0 | 0.1–10.0 | Longitudinal acceleration threshold
`sm oothing_window` | 4 | 1–20 (int) | Temporal smoothing sample count
`horizon` | 3.0 | 0.5–10.0 | Prediction horizon (s)
`use_plan` | false | boolean | Select plan trajectory vs model predictions

(See `DEFAULT_CONFIG` and `PARAM_RANGES` inside `parameter_manager.py` for authoritative definitions.)

## Persistence Format
Path (default): `/tmp/seat_control_config.json`

Example:
```json
{
  "frequency": 20,
  "turn_thresh_1": 1.0,
  "turn_thresh_2": 2.5,
  "long_thresh": 1.0,
  "smoothing_window": 4,
  "horizon": 3.0,
  "use_plan": false,
  "_timestamp_ns": 1730000000000000000
}
```
The `_timestamp_ns` field is internal; it is refreshed on writes and ignored for validation of user parameters.

Writes are atomic: a temporary file is written then `os.replace` swaps it into place to avoid partial read states during service polling.

## CLI Usage (`seat_control_cli.py`)
Common operations:
```
python -m sunnypilot_dev_msync.msync_src.seat_control_cli --show
python -m sunnypilot_dev_msync.msync_src.seat_control_cli --set frequency=30 turn_thresh_1=0.8 use_plan=true
python -m sunnypilot_dev_msync.msync_src.seat_control_cli --reset
python -m sunnypilot_dev_msync.msync_src.seat_control_cli --interactive
```
Interactive commands:
- `show` / `print` – display current config
- `set key=value [...]` – apply validated updates
- `reset` – restore defaults
- `watch [interval]` – print config whenever it changes
- `quit` / `exit` – leave interactive mode

Exit codes (non-interactive):
- `0` success
- `1` argument parsing / validation error
- `2` save failure

## Validation Rules
Enforced in `SeatControlParameterManager.validate_config`:
- Range checks per `PARAM_RANGES`
- Type coercion handled by CLI parsing; manager re-validates types and bounds
- No partial commits: full merged config must pass validation before persistence

## Hot Reload Mechanism
The service maintains:
- Last modification timestamp & cached config
- Poll loop (interval derived from internal logic) that checks `stat().st_mtime`
- On change: reload + reinstantiate dependent components (publisher / decider)

Benefits:
- No messaging handshake or request IDs
- Avoids `MultiplePublishersError` seen with prior design
- Deterministic, low overhead (single file stat)

## Adding or Modifying Parameters
1. Add default + range in `parameter_manager.py`
2. Extend any dependent logic in `short_control.py`
3. (Optional) Document in this README if broadly useful
4. Update tests if constraints or defaults changed
5. Run CLI `--reset` to populate new field on existing deployments

No schema or messaging changes are required.

## Testing Strategy
Test Type | Focus
--------- | -----
Unit tests | Validation boundaries, parsing, default reset
Integration (service + CLI) | Hot reload path correctness (modify file while service runs)
Regression | Ensure removal of messaging topics does not break other modules

Recommended test patterns:
- Write invalid value → expect rejection & unchanged file content
- Concurrent CLI writes while service polls → ensure no partial reads / crashes
- Rapid successive updates → verify latest config ultimately applied

## Seat Control Messaging
Remaining message: `seatControl` (command + source + timestamp). This is still published for downstream consumers and logging. Configuration messages are no longer emitted.

## Rationale for Simplification
- Eliminated flakiness from dual publishers
- Reduced cognitive + maintenance load
- Simplified test harness (no messaging bootstrap needed)
- Clear separation between runtime data (messaging) and configuration (file)

## Future Enhancements (Optional)
Idea | Notes
---- | -----
Inotify / kqueue watcher | Replace polling with event-driven reload if needed
Schema regeneration tool | Auto-doc current parameter set from code
Profile-based configs | Multiple JSON presets selectable via CLI flag
Safety envelope checker | Pre-commit evaluation for extreme or unsafe parameter combinations

## Quick FAQ
Q: Why are config structs missing from `custom.capnp`?
A: They were intentionally removed after migrating to file-based management. Their numeric IDs are reserved and not reused.

Q: How do I revert to defaults?
A: `seat_control_cli --reset` (optionally followed by `--show`).

Q: Does the service need a restart after parameter changes?
A: No; it hot reloads on file modification.

Q: Can I script batch changes?
A: Yes; call the CLI repeatedly or manipulate the JSON then run a no-op `--show` to confirm.

## Summary
The hyperparameter system is now a lean, file-driven mechanism emphasizing reliability, debuggability, and ease of extension. All prior messaging and UI layers for configuration have been retired in favor of a single validated JSON pathway.
