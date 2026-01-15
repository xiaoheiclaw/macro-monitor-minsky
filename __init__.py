"""
Indicator Test - Macroeconomic Indicator Validation Framework
=============================================================

Three-layer risk monitoring system:
- Structure Layer (FuelScore): Slow-moving vulnerability indicators
- Crack Layer (CrackScore): Rate-of-change indicators
- Trend Layer (TrendScore): Real-time market stress signals
"""

from .config import (
    FUEL_WEIGHTS_IC,
    FUEL_WEIGHTS_AUC,
    SYSTEM_THRESHOLDS,
    CRACK_CONFIG,
    TREND_CONFIG,
)

__version__ = "0.1.0"
__all__ = [
    "FUEL_WEIGHTS_IC",
    "FUEL_WEIGHTS_AUC",
    "SYSTEM_THRESHOLDS",
    "CRACK_CONFIG",
    "TREND_CONFIG",
]
