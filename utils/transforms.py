"""
Transform Functions
===================

Data transformation utilities for converting raw factors to Fuel Scores.

Supported transforms:
- Rolling Percentile: Maps value to 0-100 percentile within rolling window
- Rolling Z-score: Standardizes value using rolling mean/std
- Z-score to Fuel: Converts Z-score to 0-100 scale
- U-shape: |Percentile - 50| * 2, for bidirectional signals (both extremes = risk)

Usage:
    from utils.transforms import apply_transforms

    factor_df = loader.load_structure_factors()
    fuel_df = apply_transforms(factor_df)
"""

import os
import sys
from typing import Dict

import pandas as pd
import numpy as np

# Ensure parent directory is in path for relative imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import FACTOR_TRANSFORM


def compute_rolling_percentile(
    series: pd.Series,
    window: int,
    min_periods: int = None
) -> pd.Series:
    """
    Compute rolling percentile (0-100).

    For each point, compute what percentile the current value is
    within the rolling window of historical values.

    Args:
        series: Input series
        window: Rolling window size (months)
        min_periods: Minimum periods required (default: max(24, window//2))

    Returns:
        Percentile series (0-100)
    """
    if min_periods is None:
        min_periods = max(24, window // 2)

    result = pd.Series(index=series.index, dtype=float)

    for i in range(len(series)):
        if i < min_periods - 1:
            continue

        start_idx = max(0, i - window + 1)
        historical = series.iloc[start_idx:i + 1].dropna()

        if len(historical) < min_periods:
            continue

        current = series.iloc[i]
        if pd.isna(current):
            continue

        # Percentile: what fraction of values are below current
        pctl = (historical < current).sum() / len(historical) * 100
        result.iloc[i] = pctl

    return result


def compute_rolling_zscore(
    series: pd.Series,
    window: int,
    min_periods: int = None
) -> pd.Series:
    """
    Compute rolling Z-score.

    Standardizes each value using the rolling mean and standard deviation.

    Args:
        series: Input series
        window: Rolling window size (months)
        min_periods: Minimum periods required (default: max(24, window//2))

    Returns:
        Z-score series
    """
    if min_periods is None:
        min_periods = max(24, window // 2)

    rolling_mean = series.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()

    zscore = (series - rolling_mean) / rolling_std
    return zscore


def zscore_to_fuel(zscore: pd.Series) -> pd.Series:
    """
    Convert Z-score to Fuel Score (0-100).

    Mapping:
        Z <= -2.0  →  0
        Z >= +2.0  →  100
        Linear interpolation in between

    This makes Z=0 → Fuel=50 (neutral).

    Args:
        zscore: Z-score series

    Returns:
        Fuel score series (0-100)
    """
    # Linear mapping: Z ∈ [-2, 2] → Fuel ∈ [0, 100]
    fuel = (zscore + 2) / 4 * 100
    fuel = fuel.clip(0, 100)
    return fuel


def compute_credit_gap(
    series: pd.Series,
    window: int,
    min_periods: int = None
) -> pd.Series:
    """
    Compute Credit Gap Percentile transform for filtering long-term structural trends.

    This transform removes the long-term moving average from the series,
    then computes the percentile of the residual (gap). This preserves the
    trend-filtering benefit while maintaining a well-distributed 0-100 output.

    Formula:
        1. gap = x - MA(x, window)
        2. fuel = rolling_percentile(gap, window)

    This is useful for factors like V8 (Margin Debt) where:
    - There's a structural upward trend over decades
    - Raw Z-score or Percentile would always show "high" due to trend
    - Gap Percentile filters trend while maintaining good distribution

    Validation results (IC/AUC):
    - Gap Percentile: IC=-0.204, AUC=0.753 (balanced)
    - vs Z-score: IC=-0.427, AUC=0.718 (trend issue)
    - vs clip(0,3): IC=-0.139, AUC=0.769 (48% at 0, sparse signal)

    Args:
        series: Input series (raw factor values)
        window: Rolling window size (months) for MA and percentile
        min_periods: Minimum periods required (default: window//2)

    Returns:
        Fuel score series (0-100), where higher = more above trend
    """
    if min_periods is None:
        min_periods = window // 2

    # Step 1: Compute long-term moving average
    ma = series.rolling(window=window, min_periods=min_periods).mean()

    # Step 2: Compute gap (deviation from trend)
    gap = series - ma

    # Step 3: Compute rolling percentile of the gap
    result = pd.Series(index=gap.index, dtype=float)

    for i in range(len(gap)):
        if i < min_periods - 1:
            continue

        start_idx = max(0, i - window + 1)
        historical = gap.iloc[start_idx:i + 1].dropna()

        if len(historical) < min_periods:
            continue

        current = gap.iloc[i]
        if pd.isna(current):
            continue

        # Percentile: what fraction of values are below current
        pctl = (historical < current).sum() / len(historical) * 100
        result.iloc[i] = pctl

    return result


def compute_ushape_transform(
    series: pd.Series,
    window: int,
    min_periods: int = None
) -> pd.Series:
    """
    Compute U-shape transform for bidirectional signals.

    Maps percentile to 0-100 where BOTH extremes (very low OR very high) = high risk.
    Formula: |Percentile - 50| * 2

    This is useful for factors like V9 (CRE Lending Standards) where:
    - Very tight lending (high percentile) = immediate credit crunch risk
    - Very loose lending (low percentile) = bubble formation / delayed risk

    Mapping:
        Percentile = 0   →  Fuel = 100 (extreme low = risk)
        Percentile = 50  →  Fuel = 0   (neutral = safe)
        Percentile = 100 →  Fuel = 100 (extreme high = risk)

    Args:
        series: Input series
        window: Rolling window size (months)
        min_periods: Minimum periods required

    Returns:
        U-shape fuel score series (0-100)
    """
    # First compute percentile
    pctl = compute_rolling_percentile(series, window=window, min_periods=min_periods)

    # U-shape: distance from 50, scaled to 0-100
    # |pctl - 50| ranges from 0 to 50, multiply by 2 to get 0-100
    fuel = (pctl - 50).abs() * 2

    return fuel


def apply_transforms(
    factor_df: pd.DataFrame,
    config: Dict = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Apply factor-specific transforms to create Fuel Scores.

    Each factor has a configured transform type and window:
    - 'percentile': Rolling percentile (0-100)
    - 'zscore': Rolling Z-score converted to 0-100

    Args:
        factor_df: DataFrame with factor columns (V1, V2, etc.)
        config: Transform configuration (default: FACTOR_TRANSFORM from config.py)
        verbose: Print progress messages

    Returns:
        DataFrame with transformed columns (V1_fuel, V2_fuel, etc.)
    """
    if config is None:
        config = FACTOR_TRANSFORM

    if verbose:
        print("\n" + "=" * 60)
        print("Applying Factor-Specific Transforms")
        print("=" * 60)

    result = pd.DataFrame(index=factor_df.index)

    for col in factor_df.columns:
        # Only process factors in config
        if col not in config:
            if verbose:
                print(f"  {col}: Skipped (not in config)")
            continue

        series = factor_df[col].dropna()
        if len(series) < 60:
            if verbose:
                print(f"  {col}: Skipped (insufficient data)")
            continue

        factor_config = config[col]
        transform_type = factor_config['type']
        window = factor_config['window']
        flip = factor_config.get('flip', False)

        if transform_type == 'percentile':
            fuel = compute_rolling_percentile(series, window=window)
            if flip:
                fuel = 100 - fuel
                if verbose:
                    print(f"  {col}: Percentile({window // 12}Y) → Flipped (low=high risk)")
            else:
                if verbose:
                    print(f"  {col}: Percentile({window // 12}Y)")

        elif transform_type == 'zscore':
            zscore = compute_rolling_zscore(series, window=window)
            fuel = zscore_to_fuel(zscore)
            if flip:
                fuel = 100 - fuel
                if verbose:
                    print(f"  {col}: Z-score({window // 12}Y) → Flipped (low=high risk)")
            else:
                if verbose:
                    fuel_range = f"{fuel.dropna().min():.1f}-{fuel.dropna().max():.1f}"
                    print(f"  {col}: Z-score({window // 12}Y) → Fuel (range: {fuel_range})")

        elif transform_type == 'ushape':
            fuel = compute_ushape_transform(series, window=window)
            if verbose:
                print(f"  {col}: U-shape({window // 12}Y) → |Pctl-50|*2 (bidirectional)")

        elif transform_type == 'credit_gap':
            fuel = compute_credit_gap(series, window=window)
            if verbose:
                print(f"  {col}: Credit Gap({window // 12}Y) → filters trend, cyclical deviation only")

        else:
            if verbose:
                print(f"  {col}: Unknown transform type '{transform_type}', skipped")
            continue

        result[f'{col}_fuel'] = fuel

        if verbose:
            print(f"       Range: {fuel.dropna().min():.1f}-{fuel.dropna().max():.1f}")

    return result


def apply_single_transform(
    series: pd.Series,
    transform_type: str,
    window: int,
    flip: bool = False
) -> pd.Series:
    """
    Apply a single transform to a factor series.

    This is a lower-level function for testing different transform variants
    on a single factor.

    Args:
        series: Raw factor series
        transform_type: 'percentile', 'zscore', or 'ushape'
        window: Rolling window size (months)
        flip: If True, invert the fuel score (100 - fuel)

    Returns:
        Fuel score series (0-100)
    """
    series = series.dropna()

    if len(series) < 60:
        return pd.Series(dtype=float)

    if transform_type == 'percentile':
        fuel = compute_rolling_percentile(series, window=window)
    elif transform_type == 'zscore':
        zscore = compute_rolling_zscore(series, window=window)
        fuel = zscore_to_fuel(zscore)
    elif transform_type == 'ushape':
        fuel = compute_ushape_transform(series, window=window)
    elif transform_type == 'credit_gap':
        fuel = compute_credit_gap(series, window=window)
    else:
        raise ValueError(f"Unknown transform type: {transform_type}")

    if flip:
        fuel = 100 - fuel

    return fuel


# CLI interface for testing
if __name__ == '__main__':
    from data.loader import DataLoader

    print("Testing transforms...")

    loader = DataLoader()
    factors = loader.load_structure_factors(use_lagged=True)

    fuel_df = apply_transforms(factors)

    print(f"\nTransformed {len(fuel_df.columns)} factors")
    print(f"Date range: {fuel_df.index.min()} to {fuel_df.index.max()}")

    # Show latest values
    print("\nLatest Fuel Scores:")
    latest = fuel_df.dropna().iloc[-1]
    for col, val in latest.items():
        print(f"  {col}: {val:.1f}")
