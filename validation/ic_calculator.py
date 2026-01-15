"""
IC Calculator
=============

Compute Information Coefficient (Spearman correlation) between factors
and forward returns, by rate regime.

Usage:
    from validation.ic_calculator import compute_ic_by_rate_regime

    ic_results = compute_ic_by_rate_regime(factor, returns, ffr)
"""

from typing import Dict
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

# Minimum sample sizes for statistical validity
MIN_SAMPLES_FULL = 30        # Minimum samples for full sample IC
MIN_SAMPLES_REGIME = 20      # Minimum samples for regime-specific IC
IC_SIGNIFICANCE_THRESHOLD = 0.01  # Ignore IC values below this threshold


def compute_ic_by_rate_regime(
    factor: pd.Series,
    returns: pd.Series,
    ffr: pd.Series
) -> Dict:
    """
    Compute IC (Spearman) by rate regime.

    Args:
        factor: Factor series (monthly)
        returns: Forward return series (monthly)
        ffr: Federal Funds Rate series

    Returns:
        {
            'full': {'ic': x, 'p_value': y, 'n': z},
            'high_rate': {...},
            'low_rate': {...}
        }
    """
    aligned = pd.DataFrame({
        'factor': factor,
        'return': returns,
        'rate': ffr
    }).dropna()

    if len(aligned) < MIN_SAMPLES_FULL:
        return {
            'full': {'ic': np.nan, 'p_value': np.nan, 'n': len(aligned)},
            'high_rate': {'ic': np.nan, 'p_value': np.nan, 'n': 0},
            'low_rate': {'ic': np.nan, 'p_value': np.nan, 'n': 0}
        }

    rate_median = aligned['rate'].median()
    high_rate = aligned[aligned['rate'] >= rate_median]
    low_rate = aligned[aligned['rate'] < rate_median]

    results = {}

    # Full sample
    ic, p_value = spearmanr(aligned['factor'], aligned['return'])
    results['full'] = {'ic': ic, 'p_value': p_value, 'n': len(aligned)}

    # High rate
    if len(high_rate) >= MIN_SAMPLES_REGIME:
        ic, p_value = spearmanr(high_rate['factor'], high_rate['return'])
        results['high_rate'] = {'ic': ic, 'p_value': p_value, 'n': len(high_rate)}
    else:
        results['high_rate'] = {'ic': np.nan, 'p_value': np.nan, 'n': len(high_rate)}

    # Low rate
    if len(low_rate) >= MIN_SAMPLES_REGIME:
        ic, p_value = spearmanr(low_rate['factor'], low_rate['return'])
        results['low_rate'] = {'ic': ic, 'p_value': p_value, 'n': len(low_rate)}
    else:
        results['low_rate'] = {'ic': np.nan, 'p_value': np.nan, 'n': len(low_rate)}

    return results


def compute_stability_penalty(
    ic_full: float,
    ic_high: float,
    ic_low: float
) -> float:
    """
    Compute stability penalty coefficient.

    Formula: s = min(1, (|IC_high| + |IC_low|) / (2 * |IC_full|))

    This penalizes factors that only work in one rate regime.

    Args:
        ic_full: Full sample IC
        ic_high: High rate IC
        ic_low: Low rate IC

    Returns:
        Stability coefficient (0-1)
    """
    if pd.isna(ic_full) or abs(ic_full) < IC_SIGNIFICANCE_THRESHOLD:
        return 0.0

    if pd.isna(ic_high) or pd.isna(ic_low):
        return 0.5

    numerator = abs(ic_high) + abs(ic_low)
    denominator = 2 * abs(ic_full)

    if denominator < IC_SIGNIFICANCE_THRESHOLD:
        return 0.0

    return min(1.0, numerator / denominator)


def compute_forward_return(spx: pd.Series, horizon: int = 12) -> pd.Series:
    """
    Compute forward log returns (monthly).

    Args:
        spx: SPX series (daily or monthly)
        horizon: Forward horizon in months

    Returns:
        Forward return series
    """
    spx_monthly = spx.resample('ME').last()
    fwd_return = np.log(spx_monthly.shift(-horizon) / spx_monthly)
    return fwd_return
