"""
Unified Configuration for Indicator System
==========================================

All configuration parameters for Structure, Crack, and Trend layers.

Usage:
    from config import RELEASE_LAG, FUEL_WEIGHTS_IC, FUEL_WEIGHTS_AUC
"""

import os

# ============== Directory Paths ==============

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCTURE_DIR = os.path.join(PROJECT_ROOT, 'structure')
DATA_DIR = os.path.join(STRUCTURE_DIR, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
LAGGED_DIR = os.path.join(DATA_DIR, 'lagged')
TREND_DATA_DIR = os.path.join(PROJECT_ROOT, 'trend', 'data')

# ============== API Keys ==============

FRED_API_KEY = os.environ.get('FRED_API_KEY')
if FRED_API_KEY is None:
    import warnings
    warnings.warn(
        "FRED_API_KEY environment variable not set. "
        "Set it via: export FRED_API_KEY='your_key_here'",
        UserWarning
    )

# ============== Release Lag Configuration ==============
# Based on ALFRED analysis - publication delays for each factor
# Used to simulate "data available at decision time"

RELEASE_LAG = {
    'V1': 5,   # Z.1 Financial Accounts, ~5 months
    'V2': 6,   # Z.1 Financial Accounts, ~6 months (conservative)
    'V4': 6,   # BEA NIPA, ~6 months
    'V5': 3,   # Federal Reserve, ~3 months
    'V7': 0,   # Shiller CAPE, real-time
    'V8': 2,   # Fed Flow of Funds, ~2 months
    'V9': 1,   # SLOOS, ~1 month
}

# ============== Factor Configuration ==============

# Factor files mapping: factor_name -> (filename, value_column)
FACTOR_FILES = {
    'V1': ('V1_st_debt.csv', 'st_debt'),
    'V2': ('V2_uninsured_deposits.csv', 'ratio'),
    'V4': ('V4_icr.csv', 'icr'),
    'V5': ('V5_tdsp.csv', 'tdsp'),
    'V7': ('V7_cape.csv', 'cape'),
    'V8': ('V8_margin_debt.csv', 'ratio'),
    'V9': ('V9_cre_lending.csv', 'avg'),
}

# Factor direction: True = high value = high risk
FACTOR_DIRECTION = {
    'V1': True,   # ST Debt: high = risky
    'V2': True,   # Uninsured Deposits: high = risky
    'V4': False,  # ICR: LOW = risky (needs flip)
    'V5': True,   # TDSP: high = risky
    'V7': True,   # CAPE: high = risky
    'V8': True,   # Margin Debt: high = risky
    'V9': True,   # CRE Lending: high tightening = risky
}

# Factor display names
FACTOR_NAMES = {
    'V1': 'ST Debt Ratio',
    'V2': 'Uninsured Deposits',
    'V4': 'Interest Coverage',
    'V5': 'TDSP',
    'V7': 'CAPE',
    'V8': 'Margin Debt',
    'V9': 'CRE Lending',
}

# ============== Transform Configuration ==============

# Transform type and window for each factor
# Updated 2026-01-04: All factors changed to percentile, V8 to credit_gap
FACTOR_TRANSFORM = {
    'V1': {'type': 'percentile', 'window': 120},  # 10Y rolling percentile
    'V2': {'type': 'percentile', 'window': 120},  # 10Y rolling percentile (aux, 0% weight)
    'V4': {'type': 'percentile', 'window': 60, 'flip': True},   # 5Y percentile, flipped (low ICR=high risk)
    'V5': {'type': 'percentile', 'window': 60},   # 5Y rolling percentile
    'V7': {'type': 'percentile', 'window': 120},  # 10Y rolling percentile
    'V8': {'type': 'credit_gap', 'window': 120},  # 10Y Credit Gap (filters long-term trend)
    'V9': {'type': 'ushape', 'window': 120},      # 10Y U-shape |Pctl-50| (bidirectional signal)
}

# ============== FuelScore Weights ==============

# IC-based weights (vs Forward 12M Return)
# Source: FUEL_SCORE_REPORT.md
# Formula: |IC| * stability / sum(|IC| * stability)
FUEL_WEIGHTS_IC = {
    'V1_fuel': 0.122,   # 12.2%
    'V2_fuel': 0.000,   # 0.0% (stability = 0)
    'V4_fuel': 0.046,   # 4.6%
    'V5_fuel': 0.313,   # 31.3%
    'V7_fuel': 0.142,   # 14.2%
    'V8_fuel': 0.377,   # 37.7%
}

# AUC-based weights (vs Forward 12M MDD < -20%)
# Source: auc_mdd/fuel_score.py
# Formula: |AUC - 0.5| * stability / sum(...)
FUEL_WEIGHTS_AUC = {
    'V1_fuel': 0.064,   # 6.4%
    'V2_fuel': 0.000,   # 0.0%
    'V4_fuel': 0.000,   # 0.0%
    'V5_fuel': 0.520,   # 52.0%
    'V7_fuel': 0.284,   # 28.4%
    'V8_fuel': 0.132,   # 13.2%
}

# ============== CrackScore Configuration ==============

# Crack calculation parameters
CRACK_CONFIG = {
    # Delta Z-score windows
    'delta_window': {
        'V1': 4,   # 4 quarters (12M)
        'V2': 4,   # 4 quarters (12M)
        'V4': 4,   # 4 quarters (12M)
        'V5': 4,   # 4 quarters (12M)
        'V7': 4,   # 4 quarters (12M)
        'V8': 8,   # 8 quarters (24M)
    },
    # Z-score lookback window (months)
    'zscore_window': 120,  # 10 years

    # Crack state thresholds (sigma units)
    'thresholds': {
        'STABLE': 0.5,         # < 0.5 sigma
        'EARLY_CRACK': 1.0,    # 0.5 - 1.0 sigma
        'WIDENING_CRACK': 1.5, # 1.0 - 1.5 sigma
        'BREAKING': 1.5,       # >= 1.5 sigma
    },

    # Factor weights in crack score
    # Based on IC/AUC validation (see crack/crack_ic_auc_summary.csv)
    'weights': {
        'V1': 0.051,  # ST Debt (weak signal, IC p=0.368)
        'V2': 0.175,  # Bank-run risk
        'V4': 0.333,  # Credit risk (strongest)
        'V5': 0.166,  # Household stress
        'V7': 0.029,  # CAPE (weak signal, AUC<0.5)
        'V8': 0.246,  # Leverage risk
    },
}

# ============== TrendScore Configuration ==============

TREND_CONFIG = {
    # Module weights
    'module_weights': {
        'A': 0.25,  # Volatility
        'B': 0.25,  # Funding/Liquidity
        'C': 0.30,  # Credit
        'D': 0.20,  # Flow
    },

    # Data quality thresholds
    'quality_thresholds': {
        'STRONG': 4,   # All 4 modules have data
        'OK': 3,       # 3+ modules
        'WEAK': 2,     # 2 modules
        'NONE': 0,     # <2 modules
    },

    # State thresholds (0-1 scale)
    'state_thresholds': {
        'CALM': 0.3,
        'WATCH': 0.5,
        'ALERT': 0.7,
        'CRITICAL': 1.0,
    },
}

# ============== System State Thresholds ==============

SYSTEM_THRESHOLDS = {
    # FuelScore thresholds
    'fuel_score': {
        'LOW': 20,
        'NEUTRAL': 40,
        'HIGH': 60,
        'EXTREME': 80,
    },

    # Risk budget formula: clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)
    'risk_budget': {
        'min': 0.35,
        'max': 1.15,
        'base': 1.1,
        'slope': 0.007,
    },
}

# ============== Rule Engine Config (v2.0) ==============

# FuelState 阈值 (FuelScore -> 离散状态)
FUEL_STATE_THRESHOLDS = {
    'LOW': 40,        # FuelScore < 40
    'NEUTRAL': 60,    # 40 <= FuelScore < 60
    'HIGH': 80,       # 60 <= FuelScore < 80
    'EXTREME': 100,   # FuelScore >= 80
}

# 状态乘数 (State Multiplier) - 系统状态对 Risk Budget 的影响
STATE_MULTIPLIERS = {
    'NORMAL': 1.00,
    'CAUTIOUS': 0.85,
    'DEFENSIVE': 0.60,
    'CRISIS': 0.30,
}

# Crack Penalty - CrackState 对 Risk Budget 的额外惩罚
CRACK_PENALTIES = {
    'STABLE': 1.00,
    'EARLY_CRACK': 0.90,
    'WIDENING_CRACK': 0.75,
    'BREAKING': 0.60,
}

# Trend Penalty - TrendState 对 Risk Budget 的惩罚 (仅 quality OK/STRONG 时启用)
TREND_PENALTIES = {
    'CALM': 1.00,
    'WATCH': 0.95,
    'ALERT': 0.85,
    'CRITICAL': 0.70,
}

# Hysteresis 配置 (防抖，降级比升级更严格)
HYSTERESIS_CONFIG = {
    'trend_downgrade_days': 10,     # Trend 需连续 N 天回到低状态才能降级
    'crack_downgrade_months': 2,    # Crack 需连续 N 月低于阈值才能降级
    'fuel_downgrade_quarters': 2,   # Fuel 需连续 N 季度下降才能降级
}

# ============== Cache Configuration ==============

CACHE_CONFIG = {
    'streamlit_ttl': 3600,       # 1 hour cache for computed data
    'history_ttl': 3600,          # 1 hour cache for history data
    'enable_incremental': True,   # Enable incremental data updates
}

# ============== Rule Engine v2.0 - Declarative Rules ==============

# Priority rules (evaluated in order, first match wins)
# Each rule: (id, name, state, action, conditions)
# conditions: dict with keys: fuel_states, crack_states, trend_states, trend_qualities
PRIORITY_RULES = [
    # R1: Crisis - 结构破裂 + 市场确认
    {
        'id': 'R1',
        'name': 'Crisis: Trend CRITICAL + Crack裂缝',
        'state': 'CRISIS',
        'action': 'EXIT',
        'conditions': {
            'trend_states': ['CRITICAL'],
            'crack_states': ['WIDENING_CRACK', 'BREAKING'],
            'trend_qualities': ['OK', 'STRONG'],
        },
    },
    # R2: Crisis - Crack Breaking + Trend Alert
    {
        'id': 'R2',
        'name': 'Crisis: Crack BREAKING + Trend ALERT+',
        'state': 'CRISIS',
        'action': 'EXIT',
        'conditions': {
            'crack_states': ['BREAKING'],
            'trend_states': ['ALERT', 'CRITICAL'],
            'trend_qualities': ['OK', 'STRONG'],
        },
    },
    # R3: Defensive - 结构裂缝扩大 + Trend 转坏
    {
        'id': 'R3',
        'name': 'Defensive: Crack WIDENING + Trend升级',
        'state': 'DEFENSIVE',
        'action': 'HEDGE',
        'conditions': {
            'crack_states': ['WIDENING_CRACK'],
            'trend_states': ['WATCH', 'ALERT', 'CRITICAL'],
            'trend_qualities': ['OK', 'STRONG'],
        },
    },
    # R4: Defensive - Fuel 极高 + Trend Alert
    {
        'id': 'R4',
        'name': 'Defensive: Fuel EXTREME + Trend ALERT+',
        'state': 'DEFENSIVE',
        'action': 'HEDGE',
        'conditions': {
            'fuel_states': ['EXTREME'],
            'trend_states': ['ALERT', 'CRITICAL'],
            'trend_qualities': ['OK', 'STRONG'],
        },
    },
    # R5: Cautious - Fuel 高或极高 (不依赖 Trend)
    {
        'id': 'R5',
        'name': 'Cautious: Fuel高位，未点火',
        'state': 'CAUTIOUS',
        'action': 'DE-RISK',
        'conditions': {
            'fuel_states': ['HIGH', 'EXTREME'],
            'crack_states': ['STABLE', 'EARLY_CRACK'],
        },
    },
    # R6: Cautious - Crack Early Crack
    {
        'id': 'R6',
        'name': 'Cautious: Crack早期裂纹',
        'state': 'CAUTIOUS',
        'action': 'DE-RISK',
        'conditions': {
            'crack_states': ['EARLY_CRACK'],
        },
    },
    # R7: Normal - 低风险组合
    {
        'id': 'R7',
        'name': 'Normal: 无重大风险',
        'state': 'NORMAL',
        'action': 'HOLD',
        'conditions': {
            'fuel_states': ['LOW', 'NEUTRAL'],
            'crack_states': ['STABLE'],
            'trend_states': ['CALM', 'WATCH'],
        },
    },
]

# Fallback rules (when trend quality is WEAK/NONE)
FALLBACK_RULES = [
    {'id': 'R8a', 'name': 'Fallback: Crack BREAKING', 'state': 'CRISIS', 'action': 'EXIT',
     'conditions': {'crack_states': ['BREAKING']}},
    {'id': 'R8b', 'name': 'Fallback: Crack WIDENING', 'state': 'DEFENSIVE', 'action': 'HEDGE',
     'conditions': {'crack_states': ['WIDENING_CRACK']}},
    {'id': 'R8c', 'name': 'Fallback: Crack EARLY', 'state': 'CAUTIOUS', 'action': 'DE-RISK',
     'conditions': {'crack_states': ['EARLY_CRACK']}},
    {'id': 'R8d', 'name': 'Fallback: Fuel EXTREME', 'state': 'CAUTIOUS', 'action': 'DE-RISK',
     'conditions': {'fuel_states': ['EXTREME']}},
    {'id': 'R8e', 'name': 'Fallback: Fuel HIGH', 'state': 'CAUTIOUS', 'action': 'DE-RISK',
     'conditions': {'fuel_states': ['HIGH']}},
]

# Default rule (when no rules match)
DEFAULT_RULE = {
    'id': 'R0',
    'name': 'Default: 未触发任何规则',
    'state': 'NORMAL',
    'action': 'HOLD',
}
