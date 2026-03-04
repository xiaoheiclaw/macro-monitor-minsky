"""
Data Updater
============

Handles data update logic for all three layers:
- Structure layer (FRED API via DataLoader)
- Trend layer (Yahoo Finance / FRED)

Usage:
    from orchestrator.data_updater import DataUpdater

    updater = DataUpdater(project_root='/path/to/project')
    results = updater.update_all()
"""

import os
import sys
import subprocess


class DataUpdater:
    """Handles data update logic for Structure and Trend layers."""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def update_all(self, force: bool = False) -> dict:
        """
        Update all layer data.

        Args:
            force: Force re-download

        Returns:
            dict: Update status per layer
        """
        results = {}

        print("\n" + "=" * 60)
        print("UPDATING ALL DATA")
        print("=" * 60)

        print("\n[1/2] Updating Structure layer data...")
        results['structure'] = self.update_structure_data(force=force)

        print("\n[2/2] Updating Trend layer data...")
        results['trend'] = self.update_trend_data()

        print("\n" + "=" * 60)
        print("UPDATE COMPLETE")
        print("=" * 60)

        return results

    def update_structure_data(self, force: bool = False) -> dict:
        """
        Update Structure layer data via DataLoader CLI.

        Uses data.loader.DataLoader's CLI entry point.
        """
        loader_path = os.path.join(self.project_root, 'data', 'loader.py')

        if not os.path.exists(loader_path):
            return {'status': 'error', 'message': 'data/loader.py not found'}

        try:
            cmd = [sys.executable, loader_path]
            if force:
                cmd.append('--refresh')

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return {'status': 'success', 'message': 'Structure data updated'}
            else:
                return {'status': 'error', 'message': result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_trend_data(self) -> dict:
        """Update Trend layer data (Yahoo Finance / FRED)."""
        cache_script = os.path.join(
            self.project_root, 'trend', 'data', 'cache_all_factors.py'
        )

        if not os.path.exists(cache_script):
            return {'status': 'error', 'message': 'cache_all_factors.py not found'}

        try:
            result = subprocess.run(
                [sys.executable, cache_script],
                cwd=os.path.join(self.project_root, 'trend', 'data'),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return {'status': 'success', 'message': 'Trend data updated'}
            else:
                return {'status': 'error', 'message': result.stderr[:500]}

        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
