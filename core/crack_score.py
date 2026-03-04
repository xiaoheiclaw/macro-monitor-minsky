"""
CrackScore Module
=================

Crack Layer: Captures marginal deterioration and stress signals.

Unlike FuelScore (level), CrackScore tracks rate of change (ΔZ).
High CrackScore = rapid deterioration = system approaching breaking point.

States:
- STABLE: < 0.3σ - Normal monitoring
- EARLY_CRACK: 0.3-0.5σ - Reduce risk, increase monitoring
- WIDENING_CRACK: 0.5-1.0σ - Defensive: reduce position + hedge
- BREAKING: > 1.0σ - Crisis mode

Usage:
    from core import CrackScore

    crack = CrackScore()
    result = crack.compute()
    history = crack.compute_history('2020-01-01', '2024-12-31')
"""

import logging
from typing import Dict, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

from config import CRACK_CONFIG


class CrackScore:
    """
    CrackScore calculator for tracking system deterioration.

    Measures ΔZ (change in Z-score) for key vulnerability factors,
    weighted by their predictive power (AUC/IC validated).
    """

    def __init__(self, loader=None, zscore_window: int = 96):
        """
        Initialize CrackScore calculator.

        Args:
            loader: DataLoader instance
            zscore_window: Window for Z-score calculation (months)
        """
        if loader is None:
            from data.loader import DataLoader
            loader = DataLoader()

        self.loader = loader
        self.zscore_window = zscore_window

        # Cache
        self._factor_df: Optional[pd.DataFrame] = None
        self._crack_results: Optional[Dict] = None

    def _load_factors(self) -> pd.DataFrame:
        """Load factor data."""
        if self._factor_df is None:
            self._factor_df = self.loader.load_structure_factors(use_lagged=True)
        return self._factor_df

    def _compute_rolling_zscore(self, series: pd.Series) -> pd.Series:
        """Compute rolling Z-score."""
        window = self.zscore_window
        min_periods = max(24, window // 2)

        rolling_mean = series.rolling(window=window, min_periods=min_periods).mean()
        rolling_std = series.rolling(window=window, min_periods=min_periods).std()

        return (series - rolling_mean) / rolling_std

    def _compute_delta_zscore(self, series: pd.Series, delta_window: int) -> pd.Series:
        """Compute change in Z-score over delta_window."""
        zscore = self._compute_rolling_zscore(series)
        return zscore - zscore.shift(delta_window)

    def _compute_crack_signal(self, factor_name: str, series: pd.Series) -> pd.DataFrame:
        """
        Compute crack signal for a single factor.

        Returns DataFrame with: zscore, delta_z, adjusted_signal, crack_intensity, crack_score
        """
        config = CRACK_CONFIG['delta_window']
        thresholds = CRACK_CONFIG['thresholds']

        delta_window = config.get(factor_name, 4) * 3  # Convert quarters to months

        zscore = self._compute_rolling_zscore(series)
        delta_z = self._compute_delta_zscore(series, delta_window)

        # Factor-specific direction (from original crack_score.py)
        directions = {
            'V1': 1,   # ST Debt: increase is bad
            'V2': 1,   # Uninsured deposits: increase is bad
            'V4': -1,  # ICR: decrease is bad
            'V5': 1,   # TDSP: increase is bad
            'V7': 1,   # CAPE: increase is bad
            'V8': 1,   # Margin: increase is bad
        }
        direction = directions.get(factor_name, 1)
        adjusted_signal = delta_z * direction

        # Compute intensity (continuous 0-1)
        yellow = thresholds['EARLY_CRACK']
        red = thresholds['WIDENING_CRACK']

        def intensity_func(x):
            if pd.isna(x):
                return np.nan
            if x <= yellow:
                return 0.0
            elif x >= red:
                return 1.0
            else:
                return (x - yellow) / (red - yellow)

        crack_intensity = adjusted_signal.apply(intensity_func)

        # Discrete score (0/1/2)
        crack_score = pd.Series(index=series.index, dtype=float)
        crack_score[:] = 0
        crack_score[adjusted_signal > yellow] = 1
        crack_score[adjusted_signal > red] = 2

        return pd.DataFrame({
            'zscore': zscore,
            'delta_z': delta_z,
            'adjusted_signal': adjusted_signal,
            'crack_intensity': crack_intensity,
            'crack_score': crack_score,
        })

    def _compute_all_signals(self) -> Dict:
        """Compute crack signals for all factors."""
        if self._crack_results is not None:
            return self._crack_results

        factor_df = self._load_factors()
        results = {}

        # Only compute for factors in CRACK_CONFIG weights
        crack_factors = list(CRACK_CONFIG['weights'].keys())

        for factor_name in crack_factors:
            if factor_name not in factor_df.columns:
                continue

            series = factor_df[factor_name].dropna()
            if len(series) < 60:
                continue

            results[factor_name] = self._compute_crack_signal(factor_name, series)

        self._crack_results = results
        return results

    def _compute_total_score(self, crack_results: Dict) -> pd.Series:
        """
        Compute weighted total CrackScore.

        Formula: CrackScore = Σ(w_i × max(0, adjusted_signal_i))
        """
        weights = CRACK_CONFIG['weights']

        # Get common index
        all_indices = None
        for factor_name, df in crack_results.items():
            if all_indices is None:
                all_indices = df.index
            else:
                all_indices = all_indices.union(df.index)

        if all_indices is None:
            return pd.Series(dtype=float)

        all_indices = all_indices.sort_values()

        # Build signal matrix
        signal_matrix = pd.DataFrame(index=all_indices)
        valid_weights = {}

        for factor_name, df in crack_results.items():
            weight = weights.get(factor_name, 0)
            if weight <= 0:
                continue

            signal = df['adjusted_signal'].reindex(all_indices).ffill()
            signal_matrix[factor_name] = signal
            valid_weights[factor_name] = weight

        # Compute weighted score
        result = pd.Series(index=all_indices, dtype=float)
        result[:] = 0.0

        for idx in all_indices:
            row = signal_matrix.loc[idx]
            available = row.dropna().index.tolist()

            if len(available) == 0:
                result[idx] = np.nan
                continue

            # Normalize weights for available factors
            avail_weights = {f: valid_weights[f] for f in available if f in valid_weights}
            total_weight = sum(avail_weights.values())

            if total_weight < 0.001:
                result[idx] = 0.0
                continue

            score = 0.0
            for f in available:
                if f in avail_weights:
                    norm_weight = avail_weights[f] / total_weight
                    factor_contrib = max(0, row[f])  # Truncate negative
                    score += norm_weight * factor_contrib

            result[idx] = score

        return result

    @staticmethod
    def _get_state(score: float) -> str:
        """Convert score to state string."""
        thresholds = CRACK_CONFIG['thresholds']

        if pd.isna(score):
            return 'UNKNOWN'
        elif score < thresholds['STABLE']:
            return 'STABLE'
        elif score < thresholds['EARLY_CRACK']:
            return 'EARLY_CRACK'
        elif score < thresholds['WIDENING_CRACK']:
            return 'WIDENING_CRACK'
        else:
            return 'BREAKING'

    def compute(self) -> Dict:
        """
        Compute current CrackScore.

        Returns:
            {
                'date': datetime,
                'crack_score': float (σ),
                'state': str,
                'factor_breakdown': dict,
            }
        """
        crack_results = self._compute_all_signals()
        total_score = self._compute_total_score(crack_results)

        latest_score = total_score.dropna().iloc[-1] if len(total_score.dropna()) > 0 else np.nan
        latest_date = total_score.dropna().index[-1] if len(total_score.dropna()) > 0 else None

        # Factor breakdown
        breakdown = {}
        weights = CRACK_CONFIG['weights']
        factor_labels = {
            'V1': 'Duration (ST Debt)',
            'V2': 'Bank-run (Uninsured)',
            'V4': 'Credit (ICR)',
            'V5': 'Household (TDSP)',
            'V7': 'Valuation (CAPE)',
            'V8': 'Leverage (Margin)',
        }

        for factor_name, df in crack_results.items():
            if len(df['adjusted_signal'].dropna()) > 0:
                signal = df['adjusted_signal'].dropna().iloc[-1]
                weight = weights.get(factor_name, 0)
                contribution = weight * max(0, signal)

                breakdown[factor_name] = {
                    'label': factor_labels.get(factor_name, factor_name),
                    'delta_z': signal,
                    'weight': weight,
                    'contribution': contribution,
                }

        return {
            'date': latest_date,
            'crack_score': latest_score,
            'state': self._get_state(latest_score),
            'factor_breakdown': breakdown,
        }

    def compute_history(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Compute historical CrackScore time series.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with columns: crack_score, state
        """
        crack_results = self._compute_all_signals()
        total_score = self._compute_total_score(crack_results)

        # Filter date range
        if start_date:
            total_score = total_score[total_score.index >= pd.Timestamp(start_date)]
        if end_date:
            total_score = total_score[total_score.index <= pd.Timestamp(end_date)]

        result = pd.DataFrame({
            'crack_score': total_score,
            'state': total_score.apply(self._get_state),
        })

        # Add factor columns
        for factor_name, df in crack_results.items():
            result[f'{factor_name}_delta_z'] = df['adjusted_signal'].reindex(result.index)

        return result

    def clear_cache(self):
        """Clear cached data."""
        self._factor_df = None
        self._crack_results = None


# CLI interface
if __name__ == '__main__':
    print("Testing CrackScore...")

    crack = CrackScore()
    result = crack.compute()

    print(f"\nDate: {result['date']}")
    print(f"CrackScore: {result['crack_score']:.2f}σ")
    print(f"State: {result['state']}")

    print("\n[Factor Breakdown]")
    for factor, data in result['factor_breakdown'].items():
        status = '🔴' if data['delta_z'] > 1.0 else '🟡' if data['delta_z'] > 0.5 else '🟢'
        print(f"  {data['label']}: ΔZ={data['delta_z']:.2f}σ (w={data['weight']:.1%}) {status}")
