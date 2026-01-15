"""
Weight Optimizer
================

Computes optimal factor weights using IC (Return) or AUC (MDD) methods.

Usage:
    from validation import WeightOptimizer
    from data.loader import DataLoader

    loader = DataLoader()
    optimizer = WeightOptimizer(loader)

    ic_weights = optimizer.compute_ic_weights()
    auc_weights = optimizer.compute_auc_weights()
"""

import os
import sys
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    FACTOR_TRANSFORM,
    FACTOR_FILES,
    PROJECT_ROOT,
)
from .ic_calculator import (
    compute_ic_by_rate_regime,
    compute_stability_penalty,
    compute_forward_return,
)
from .auc_calculator import (
    compute_auc_mdd,
    compute_auc_stability,
    compute_forward_max_drawdown,
)


class WeightOptimizer:
    """
    Optimizes factor weights using IC or AUC methods.

    Two weight schemes:
    - IC (Return): Weight = |IC| * stability, where IC is vs 12M forward return
    - AUC (MDD): Weight = |AUC - 0.5| * stability, where AUC predicts 12M MDD < -20%
    """

    def __init__(self, loader=None):
        """
        Initialize weight optimizer.

        Args:
            loader: DataLoader instance (optional, will create if not provided)
        """
        if loader is None:
            from data.loader import DataLoader
            loader = DataLoader()

        self.loader = loader
        self._factor_fuel: Optional[pd.DataFrame] = None
        self._spx: Optional[pd.Series] = None
        self._ffr: Optional[pd.Series] = None

    def _load_data(self):
        """Load required data if not already loaded."""
        if self._factor_fuel is None:
            from utils.transforms import apply_transforms

            factors = self.loader.load_structure_factors(use_lagged=True)
            self._factor_fuel = apply_transforms(factors)

        if self._spx is None:
            self._spx = self.loader.load_spx(use_lagged=True)

        if self._ffr is None:
            self._ffr = self.loader.load_fed_funds(use_lagged=True)

    def compute_ic_weights(self) -> Dict[str, float]:
        """
        Compute weights based on IC vs Forward 12M Return.

        Formula:
            w_i = (|IC_i| * stability_i) / sum(|IC_j| * stability_j)

        Returns:
            Dict mapping factor names (e.g., 'V1_fuel') to weights
        """
        self._load_data()

        # Compute forward returns
        fwd_return = compute_forward_return(self._spx, horizon=12)
        fwd_return = fwd_return.reindex(self._factor_fuel.index)
        ffr_monthly = self._ffr.resample('ME').last().reindex(self._factor_fuel.index)

        # Compute IC for each factor
        ic_results = {}
        for col in self._factor_fuel.columns:
            factor_series = self._factor_fuel[col].dropna()
            if len(factor_series) < 60:
                continue
            ic_results[col] = compute_ic_by_rate_regime(
                factor_series, fwd_return, ffr_monthly
            )

        # Compute weights
        weights_raw = {}
        for col, ic_data in ic_results.items():
            ic_full = ic_data['full']['ic']
            ic_high = ic_data['high_rate']['ic']
            ic_low = ic_data['low_rate']['ic']

            if pd.isna(ic_full):
                weights_raw[col] = 0.0
                continue

            base_weight = abs(ic_full)
            stability = compute_stability_penalty(ic_full, ic_high, ic_low)
            weights_raw[col] = base_weight * stability

        # Normalize
        total = sum(weights_raw.values())
        if total < 0.001:
            return {col: 1.0 / len(ic_results) for col in ic_results}

        return {col: w / total for col, w in weights_raw.items()}

    def compute_auc_weights(self, threshold: float = -0.20) -> Dict[str, float]:
        """
        Compute weights based on AUC vs Forward 12M MDD.

        Formula:
            w_i = (|AUC_i - 0.5| * stability_i) / sum(...)

        Args:
            threshold: MDD threshold (default -0.20 for -20%)

        Returns:
            Dict mapping factor names (e.g., 'V1_fuel') to weights
        """
        self._load_data()

        # Compute forward MDD
        fwd_mdd = compute_forward_max_drawdown(self._spx, horizon=252)
        fwd_mdd_monthly = fwd_mdd.resample('ME').first()
        fwd_mdd_monthly = fwd_mdd_monthly.reindex(self._factor_fuel.index)
        ffr_monthly = self._ffr.resample('ME').last().reindex(self._factor_fuel.index)

        # Compute AUC for each factor
        auc_results = {}
        for col in self._factor_fuel.columns:
            factor_series = self._factor_fuel[col].dropna()
            if len(factor_series) < 60:
                continue
            auc_results[col] = compute_auc_mdd(
                factor_series, fwd_mdd_monthly, threshold, ffr_monthly
            )

        # Compute weights
        weights_raw = {}
        for col, auc_data in auc_results.items():
            auc_full = auc_data['full']['auc']
            auc_high = auc_data['high_rate']['auc']
            auc_low = auc_data['low_rate']['auc']

            if pd.isna(auc_full):
                weights_raw[col] = 0.0
                continue

            # Effective signal: |AUC - 0.5|
            base_weight = abs(auc_full - 0.5)
            stability = compute_auc_stability(auc_full, auc_high, auc_low)
            weights_raw[col] = base_weight * stability

        # Normalize
        total = sum(weights_raw.values())
        if total < 0.001:
            return {col: 1.0 / len(auc_results) for col in auc_results}

        return {col: w / total for col, w in weights_raw.items()}

    def generate_report(self, output_dir: str = None) -> str:
        """
        Generate validation report comparing IC and AUC weights.

        Args:
            output_dir: Output directory (default: validation/reports/)

        Returns:
            Path to generated report
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(__file__), 'reports'
            )
        os.makedirs(output_dir, exist_ok=True)

        self._load_data()

        # Compute both weight schemes
        ic_weights = self.compute_ic_weights()
        auc_weights = self.compute_auc_weights()

        # Get factor names
        factors = sorted(set(
            col.replace('_fuel', '') for col in ic_weights.keys()
        ))

        # Generate report
        report = f"""# Weight Validation Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Weight Comparison

| Factor | IC Weight | AUC Weight |
|--------|-----------|------------|
"""

        for factor in factors:
            col = f'{factor}_fuel'
            ic_w = ic_weights.get(col, 0) * 100
            auc_w = auc_weights.get(col, 0) * 100
            report += f"| {factor} | {ic_w:.1f}% | {auc_w:.1f}% |\n"

        report += """

## Method Description

### IC (Return) Weights
- Based on Spearman IC vs Forward 12M Return
- Formula: w = |IC| × stability
- Stability: Cross-rate-regime consistency

### AUC (MDD) Weights
- Based on AUC for predicting 12M MDD < -20%
- Formula: w = |AUC - 0.5| × stability
- More focused on tail risk prediction

## Recommended Usage

- **IC weights**: General risk monitoring
- **AUC weights**: Tail risk / crash prediction focus

---

*Generated by WeightOptimizer*
"""

        report_path = os.path.join(output_dir, 'weight_validation_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report_path


# CLI interface
if __name__ == '__main__':
    print("Computing weights...")

    from data.loader import DataLoader

    loader = DataLoader()
    optimizer = WeightOptimizer(loader)

    print("\n[IC Weights (Return)]")
    ic_weights = optimizer.compute_ic_weights()
    for col, w in sorted(ic_weights.items(), key=lambda x: -x[1]):
        print(f"  {col}: {w:.1%}")

    print("\n[AUC Weights (MDD)]")
    auc_weights = optimizer.compute_auc_weights()
    for col, w in sorted(auc_weights.items(), key=lambda x: -x[1]):
        print(f"  {col}: {w:.1%}")

    print("\n[Generating Report]")
    report_path = optimizer.generate_report()
    print(f"  Saved: {report_path}")
