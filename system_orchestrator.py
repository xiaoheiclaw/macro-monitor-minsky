"""
System Orchestrator - Main entry point for the macro risk monitoring system.
=============================================================================

Thin wrapper that delegates to orchestrator/ submodules while maintaining
the original public API for backward compatibility.

Usage:
    python system_orchestrator.py              # 查看当前状态 (v2 dashboard)
    python system_orchestrator.py --update     # 更新数据并查看
    python system_orchestrator.py --json out.json  # 导出 JSON
    python system_orchestrator.py --update-only    # 仅更新数据
"""

import os
import sys
import json
import argparse
import warnings
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

# === Path Setup ===
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

_paths_to_add = [
    PROJECT_ROOT,
    os.path.join(PROJECT_ROOT, 'structure'),
    os.path.join(PROJECT_ROOT, 'structure', 'aggregation', 'ic_return'),
    os.path.join(PROJECT_ROOT, 'crack'),
    os.path.join(PROJECT_ROOT, 'trend'),
]
for _path in _paths_to_add:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Orchestrator submodules
from orchestrator.state_machine import StateMachine
from orchestrator.data_updater import DataUpdater
from orchestrator.cli_formatter import CLIFormatter, make_bar
from orchestrator.explanation import ExplanationBuilder

# Re-export display-name dicts for backward compatibility (used by dashboard_app.py)
from orchestrator.explanation import FACTOR_NAMES, MODULE_NAMES  # noqa: F401


class SystemOrchestrator:
    """三层系统整合器 — thin wrapper over orchestrator/ submodules."""

    def __init__(self, use_lagged: bool = True, verbose: bool = True):
        self.use_lagged = use_lagged
        self.verbose = verbose
        self.project_root = PROJECT_ROOT

        # Delegates
        self._state_machine = StateMachine()
        self._data_updater = DataUpdater(PROJECT_ROOT)
        self._cli_formatter = CLIFormatter()

        # Layer output caches
        self._structure_output: Optional[dict] = None
        self._crack_output: Optional[dict] = None
        self._trend_output: Optional[dict] = None

    # =========================================================================
    # Data Update — delegated to DataUpdater
    # =========================================================================

    def update_all_data(self, force: bool = False) -> dict:
        """Update all three-layer data."""
        return self._data_updater.update_all(force=force)

    def update_structure_data(self, force: bool = False) -> dict:
        """Update Structure layer data (FRED API)."""
        return self._data_updater.update_structure_data(force=force)

    def update_trend_data(self) -> dict:
        """Update Trend layer data (Yahoo Finance / FRED)."""
        return self._data_updater.update_trend_data()

    # =========================================================================
    # Structure Layer
    # =========================================================================

    def compute_structure_output(self) -> dict:
        """
        Compute Structure layer output (0.2A schema).

        Returns:
            dict: fuel_score, fuel_signal, fuel_components, risk_budget, etc.
        """
        if self._structure_output is not None:
            return self._structure_output

        try:
            from data.loader import DataLoader
            from utils.transforms import apply_transforms
            from config import FUEL_WEIGHTS_IC

            loader = DataLoader()
            factor_df = loader.load_structure_factors(use_lagged=self.use_lagged)
            if factor_df is None or len(factor_df) == 0:
                return self._empty_structure_output()

            fuel_df = apply_transforms(factor_df, verbose=False)

            weights = {
                'V1': 0.122,
                'V4': 0.046,
                'V5': 0.313,
                'V7': 0.142,
                'V8': 0.377,
            }

            fuel_score = 0.0
            components = {}
            total_weight = 0.0
            latest_dates = {}

            for factor, weight in weights.items():
                col = f'{factor}_fuel'
                if col not in fuel_df.columns:
                    continue
                factor_data = fuel_df[col].dropna()
                if len(factor_data) == 0:
                    continue

                latest_idx = factor_data.index.max()
                value = factor_data.loc[latest_idx]
                contribution = weight * value
                fuel_score += contribution
                total_weight += weight
                latest_dates[factor] = latest_idx

                components[factor] = {
                    'value': float(value),
                    'weight': weight,
                    'contribution': float(contribution),
                    'name': FACTOR_NAMES.get(factor, factor),
                    'date': latest_idx.strftime('%Y-%m-%d') if hasattr(latest_idx, 'strftime') else str(latest_idx),
                }

            if total_weight == 0:
                return self._empty_structure_output()

            report_date = max(latest_dates.values()) if latest_dates else datetime.now()
            if total_weight > 0:
                fuel_score = fuel_score / total_weight

            fuel_signal = self._get_fuel_signal(fuel_score)
            risk_budget = np.clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)

            dominant = max(components.items(), key=lambda x: x[1]['contribution']) if components else (None, {})
            notes = f"{FACTOR_NAMES.get(dominant[0], dominant[0])} 主导" if dominant[0] else "无数据"

            self._structure_output = {
                'date': report_date.strftime('%Y-%m-%d') if hasattr(report_date, 'strftime') else str(report_date),
                'fuel_score': float(fuel_score),
                'fuel_signal': fuel_signal,
                'fuel_components': components,
                'risk_budget': float(risk_budget),
                'notes': notes,
            }
            return self._structure_output

        except Exception as e:
            if self.verbose:
                print(f"  [Structure] Error: {e}")
            return self._empty_structure_output()

    @staticmethod
    def _empty_structure_output() -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'fuel_score': 50.0,
            'fuel_signal': 'NEUTRAL',
            'fuel_components': {},
            'risk_budget': 0.75,
            'notes': 'No data',
        }

    @staticmethod
    def _get_fuel_signal(fuel_score: float) -> str:
        if fuel_score >= 80:
            return 'EXTREME_HIGH'
        elif fuel_score >= 60:
            return 'HIGH'
        elif fuel_score >= 40:
            return 'NEUTRAL'
        elif fuel_score >= 20:
            return 'LOW'
        else:
            return 'EXTREME_LOW'

    # =========================================================================
    # Crack Layer
    # =========================================================================

    def compute_crack_output(self) -> dict:
        """
        Compute Crack layer output (0.2B schema).

        Returns:
            dict: crack_score, crack_state, crack_components, dominant_crack
        """
        if self._crack_output is not None:
            return self._crack_output

        try:
            from core.crack_score import CrackScore

            crack = CrackScore()
            result = crack.compute()

            components = {}
            dominant = None
            max_contrib = 0

            for factor, info in result.get('factor_breakdown', {}).items():
                signal = info.get('delta_z', info.get('signal', 0))
                weight = info.get('weight', 0)
                contribution = info.get('contribution', max(0, signal) * weight)
                components[factor] = {
                    'signal': float(signal),
                    'weight': float(weight),
                    'contribution': float(contribution),
                    'name': FACTOR_NAMES.get(factor, info.get('label', factor)),
                }
                if contribution > max_contrib:
                    max_contrib = contribution
                    dominant = factor

            self._crack_output = {
                'date': str(result.get('date', datetime.now().strftime('%Y-%m-%d'))),
                'crack_score': float(result.get('crack_score', 0)),
                'crack_state': result.get('state', 'STABLE'),
                'crack_components': components,
                'dominant_crack': dominant,
            }
            return self._crack_output

        except Exception as e:
            if self.verbose:
                print(f"  [Crack] Error: {e}")
            return self._empty_crack_output()

    @staticmethod
    def _empty_crack_output() -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'crack_score': 0.0,
            'crack_state': 'STABLE',
            'crack_components': {},
            'dominant_crack': None,
        }

    # =========================================================================
    # Trend Layer
    # =========================================================================

    def compute_trend_output(self) -> dict:
        """
        Compute Trend layer output (0.2C schema).

        Returns:
            dict: trend_heat, trend_state, data_quality, module_heat, etc.
        """
        if self._trend_output is not None:
            return self._trend_output

        try:
            from trend_score.trend_score import TrendScore

            ts = TrendScore()
            result = ts.compute_latest()

            module_heat = {}
            for mod_name, mod_state in result.get('module_states', {}).items():
                module_heat[mod_name] = float(mod_state.get('heat_score', 0))

            data_quality = result.get('data_quality', {
                'coverage_modules': 0,
                'quality_level': 'NONE',
                'confidence': 0.0,
                'is_trustworthy': False,
            })

            self._trend_output = {
                'date': result['date'].strftime('%Y-%m-%d') if hasattr(result.get('date'), 'strftime') else str(result.get('date', '')),
                'trend_heat': float(result.get('trend_heat_score', 0) or 0),
                'trend_state': result.get('trend_state', 'INSUFFICIENT_DATA'),
                'data_quality': data_quality,
                'module_heat': module_heat,
                'factor_intensity': {},
                'dominant_module': result.get('trigger_flags', {}).get('dominant_module'),
            }
            return self._trend_output

        except Exception as e:
            if self.verbose:
                print(f"  [Trend] Error: {e}")
            return self._empty_trend_output()

    @staticmethod
    def _empty_trend_output() -> dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trend_heat': 0.0,
            'trend_state': 'INSUFFICIENT_DATA',
            'data_quality': {
                'coverage_modules': 0,
                'quality_level': 'NONE',
                'confidence': 0.0,
                'is_trustworthy': False,
            },
            'module_heat': {},
            'factor_intensity': {},
            'dominant_module': None,
        }

    # =========================================================================
    # Portfolio Action — v2 (primary), v1 removed
    # =========================================================================

    def compute_portfolio_action_v2(self, use_hysteresis: bool = False) -> dict:
        """
        v2 rule-engine portfolio action output.

        Delegates to StateMachine after computing layer outputs.
        """
        structure = self.compute_structure_output()
        crack = self.compute_crack_output()
        trend = self.compute_trend_output()
        return self._state_machine.compute_portfolio_action(
            structure, crack, trend, use_hysteresis=use_hysteresis,
        )

    # Backward-compatible alias — compute_portfolio_action now uses v2
    def compute_portfolio_action(self) -> dict:
        """Compute portfolio action (delegates to v2 engine)."""
        return self.compute_portfolio_action_v2()

    # =========================================================================
    # CLI Dashboard — delegated to CLIFormatter
    # =========================================================================

    def print_dashboard_v2(self) -> None:
        """Print v2 CLI dashboard."""
        result = self.compute_portfolio_action_v2()
        self._cli_formatter.print_dashboard_v2(result)

    # print_dashboard now uses v2
    def print_dashboard(self) -> None:
        """Print CLI dashboard (v2)."""
        self.print_dashboard_v2()

    # =========================================================================
    # Helper — kept for backward compat (used internally & by subclasses)
    # =========================================================================

    @staticmethod
    def _make_bar(value: float, max_val: float, width: int = 10) -> str:
        """Generate a text progress bar."""
        return make_bar(value, max_val, width)

    # Delegated state-machine helpers (backward compat)
    def _get_fuel_state(self, fuel_score: float) -> str:
        return self._state_machine.get_fuel_state(fuel_score)

    def _apply_rules(self, fuel_state, crack_state, trend_state, trend_quality):
        return self._state_machine.apply_rules(fuel_state, crack_state, trend_state, trend_quality)

    def _compute_risk_budget_v2(self, fuel_score, system_state, crack_state, trend_state, trend_quality):
        return self._state_machine.compute_risk_budget(fuel_score, system_state, crack_state, trend_state, trend_quality)

    # =========================================================================
    # History
    # =========================================================================

    def compute_history(
        self,
        start_date: str = '2004-01-01',
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        Compute historical data for charting.

        Returns:
            DataFrame with trend_heat, trend_state per date.
        """
        results = []
        try:
            from trend_score.trend_score import TrendScore
            ts = TrendScore()
            trend_history = ts.compute_history(start_date=start_date, end_date=end_date, freq='D')

            for idx, row in trend_history.iterrows():
                results.append({
                    'date': idx,
                    'trend_heat': row.get('trend_heat_score', np.nan),
                    'trend_state': row.get('trend_state', 'UNKNOWN'),
                })

            df = pd.DataFrame(results)
            df.set_index('date', inplace=True)
            return df

        except Exception as e:
            if self.verbose:
                print(f"  [History] Error: {e}")
            return pd.DataFrame()

    # =========================================================================
    # JSON Export
    # =========================================================================

    def export_json(self, filepath: str) -> None:
        """Export JSON report."""
        result = self.compute_portfolio_action()

        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Timestamp):
                return obj.strftime('%Y-%m-%d')
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        result = convert(result)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Exported to: {filepath}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Indicator System Orchestrator')
    parser.add_argument('--update', action='store_true', help='Update data before showing dashboard')
    parser.add_argument('--update-only', action='store_true', help='Only update data, do not show dashboard')
    parser.add_argument('--json', type=str, help='Export to JSON file')
    parser.add_argument('--raw', action='store_true', help='Use raw data instead of lagged')

    args = parser.parse_args()

    orch = SystemOrchestrator(use_lagged=not args.raw)

    if args.update or args.update_only:
        orch.update_all_data()

    if args.update_only:
        return

    if args.json:
        orch.export_json(args.json)
    else:
        orch.print_dashboard()


if __name__ == '__main__':
    main()
