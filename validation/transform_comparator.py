"""
Transform Comparator
====================

Systematically compare different transform configurations for each factor
to find the optimal transform method.

Tests:
- Percentile (5Y, 10Y)
- Z-score (5Y, 10Y)

Metrics:
- IC (Spearman correlation with 12M forward returns)
- AUC (ROC AUC for MDD < -20% prediction)
- Stability (cross-rate-regime consistency)

Usage:
    python -m validation.transform_comparator

    # Or in Python:
    from validation.transform_comparator import TransformComparator
    comparator = TransformComparator()
    report = comparator.generate_report()
"""

import os
import sys
from typing import Dict, List
from datetime import datetime

import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import DataLoader
from utils.transforms import apply_single_transform
from validation.ic_calculator import (
    compute_ic_by_rate_regime,
    compute_stability_penalty,
    compute_forward_return
)
from validation.auc_calculator import (
    compute_auc_mdd,
    compute_auc_stability,
    compute_forward_max_drawdown
)
from config import FACTOR_TRANSFORM


# Factor names for display
FACTOR_NAMES = {
    'V1': 'ST Debt Ratio',
    'V4': 'Interest Coverage (ICR)',
    'V5': 'TDSP (Debt Service)',
    'V7': 'Shiller PE (CAPE)',
    'V8': 'Margin Debt Ratio',
}

# Factors that require flip (low value = high risk)
FLIP_FACTORS = ['V4']


class TransformComparator:
    """
    Compare different transform configurations for each factor.

    Transform variants tested:
    - pctl_5y: 5-year rolling percentile
    - pctl_10y: 10-year rolling percentile
    - zscore_5y: 5-year rolling Z-score → Fuel
    - zscore_10y: 10-year rolling Z-score → Fuel
    """

    TRANSFORM_VARIANTS = {
        'pctl_5y': {'type': 'percentile', 'window': 60},
        'pctl_10y': {'type': 'percentile', 'window': 120},
        'zscore_5y': {'type': 'zscore', 'window': 60},
        'zscore_10y': {'type': 'zscore', 'window': 120},
    }

    def __init__(self, loader: DataLoader = None, factors: List[str] = None):
        """
        Initialize comparator.

        Args:
            loader: DataLoader instance (creates one if not provided)
            factors: List of factors to test (default: V1, V4, V5, V7, V8)
        """
        if loader is None:
            loader = DataLoader()
        self.loader = loader

        if factors is None:
            factors = ['V1', 'V4', 'V5', 'V7', 'V8']
        self.factors = factors

        # Load data
        self._load_data()

    def _load_data(self):
        """Load all required data."""
        print("Loading data for transform comparison...")

        # Load raw factors (without transform)
        self.raw_factors = self.loader.load_structure_factors(use_lagged=True)

        # Load SPX for return calculation
        spx = self.loader.load_spx()

        # Compute 12M forward returns (monthly)
        self.fwd_returns = compute_forward_return(spx, horizon=12)

        # Compute 12M forward MDD (daily → monthly)
        fwd_mdd_daily = compute_forward_max_drawdown(spx, horizon=252)
        self.fwd_mdd = fwd_mdd_daily.resample('ME').last()

        # Load Fed Funds Rate for regime split
        # Resample to month-end to align with factors and returns
        ffr_raw = self.loader.load_fed_funds()
        self.ffr = ffr_raw.resample('ME').last().ffill()

        print(f"  Loaded {len(self.raw_factors.columns)} factors")
        print(f"  Forward returns: {len(self.fwd_returns.dropna())} months")
        print(f"  Forward MDD: {len(self.fwd_mdd.dropna())} months")

    def _get_current_config(self, factor: str) -> str:
        """Get current transform configuration for a factor."""
        if factor not in FACTOR_TRANSFORM:
            return 'N/A'

        config = FACTOR_TRANSFORM[factor]
        t_type = config['type']
        window = config['window']
        flip = config.get('flip', False)

        name = f"{t_type[:4]}_{window // 12}y"
        if flip:
            name += ' (flip)'
        return name

    def compare_single_factor(self, factor: str) -> pd.DataFrame:
        """
        Compare all transform variants for a single factor.

        Args:
            factor: Factor name (V1, V4, etc.)

        Returns:
            DataFrame with columns:
                IC_full, IC_high, IC_low, IC_pval, stability,
                AUC_full, AUC_high, AUC_low,
                IC_score, AUC_score
        """
        if factor not in self.raw_factors.columns:
            print(f"  Warning: {factor} not found in data")
            return pd.DataFrame()

        raw_series = self.raw_factors[factor]
        needs_flip = factor in FLIP_FACTORS

        results = []

        for variant_name, config in self.TRANSFORM_VARIANTS.items():
            # Apply transform
            fuel = apply_single_transform(
                raw_series,
                transform_type=config['type'],
                window=config['window'],
                flip=needs_flip
            )

            if len(fuel.dropna()) < 60:
                continue

            # Resample to monthly for alignment
            fuel_monthly = fuel.resample('ME').last()

            # Compute IC
            ic_result = compute_ic_by_rate_regime(
                fuel_monthly,
                self.fwd_returns,
                self.ffr
            )

            ic_full = ic_result['full']['ic']
            ic_high = ic_result['high_rate']['ic']
            ic_low = ic_result['low_rate']['ic']
            ic_pval = ic_result['full']['p_value']

            stability = compute_stability_penalty(ic_full, ic_high, ic_low)

            # Compute AUC
            auc_result = compute_auc_mdd(
                fuel_monthly,
                self.fwd_mdd,
                threshold=-0.20,
                ffr=self.ffr
            )

            auc_full = auc_result['full']['auc']
            auc_high = auc_result['high_rate']['auc']
            auc_low = auc_result['low_rate']['auc']

            auc_stability = compute_auc_stability(auc_full, auc_high, auc_low)

            # Compute scores
            ic_score = abs(ic_full) * stability if not pd.isna(ic_full) else 0
            auc_score = abs(auc_full - 0.5) * auc_stability if not pd.isna(auc_full) else 0

            results.append({
                'variant': variant_name,
                'IC_full': ic_full,
                'IC_high': ic_high,
                'IC_low': ic_low,
                'IC_pval': ic_pval,
                'stability': stability,
                'AUC_full': auc_full,
                'AUC_high': auc_high,
                'AUC_low': auc_low,
                'IC_score': ic_score,
                'AUC_score': auc_score,
            })

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results).set_index('variant')
        return df

    def compare_all_factors(self) -> Dict[str, pd.DataFrame]:
        """
        Compare all transform variants for all factors.

        Returns:
            Dict mapping factor name to comparison DataFrame
        """
        results = {}

        for factor in self.factors:
            print(f"\nComparing transforms for {factor}...")
            df = self.compare_single_factor(factor)
            if len(df) > 0:
                results[factor] = df

        return results

    def find_best_transform(
        self,
        factor: str,
        metric: str = 'ic'
    ) -> tuple:
        """
        Find the best transform for a factor based on specified metric.

        Args:
            factor: Factor name
            metric: 'ic' or 'auc'

        Returns:
            (best_variant_name, score)
        """
        df = self.compare_single_factor(factor)
        if len(df) == 0:
            return (None, 0.0)

        score_col = 'IC_score' if metric == 'ic' else 'AUC_score'
        best_idx = df[score_col].idxmax()
        best_score = df.loc[best_idx, score_col]

        return (best_idx, best_score)

    def generate_report(self) -> str:
        """
        Generate a comprehensive Markdown report comparing all transforms.

        Returns:
            Markdown formatted report string
        """
        report = []
        report.append("# Transform Comparison Report")
        report.append("")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## Summary")
        report.append("")
        report.append("Testing 4 transform variants for each factor:")
        report.append("- `pctl_5y`: 5-year rolling percentile")
        report.append("- `pctl_10y`: 10-year rolling percentile")
        report.append("- `zscore_5y`: 5-year rolling Z-score")
        report.append("- `zscore_10y`: 10-year rolling Z-score")
        report.append("")

        # Summary table
        report.append("### Best Transform per Factor")
        report.append("")
        report.append("| Factor | Name | Current | Best IC | IC Score | Best AUC | AUC Score |")
        report.append("|--------|------|---------|---------|----------|----------|-----------|")

        all_results = self.compare_all_factors()

        for factor in self.factors:
            if factor not in all_results:
                continue

            df = all_results[factor]
            name = FACTOR_NAMES.get(factor, factor)
            current = self._get_current_config(factor)

            best_ic, ic_score = self.find_best_transform(factor, 'ic')
            best_auc, auc_score = self.find_best_transform(factor, 'auc')

            report.append(
                f"| {factor} | {name} | {current} | "
                f"{best_ic} | {ic_score:.4f} | {best_auc} | {auc_score:.4f} |"
            )

        report.append("")
        report.append("---")
        report.append("")

        # Detailed results per factor
        for factor in self.factors:
            if factor not in all_results:
                continue

            df = all_results[factor]
            name = FACTOR_NAMES.get(factor, factor)
            current = self._get_current_config(factor)

            report.append(f"## {factor}: {name}")
            report.append("")
            report.append(f"**Current Configuration**: `{current}`")
            report.append("")

            # Find best
            best_ic = df['IC_score'].idxmax()
            best_auc = df['AUC_score'].idxmax()

            report.append(f"**Best IC Transform**: `{best_ic}` (score: {df.loc[best_ic, 'IC_score']:.4f})")
            report.append(f"**Best AUC Transform**: `{best_auc}` (score: {df.loc[best_auc, 'AUC_score']:.4f})")
            report.append("")

            # Detailed table
            report.append("### Detailed Comparison")
            report.append("")
            report.append("| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |")
            report.append("|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|")

            for variant in df.index:
                row = df.loc[variant]
                report.append(
                    f"| {variant} | "
                    f"{row['IC_full']:.4f} | "
                    f"{row['IC_high']:.4f} | "
                    f"{row['IC_low']:.4f} | "
                    f"{row['IC_pval']:.4f} | "
                    f"{row['stability']:.2f} | "
                    f"{row['AUC_full']:.4f} | "
                    f"{row['IC_score']:.4f} | "
                    f"{row['AUC_score']:.4f} |"
                )

            report.append("")

            # Recommendation
            report.append("### Recommendation")
            report.append("")

            current_is_best_ic = current.startswith(best_ic.split('_')[0])
            current_is_best_auc = current.startswith(best_auc.split('_')[0])

            if best_ic == best_auc:
                if current.startswith(best_ic.split('_')[0]):
                    report.append(f"Current configuration is optimal for both IC and AUC.")
                else:
                    report.append(f"**Consider switching to `{best_ic}`** - optimal for both IC and AUC.")
            else:
                report.append(f"- IC optimized: `{best_ic}`")
                report.append(f"- AUC optimized: `{best_auc}`")
                report.append("")
                report.append("Choose based on your priority:")
                report.append("- For return prediction: use IC-optimized")
                report.append("- For crash detection: use AUC-optimized")

            report.append("")
            report.append("---")
            report.append("")

        # Final recommendations
        report.append("## Final Recommendations")
        report.append("")
        report.append("Based on this analysis, consider updating `config.py` with:")
        report.append("")
        report.append("```python")
        report.append("FACTOR_TRANSFORM = {")

        for factor in self.factors:
            if factor not in all_results:
                continue

            best_ic, _ = self.find_best_transform(factor, 'ic')
            if best_ic:
                config = self.TRANSFORM_VARIANTS[best_ic]
                flip = factor in FLIP_FACTORS
                flip_str = ", 'flip': True" if flip else ""
                report.append(
                    f"    '{factor}': {{'type': '{config['type']}', "
                    f"'window': {config['window']}{flip_str}}},"
                )

        report.append("}")
        report.append("```")
        report.append("")

        return "\n".join(report)


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compare transform variants')
    parser.add_argument(
        '--factors',
        nargs='+',
        default=['V1', 'V4', 'V5', 'V7', 'V8'],
        help='Factors to test'
    )
    parser.add_argument(
        '--output',
        default='TRANSFORM_COMPARISON_REPORT.md',
        help='Output report file'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Transform Comparison Test")
    print("=" * 60)

    comparator = TransformComparator(factors=args.factors)
    report = comparator.generate_report()

    # Save report
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        args.output
    )

    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_results = comparator.compare_all_factors()
    for factor in args.factors:
        if factor not in all_results:
            continue

        name = FACTOR_NAMES.get(factor, factor)
        best_ic, ic_score = comparator.find_best_transform(factor, 'ic')
        best_auc, auc_score = comparator.find_best_transform(factor, 'auc')

        print(f"\n{factor} ({name}):")
        print(f"  Current: {comparator._get_current_config(factor)}")
        print(f"  Best IC: {best_ic} (score: {ic_score:.4f})")
        print(f"  Best AUC: {best_auc} (score: {auc_score:.4f})")
