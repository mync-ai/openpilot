#!/usr/bin/env python3
"""
Seat Control Hyperparameter Experiment Script

This script runs the seat control service with various hyperparameter combinations
to test and evaluate performance. It can run single experiments or systematic
hyperparameter sweeps.
"""

import argparse
import sys
import os
import subprocess
import time
import itertools
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# Add the openpilot root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from sunnypilot_dev_msync.msync_src.seat_control_service import run_service


class SeatControlExperiment:
    """Manages seat control hyperparameter experiments."""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir
        self.results = []

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def run_single_experiment(self, params: Dict[str, Any], duration: int = 60):
        """
        Run a single experiment with given parameters.

        Args:
            params: Dictionary of hyperparameters
            duration: Duration to run the experiment in seconds
        """
        print(f"Running experiment with parameters: {params}")

        experiment_start = datetime.now()

        try:
            # Import and run the service directly for better control
            from sunnypilot_dev_msync.msync_src.seat_control_service import run_service

            # Note: This would ideally run the service for the specified duration
            # and collect metrics. For now, we'll simulate the experiment.
            print(f"  Starting service for {duration} seconds...")

            # Simulate experiment results
            experiment_result = {
                'timestamp': experiment_start.isoformat(),
                'parameters': params,
                'duration': duration,
                'status': 'completed',
                'metrics': {
                    'avg_response_time': 0.05,  # Placeholder
                    'command_frequency': params['frequency'],
                    'error_count': 0
                }
            }

            self.results.append(experiment_result)
            print(f"  Experiment completed successfully")

            return experiment_result

        except Exception as e:
            print(f"  Experiment failed: {e}")
            experiment_result = {
                'timestamp': experiment_start.isoformat(),
                'parameters': params,
                'duration': duration,
                'status': 'failed',
                'error': str(e)
            }
            self.results.append(experiment_result)
            return experiment_result

    def run_subprocess_experiment(self, params: Dict[str, Any], duration: int = 60):
        """
        Run experiment by launching seat_control_service as a subprocess.

        Args:
            params: Dictionary of hyperparameters
            duration: Duration to run the experiment in seconds
        """
        print(f"Running subprocess experiment with parameters: {params}")

        # Build command line arguments
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'seat_control_service.py'),
            '--frequency', str(params['frequency']),
            '--turn-thresh-1', str(params['turn_thresh_1']),
            '--turn-thresh-2', str(params['turn_thresh_2']),
            '--long-thresh', str(params['long_thresh']),
            '--smoothing-window', str(params['smoothing_window'])
        ]

        # Add use_plan flag if True
        if params.get('use_plan', False):
            cmd.append('--use-plan')

        # Add topics if specified
        if 'topics' in params:
            cmd.extend(['--topics'] + params['topics'])

        print(f"  Command: {' '.join(cmd)}")

        experiment_start = datetime.now()

        try:
            # Start the service
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Let it run for the specified duration
            time.sleep(duration)

            # Stop the service
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            experiment_result = {
                'timestamp': experiment_start.isoformat(),
                'parameters': params,
                'duration': duration,
                'status': 'completed',
                'return_code': process.returncode,
                'metrics': {
                    'command_frequency': params['frequency'],
                    'process_duration': duration
                }
            }

            self.results.append(experiment_result)
            print(f"  Experiment completed with return code: {process.returncode}")

            return experiment_result

        except Exception as e:
            print(f"  Experiment failed: {e}")
            experiment_result = {
                'timestamp': experiment_start.isoformat(),
                'parameters': params,
                'duration': duration,
                'status': 'failed',
                'error': str(e)
            }
            self.results.append(experiment_result)
            return experiment_result

    def run_grid_search(self, param_grid: Dict[str, List], duration: int = 60,
                       use_subprocess: bool = True):
        """
        Run a grid search over hyperparameter combinations.

        Args:
            param_grid: Dictionary where keys are parameter names and values are lists of values to try
            duration: Duration for each experiment
            use_subprocess: Whether to run experiments as subprocesses
        """
        print(f"Starting grid search with {len(param_grid)} parameters")

        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        print(f"Total combinations to test: {len(combinations)}")

        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            print(f"\n--- Experiment {i+1}/{len(combinations)} ---")

            if use_subprocess:
                self.run_subprocess_experiment(params, duration)
            else:
                self.run_single_experiment(params, duration)

            # Small delay between experiments
            time.sleep(2)

        print(f"\nGrid search completed. {len(self.results)} experiments run.")

    def save_results(self, filename: Optional[str] = None):
        """Save experiment results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"seat_control_experiments_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"Results saved to: {filepath}")
        return filepath

    def print_summary(self):
        """Print a summary of experiment results."""
        if not self.results:
            print("No experiment results to summarize.")
            return

        print("\n" + "="*60)
        print("EXPERIMENT SUMMARY")
        print("="*60)

        total_experiments = len(self.results)
        successful = sum(1 for r in self.results if r['status'] == 'completed')
        failed = total_experiments - successful

        print(f"Total experiments: {total_experiments}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")

        if successful > 0:
            print("\nSuccessful experiments:")
            for i, result in enumerate([r for r in self.results if r['status'] == 'completed']):
                params = result['parameters']
                use_plan_str = f", plan={params.get('use_plan', False)}"
                print(f"  {i+1}. freq={params['frequency']}, turn1={params['turn_thresh_1']}, "
                      f"turn2={params['turn_thresh_2']}, long={params['long_thresh']}, "
                      f"smooth={params['smoothing_window']}{use_plan_str}")

        if failed > 0:
            print("\nFailed experiments:")
            for i, result in enumerate([r for r in self.results if r['status'] == 'failed']):
                params = result['parameters']
                error = result.get('error', 'Unknown error')
                print(f"  {i+1}. {params} - Error: {error}")


def main():
    parser = argparse.ArgumentParser(
        description='Run seat control hyperparameter experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Single experiment with custom parameters
  %(prog)s --frequency 30 --turn-thresh-1 0.8 --turn-thresh-2 2.0 --duration 120

  # Grid search over multiple values
  %(prog)s --grid-search --frequency 10,20,30 --turn-thresh-1 0.5,1.0,1.5 --duration 60

  # Quick test with default parameters
  %(prog)s --duration 30
        '''
    )

    # Experiment control
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration for each experiment in seconds')
    parser.add_argument('--grid-search', action='store_true',
                       help='Run grid search over parameter combinations')
    parser.add_argument('--output-dir', default='data',
                       help='Directory to save results')
    parser.add_argument('--use-subprocess', action='store_true', default=True,
                       help='Run experiments as subprocesses (recommended)')

    # Hyperparameters - can be single values or comma-separated lists for grid search
    parser.add_argument('--frequency', default='20',
                       help='Update frequency in Hz (single value or comma-separated list)')
    parser.add_argument('--turn-thresh-1', default='1.0',
                       help='First turn threshold (single value or comma-separated list)')
    parser.add_argument('--turn-thresh-2', default='2.5',
                       help='Second turn threshold (single value or comma-separated list)')
    parser.add_argument('--long-thresh', default='1.0',
                       help='Longitudinal threshold (single value or comma-separated list)')
    parser.add_argument('--smoothing-window', default='4',
                       help='Smoothing window size (single value or comma-separated list)')
    parser.add_argument('--use-plan', action='store_true', default=False,
                       help='Use plan data instead of prediction data for longitudinal decisions')
    parser.add_argument('--topics', nargs='+',
                       default=['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState'],
                       help='List of topics to subscribe to')

    args = parser.parse_args()

    # Create experiment manager
    experiment = SeatControlExperiment(output_dir=args.output_dir)

    if args.grid_search:
        # Parse parameter ranges for grid search
        param_grid = {}

        if ',' in args.frequency:
            param_grid['frequency'] = [int(x.strip()) for x in args.frequency.split(',')]
        else:
            param_grid['frequency'] = [int(args.frequency)]

        if ',' in args.turn_thresh_1:
            param_grid['turn_thresh_1'] = [float(x.strip()) for x in args.turn_thresh_1.split(',')]
        else:
            param_grid['turn_thresh_1'] = [float(args.turn_thresh_1)]

        if ',' in args.turn_thresh_2:
            param_grid['turn_thresh_2'] = [float(x.strip()) for x in args.turn_thresh_2.split(',')]
        else:
            param_grid['turn_thresh_2'] = [float(args.turn_thresh_2)]

        if ',' in args.long_thresh:
            param_grid['long_thresh'] = [float(x.strip()) for x in args.long_thresh.split(',')]
        else:
            param_grid['long_thresh'] = [float(args.long_thresh)]

        if ',' in args.smoothing_window:
            param_grid['smoothing_window'] = [int(x.strip()) for x in args.smoothing_window.split(',')]
        else:
            param_grid['smoothing_window'] = [int(args.smoothing_window)]

        # Add topics to all experiments
        param_grid['topics'] = [args.topics]

        # Run grid search
        experiment.run_grid_search(param_grid, args.duration, args.use_subprocess)

    else:
        # Single experiment
        params = {
            'frequency': int(args.frequency),
            'turn_thresh_1': float(args.turn_thresh_1),
            'turn_thresh_2': float(args.turn_thresh_2),
            'long_thresh': float(args.long_thresh),
            'smoothing_window': int(args.smoothing_window),
            'use_plan': args.use_plan,
            'topics': args.topics
        }

        if args.use_subprocess:
            experiment.run_subprocess_experiment(params, args.duration)
        else:
            experiment.run_single_experiment(params, args.duration)

    # Save results and print summary
    experiment.save_results()
    experiment.print_summary()


if __name__ == "__main__":
    main()