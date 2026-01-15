"""
AUC Calculator
==============

Compute AUC (Area Under ROC Curve) for predicting forward MDD events,
by rate regime.

Usage:
    from validation.auc_calculator import compute_auc_mdd

    auc_results = compute_auc_mdd(factor, fwd_mdd, threshold, ffr)
"""

from typing import Dict
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score


def compute_auc_mdd(
    factor: pd.Series,
    fwd_mdd: pd.Series,
    threshold: float,
    ffr: pd.Series
) -> Dict:
    """
    Compute AUC for predicting MDD < threshold events.

    Args:
        factor: Factor series
        fwd_mdd: Forward MDD series (negative values)
        threshold: MDD threshold (e.g., -0.20 for -20%)
        ffr: Federal Funds Rate

    Returns:
        {
            'full': {'auc': x, 'n_events': y, 'n': z},
            'high_rate': {...},
            'low_rate': {...}
        }
    """
    # Create event indicator: MDD < threshold
    event = (fwd_mdd < threshold).astype(int)

    aligned = pd.DataFrame({
        'factor': factor,
        'event': event,
        'rate': ffr
    }).dropna()

    if len(aligned) < 30 or aligned['event'].nunique() < 2:
        return {
            'full': {'auc': np.nan, 'n_events': 0, 'n': len(aligned)},
            'high_rate': {'auc': np.nan, 'n_events': 0, 'n': 0},
            'low_rate': {'auc': np.nan, 'n_events': 0, 'n': 0}
        }

    rate_median = aligned['rate'].median()
    high_rate = aligned[aligned['rate'] >= rate_median]
    low_rate = aligned[aligned['rate'] < rate_median]

    results = {}

    # Full sample
    try:
        auc = roc_auc_score(aligned['event'], aligned['factor'])
        results['full'] = {
            'auc': auc,
            'n_events': int(aligned['event'].sum()),
            'n': len(aligned)
        }
    except ValueError as e:
        # AUC cannot be computed when only one class is present
        results['full'] = {
            'auc': np.nan,
            'n_events': int(aligned['event'].sum()),
            'n': len(aligned),
            'error': str(e)
        }

    # High rate
    if len(high_rate) >= 20 and high_rate['event'].nunique() >= 2:
        try:
            auc = roc_auc_score(high_rate['event'], high_rate['factor'])
            results['high_rate'] = {
                'auc': auc,
                'n_events': int(high_rate['event'].sum()),
                'n': len(high_rate)
            }
        except ValueError as e:
            results['high_rate'] = {
                'auc': np.nan,
                'n_events': int(high_rate['event'].sum()),
                'n': len(high_rate),
                'error': str(e)
            }
    else:
        results['high_rate'] = {
            'auc': np.nan,
            'n_events': 0,
            'n': len(high_rate)
        }

    # Low rate
    if len(low_rate) >= 20 and low_rate['event'].nunique() >= 2:
        try:
            auc = roc_auc_score(low_rate['event'], low_rate['factor'])
            results['low_rate'] = {
                'auc': auc,
                'n_events': int(low_rate['event'].sum()),
                'n': len(low_rate)
            }
        except ValueError as e:
            results['low_rate'] = {
                'auc': np.nan,
                'n_events': int(low_rate['event'].sum()),
                'n': len(low_rate),
                'error': str(e)
            }
    else:
        results['low_rate'] = {
            'auc': np.nan,
            'n_events': 0,
            'n': len(low_rate)
        }

    return results


def compute_auc_stability(
    auc_full: float,
    auc_high: float,
    auc_low: float
) -> float:
    """
    Compute AUC stability coefficient.

    AUC baseline is 0.5 (random). Uses |AUC - 0.5| as signal strength.
    AUC < 0.5 is also valid (opposite direction but predictive).

    Stability check: high_rate and low_rate AUC should be in same direction as full.

    Args:
        auc_full: Full sample AUC
        auc_high: High rate AUC
        auc_low: Low rate AUC

    Returns:
        Stability coefficient (0-1)
    """
    if pd.isna(auc_full):
        return 0.0

    if pd.isna(auc_high) or pd.isna(auc_low):
        return 0.5

    # Effective signal: |AUC - 0.5|
    eff_full = abs(auc_full - 0.5)

    if eff_full < 0.01:
        return 0.0

    # Check direction consistency
    full_direction = 1 if auc_full > 0.5 else -1
    high_direction = 1 if auc_high > 0.5 else -1
    low_direction = 1 if auc_low > 0.5 else -1

    # Same direction signal strength
    eff_high = abs(auc_high - 0.5) if high_direction == full_direction else 0
    eff_low = abs(auc_low - 0.5) if low_direction == full_direction else 0

    numerator = eff_high + eff_low
    denominator = 2 * eff_full

    return min(1.0, numerator / denominator)


def compute_forward_max_drawdown(
    prices: pd.Series,
    horizon: int = 252
) -> pd.Series:
    """
    Compute forward maximum drawdown for each date.

    Args:
        prices: Price series (daily)
        horizon: Forward horizon in trading days (252 ≈ 12 months)

    Returns:
        Forward MDD series (negative values)
    """
    result = pd.Series(index=prices.index, dtype=float)

    for i in range(len(prices) - horizon):
        window = prices.iloc[i:i + horizon + 1]
        peak = window.cummax()
        drawdown = (window - peak) / peak
        max_drawdown = drawdown.min()
        result.iloc[i] = max_drawdown

    return result
