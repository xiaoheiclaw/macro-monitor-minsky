"""
FuelScore Module
================

Structure Layer: Slow-moving risk accumulation indicators.

Factors:
- V1: ST Debt Ratio
- V2: Uninsured Deposits
- V4: Interest Coverage Ratio
- V5: TDSP (Debt Service)
- V7: CAPE
- V8: Margin Debt

Weight Schemes:
- IC (Return): Based on correlation with 12M forward returns
- AUC (MDD): Based on predicting 12M MDD < -20%

Usage:
    from core import FuelScore

    fuel = FuelScore(weight_scheme='ic')
    result = fuel.compute()
    history = fuel.compute_history('2020-01-01', '2024-12-31')
"""

import logging
from typing import Dict, Optional
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

from config import (
    FUEL_WEIGHTS_IC,
    FUEL_WEIGHTS_AUC,
    SYSTEM_THRESHOLDS,
)


class FuelScore:
    """
    FuelScore calculator with support for multiple weight schemes.

    Parameters:
    -----------
    loader : DataLoader
        Data loader instance (optional, will create if not provided)
    weight_scheme : str
        'ic' for Return IC weights, 'auc' for MDD AUC weights
    """

    def __init__(self, loader=None, weight_scheme: str = 'ic'):
        if loader is None:
            from data.loader import DataLoader
            loader = DataLoader()

        self.loader = loader
        self.weight_scheme = weight_scheme

        # Select weights based on scheme
        if weight_scheme == 'auc':
            self.weights = FUEL_WEIGHTS_AUC.copy()
        else:
            self.weights = FUEL_WEIGHTS_IC.copy()

        # Cache
        self._factor_fuel: Optional[pd.DataFrame] = None

    def _load_transformed_factors(self) -> pd.DataFrame:
        """Load and transform factors."""
        if self._factor_fuel is None:
            from utils.transforms import apply_transforms

            factors = self.loader.load_structure_factors(use_lagged=True)
            self._factor_fuel = apply_transforms(factors, verbose=False)

        return self._factor_fuel

    @staticmethod
    def _weighted_score(factor_values: pd.Series, weights: Dict[str, float]) -> float:
        """
        Compute weighted score from factor values with given weights.

        Args:
            factor_values: Series with factor fuel values (e.g., {'V1_fuel': 45, ...})
            weights: Dict mapping column names to weights

        Returns:
            Weighted average score (0-100), or np.nan if no valid data
        """
        weighted_sum = 0.0
        weight_sum = 0.0

        for col, weight in weights.items():
            if weight <= 0 or col not in factor_values.index:
                continue
            val = factor_values[col]
            if not pd.isna(val):
                weighted_sum += weight * val
                weight_sum += weight

        return weighted_sum / weight_sum if weight_sum > 0 else np.nan

    def _compute_score(self, factor_values: pd.Series) -> float:
        """Compute weighted FuelScore using instance weights."""
        return self._weighted_score(factor_values, self.weights)

    def _get_signal(self, score: float) -> str:
        """Convert score to signal string."""
        thresholds = SYSTEM_THRESHOLDS['fuel_score']

        if score >= thresholds['EXTREME']:
            return 'EXTREME HIGH'
        elif score >= thresholds['HIGH']:
            return 'HIGH'
        elif score >= thresholds['NEUTRAL']:
            return 'NEUTRAL'
        elif score >= thresholds['LOW']:
            return 'LOW'
        else:
            return 'EXTREME LOW'

    def compute(self) -> Dict:
        """
        Compute current FuelScore.

        Returns:
            {
                'date': datetime,
                'fuel_score': float,
                'signal': str,
                'factor_breakdown': dict,
                'weight_scheme': str,
            }
        """
        factor_fuel = self._load_transformed_factors()

        # Get latest valid values
        latest_values = factor_fuel.ffill().iloc[-1]
        score = self._compute_score(latest_values)

        # Factor breakdown
        breakdown = {}
        for col in factor_fuel.columns:
            factor_name = col.replace('_fuel', '')
            breakdown[factor_name] = {
                'fuel': latest_values.get(col, np.nan),
                'weight': self.weights.get(col, 0),
            }

        return {
            'date': factor_fuel.index[-1],
            'fuel_score': score,
            'signal': self._get_signal(score),
            'factor_breakdown': breakdown,
            'weight_scheme': self.weight_scheme,
        }

    def compute_history(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Compute historical FuelScore time series.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with columns: fuel_score, signal, and factor values
        """
        factor_fuel = self._load_transformed_factors()

        # Filter date range
        if start_date:
            factor_fuel = factor_fuel[factor_fuel.index >= pd.Timestamp(start_date)]
        if end_date:
            factor_fuel = factor_fuel[factor_fuel.index <= pd.Timestamp(end_date)]

        # Forward fill for calculation
        factor_filled = factor_fuel.ffill()

        # Compute score for each date
        scores = []
        for idx in factor_filled.index:
            score = self._compute_score(factor_filled.loc[idx])
            scores.append({
                'date': idx,
                'fuel_score': score,
                'signal': self._get_signal(score) if not pd.isna(score) else 'N/A',
            })

        result = pd.DataFrame(scores)
        if len(result) > 0:
            result = result.set_index('date')

            # Add factor columns
            for col in factor_fuel.columns:
                result[col] = factor_filled[col]

        return result

    def compute_both_schemes(self) -> Dict:
        """
        Compute FuelScore using both weight schemes for comparison.

        Returns:
            {
                'date': datetime,
                'ic': {'fuel_score': x, 'signal': y},
                'auc': {'fuel_score': x, 'signal': y},
            }
        """
        factor_fuel = self._load_transformed_factors()
        latest_values = factor_fuel.ffill().iloc[-1]

        score_ic = self._weighted_score(latest_values, FUEL_WEIGHTS_IC)
        score_auc = self._weighted_score(latest_values, FUEL_WEIGHTS_AUC)

        return {
            'date': factor_fuel.index[-1],
            'ic': {
                'fuel_score': score_ic,
                'signal': self._get_signal(score_ic),
            },
            'auc': {
                'fuel_score': score_auc,
                'signal': self._get_signal(score_auc),
            },
        }

    def compute_history_both_schemes(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Compute historical FuelScore with both weight schemes.

        Returns:
            DataFrame with columns: fuel_score_ic, fuel_score_auc
        """
        factor_fuel = self._load_transformed_factors()

        # Filter date range
        if start_date:
            factor_fuel = factor_fuel[factor_fuel.index >= pd.Timestamp(start_date)]
        if end_date:
            factor_fuel = factor_fuel[factor_fuel.index <= pd.Timestamp(end_date)]

        factor_filled = factor_fuel.ffill()

        results = []
        for idx in factor_filled.index:
            row = factor_filled.loc[idx]
            results.append({
                'date': idx,
                'fuel_score_ic': self._weighted_score(row, FUEL_WEIGHTS_IC),
                'fuel_score_auc': self._weighted_score(row, FUEL_WEIGHTS_AUC),
            })

        result = pd.DataFrame(results)
        if len(result) > 0:
            result = result.set_index('date')

        return result

    def clear_cache(self):
        """Clear cached data."""
        self._factor_fuel = None


# CLI interface
if __name__ == '__main__':
    print("Testing FuelScore...")

    fuel = FuelScore(weight_scheme='ic')
    result = fuel.compute()

    print(f"\nDate: {result['date']}")
    print(f"Fuel Score (IC): {result['fuel_score']:.1f}")
    print(f"Signal: {result['signal']}")

    print("\n[Factor Breakdown]")
    for factor, data in result['factor_breakdown'].items():
        if data['weight'] > 0:
            print(f"  {factor}: {data['fuel']:.1f} (weight: {data['weight']:.1%})")

    # Compare both schemes
    print("\n[Both Schemes]")
    both = fuel.compute_both_schemes()
    print(f"  IC:  {both['ic']['fuel_score']:.1f} ({both['ic']['signal']})")
    print(f"  AUC: {both['auc']['fuel_score']:.1f} ({both['auc']['signal']})")
