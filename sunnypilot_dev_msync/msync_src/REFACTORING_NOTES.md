# Seat Control Service Refactoring Summary

## Changes Made

### 1. Centralized SubMaster Management
- **`seat_control_service.py`**: Now creates and manages the SubMaster instance
- **`op_translator.py`**: Refactored to accept SubMaster as a parameter instead of creating its own
- **`seat_control_integration.py`**: Updated to accept SubMaster from the service

### 2. Enhanced Command Line Interface
- All hyperparameters are now exposed as command-line arguments in `seat_control_service.py`
- Added `--topics` argument to specify which message topics to subscribe to
- Added `--use-plan` flag to control whether to use plan data or prediction data for longitudinal decisions
- Default values are maintained for all parameters

### 3. New Experiment Script
- **`seat_control_exp.py`**: New script for running hyperparameter experiments
- Supports both single experiments and grid search
- Can run experiments as subprocesses for better isolation
- Saves results to JSON files with timestamps and metrics
- Includes support for the new `use_plan` parameter

### 4. Plan Data Integration
- **`op_translator.py`**: Updated to extract both prediction and plan data from messages
- **`short_control.py`**: Enhanced to handle plan data with fallback to prediction data
- Supports switching between plan and prediction data via the `use_plan` parameter

## Usage Examples

### Basic Service Usage
```bash
# Run with default parameters (using prediction data)
python seat_control_service.py

# Run with plan data instead of predictions
python seat_control_service.py --use-plan

# Run with custom parameters and plan data
python seat_control_service.py --frequency 30 --turn-thresh-1 0.8 --use-plan

# Run with specific topics only
python seat_control_service.py --topics modelV2 carState longitudinalPlan --use-plan
```

### Experiment Usage
```bash
# Single experiment with plan data
python seat_control_exp.py --frequency 30 --turn-thresh-1 0.8 --use-plan --duration 120

# Grid search comparing prediction vs plan data
python seat_control_exp.py --grid-search --frequency 20,30 --use-plan --duration 60

# Quick test run with plan data
python seat_control_exp.py --use-plan --duration 30
```

## Architecture Benefits

1. **Modular Design**: SubMaster is created once and passed to components that need it
2. **Parameter Flexibility**: All hyperparameters can be adjusted without code changes
3. **Data Source Control**: Can switch between prediction and plan data for longitudinal decisions
4. **Experiment Support**: Systematic testing of parameter combinations including data source
5. **Clean Separation**: Service logic is separated from experiment logic
6. **Reusability**: Components can be imported and used programmatically

## New `use_plan` Parameter

The `use_plan` boolean parameter controls which data source is used for longitudinal decisions:

- **`False` (default)**: Uses ModelV2 prediction data (acceleration and velocity predictions)
- **`True`**: Uses longitudinal plan data (planned accelerations and speeds)

### Implementation Details:
- Plan data is extracted from `longitudinalPlan` messages in `op_translator.py`
- The `Decider` class automatically falls back to prediction data if plan data is unavailable
- The `get_x_vectors()` method returns the appropriate data based on the `use_plan` setting
- Both data sources use the same horizon and indexing logic

## File Structure
```
msync_src/
├── seat_control_service.py      # Main service with SubMaster management
├── seat_control_integration.py  # Publisher that accepts SubMaster
├── op_translator.py             # Data extraction (prediction + plan data)
├── seat_control_exp.py          # Hyperparameter experiment runner
└── short_control.py             # Decision logic with plan/prediction support
```

## Migration Notes

- `op_translator.py` no longer creates its own SubMaster
- `seat_control_integration.py` constructor now requires a SubMaster parameter
- All hyperparameters including `use_plan` can be passed via command line
- Plan data extraction requires `longitudinalPlan` in the topics list
- Experiment results now include the `use_plan` setting in summaries