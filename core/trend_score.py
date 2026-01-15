"""
TrendScore Module
=================

Trend Layer: Real-time market stress signals.

Modules:
- A: Volatility Regime (VIX, SKEW, MOVE)
- B: Funding / Liquidity (EFFR-SOFR, GCF Repo)
- C: Credit Compensation (HY Spread, IG Spread)
- D: Flow Confirmation (HYG, LQD, TLT flows)

States:
- CALM: Normal market conditions
- WATCH: Elevated monitoring
- ALERT: Risk warning
- CRITICAL: Crisis signals

Usage:
    from core import TrendScore

    trend = TrendScore()
    result = trend.compute()
    history = trend.compute_history('2020-01-01', '2024-12-31')
"""

import os
import sys
from typing import Dict, Optional

import pandas as pd
import numpy as np

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TREND_CONFIG, TREND_DATA_DIR


class TrendScore:
    """
    TrendScore calculator - wrapper for the trend/trend_score module.

    Delegates to the existing TrendScore implementation while providing
    a consistent interface with FuelScore and CrackScore.
    """

    def __init__(self, loader=None):
        """
        Initialize TrendScore calculator.

        Args:
            loader: DataLoader instance (optional)
        """
        if loader is None:
            from data.loader import DataLoader
            loader = DataLoader()

        self.loader = loader
        self._trend_score = None

    def _get_trend_score_impl(self):
        """Get the underlying TrendScore implementation."""
        if self._trend_score is None:
            # Add trend_score package to path
            trend_package_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'trend'
            )
            if trend_package_dir not in sys.path:
                sys.path.insert(0, trend_package_dir)

            # Import as package
            from trend_score.trend_score import TrendScore as TrendScoreImpl
            self._trend_score = TrendScoreImpl(data_dir=TREND_DATA_DIR)

        return self._trend_score

    def _get_state(self, heat_score: float) -> str:
        """Convert heat score to state string."""
        thresholds = TREND_CONFIG['state_thresholds']

        if pd.isna(heat_score):
            return 'UNKNOWN'
        elif heat_score < thresholds['CALM']:
            return 'CALM'
        elif heat_score < thresholds['WATCH']:
            return 'WATCH'
        elif heat_score < thresholds['ALERT']:
            return 'ALERT'
        else:
            return 'CRITICAL'

    def compute(self) -> Dict:
        """
        Compute current TrendScore.

        Returns:
            {
                'date': datetime,
                'trend_score': float (0-1),
                'state': str,
                'module_breakdown': dict,
                'data_quality': dict,
            }
        """
        impl = self._get_trend_score_impl()

        try:
            result = impl.compute_latest()
        except Exception as e:
            return {
                'date': None,
                'trend_score': np.nan,
                'state': 'NO_DATA',
                'module_breakdown': {},
                'data_quality': {'quality_level': 'NONE'},
                'error': str(e),
            }

        # Extract module breakdown
        module_breakdown = {}
        module_states = result.get('module_states', {})

        for mod_name, mod_state in module_states.items():
            module_breakdown[mod_name] = {
                'heat_score': mod_state.get('heat_score', np.nan),
                'state': mod_state.get('state', 'UNKNOWN'),
                'dominant_factor': mod_state.get('dominant_factor'),
            }

        return {
            'date': result.get('date'),
            'trend_score': result.get('trend_heat_score', np.nan),
            'state': result.get('trend_state', 'UNKNOWN'),
            'module_breakdown': module_breakdown,
            'data_quality': result.get('data_quality', {}),
            'trigger_flags': result.get('trigger_flags', {}),
        }

    def compute_history(
        self,
        start_date: str = None,
        end_date: str = None,
        freq: str = 'D'
    ) -> pd.DataFrame:
        """
        Compute historical TrendScore time series.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            freq: Frequency ('D' daily, 'W' weekly, 'ME' monthly)

        Returns:
            DataFrame with columns: trend_score, state, module_X_heat, etc.
        """
        impl = self._get_trend_score_impl()

        try:
            history = impl.compute_history(
                start_date=start_date,
                end_date=end_date,
                freq=freq
            )
        except Exception as e:
            return pd.DataFrame()

        # Rename columns for consistency
        result = pd.DataFrame(index=history.index)
        result['trend_score'] = history.get('trend_heat_score')
        result['state'] = history.get('trend_state')

        # Module columns
        for col in history.columns:
            if col.startswith('module_') and col.endswith('_heat'):
                result[col] = history[col]
            elif col.startswith('module_') and col.endswith('_state'):
                result[col] = history[col]

        # Data quality
        if 'quality_level' in history.columns:
            result['quality_level'] = history['quality_level']
        if 'confidence' in history.columns:
            result['confidence'] = history['confidence']

        return result

    def get_module_weights(self) -> Dict[str, float]:
        """Get current module weights."""
        return TREND_CONFIG['module_weights'].copy()

    def clear_cache(self):
        """Clear cached data."""
        if self._trend_score is not None:
            self._trend_score._data_cache.clear()


# CLI interface
if __name__ == '__main__':
    print("Testing TrendScore...")

    trend = TrendScore()
    result = trend.compute()

    print(f"\nDate: {result['date']}")
    print(f"Trend Score: {result['trend_score']:.2f}")
    print(f"State: {result['state']}")

    dq = result.get('data_quality', {})
    print(f"Quality: {dq.get('quality_level', 'N/A')} ({dq.get('coverage_modules', 0)} modules)")

    print("\n[Module Breakdown]")
    for mod_name, mod_data in result['module_breakdown'].items():
        heat = mod_data.get('heat_score', np.nan)
        state = mod_data.get('state', 'UNKNOWN')
        print(f"  Module {mod_name}: {heat:.2f} ({state})")
