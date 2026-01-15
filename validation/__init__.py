"""
Validation Module
=================

IC and AUC-based weight calculation and validation for FuelScore.

Usage:
    from validation import WeightOptimizer

    optimizer = WeightOptimizer()
    ic_weights = optimizer.compute_ic_weights()
    auc_weights = optimizer.compute_auc_weights()
"""

from .weight_optimizer import WeightOptimizer
from .ic_calculator import compute_ic_by_rate_regime, compute_stability_penalty
from .auc_calculator import compute_auc_mdd, compute_auc_stability

__all__ = [
    'WeightOptimizer',
    'compute_ic_by_rate_regime',
    'compute_stability_penalty',
    'compute_auc_mdd',
    'compute_auc_stability',
]
