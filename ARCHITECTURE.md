# Indicator System Architecture

## Overview

A three-layer risk monitoring system for equity markets, consisting of:

1. **Structure Layer (FuelScore)** - Slow-moving macro vulnerability indicators
2. **Crack Layer (CrackScore)** - Marginal deterioration signals (rate of change)
3. **Trend Layer (TrendScore)** - Real-time market stress indicators

---

## Project Structure

```
indicator_test/
├── config.py              # Unified configuration (weights, thresholds, paths)
├── dashboard_app.py       # Streamlit web dashboard
├── system_orchestrator.py # Three-layer integration
│
├── core/                  # Core computation modules
│   ├── fuel_score.py      # FuelScore (IC/AUC dual weights)
│   ├── crack_score.py     # CrackScore (ΔZ signals)
│   └── trend_score.py     # TrendScore wrapper
│
├── data/                  # Data loading layer
│   └── loader.py          # Unified DataLoader with lag support
│
├── validation/            # Weight validation & optimization
│   ├── ic_calculator.py   # IC (Return correlation) calculation
│   ├── auc_calculator.py  # AUC (MDD prediction) calculation
│   └── weight_optimizer.py # Weight optimization & reporting
│
├── utils/                 # Utility functions
│   └── transforms.py      # Percentile, Z-score transforms
│
├── lib/                   # Research & analysis libraries
│   ├── ic_analysis.py     # IC statistical analysis
│   ├── regime_analysis.py # Rate regime analysis
│   └── ...
│
├── trend/                 # Trend layer implementation
│   └── trend_score/       # TrendScore module
│
└── structure/             # Structure layer data
    └── data/              # Factor CSV files
        ├── raw/           # Original data
        └── lagged/        # Release-lag adjusted data
```

---

## Core Modules

### 1. FuelScore (`core/fuel_score.py`)

Measures long-term macro vulnerability accumulation (0-100 scale).

**Factors:**
| Factor | Name | Weight (IC) | Weight (AUC) |
|--------|------|-------------|--------------|
| V1 | ST Debt Ratio | 12.2% | 6.4% |
| V4 | Interest Coverage | 4.6% | 0.0% |
| V5 | TDSP (Debt Service) | 31.3% | 52.0% |
| V7 | CAPE | 14.2% | 28.4% |
| V8 | Margin Debt | 37.7% | 13.2% |

**Weight Schemes:**
- **IC (Return)**: Based on 12-month forward return correlation
- **AUC (MDD)**: Based on predicting 12-month MDD < -20%

**Usage:**
```python
from core import FuelScore

fuel = FuelScore(weight_scheme='ic')  # or 'auc'
result = fuel.compute()
# {'fuel_score': 55.0, 'signal': 'NEUTRAL', ...}

# Compare both schemes
both = fuel.compute_both_schemes()
# {'ic': {'fuel_score': 55.0}, 'auc': {'fuel_score': 78.0}}

# Historical data
history = fuel.compute_history('2020-01-01', '2024-12-31')
```

**Signal Thresholds:**
- EXTREME LOW: < 20
- LOW: 20-40
- NEUTRAL: 40-60
- HIGH: 60-80
- EXTREME HIGH: > 80

---

### 2. CrackScore (`core/crack_score.py`)

Tracks rate of change (ΔZ) in vulnerability factors. Early warning for regime shifts.

**Factors & Weights:**
| Factor | Weight | Description |
|--------|--------|-------------|
| V2 | 17.5% | Uninsured Deposits |
| V4 | 33.3% | Interest Coverage |
| V5 | 16.6% | TDSP |
| V8 | 24.6% | Margin Debt |

**States:**
- **STABLE**: ΔZ < 0.3σ
- **EARLY_CRACK**: 0.3σ ≤ ΔZ < 0.5σ
- **WIDENING_CRACK**: 0.5σ ≤ ΔZ < 1.0σ
- **BREAKING**: ΔZ ≥ 1.0σ

**Usage:**
```python
from core import CrackScore

crack = CrackScore()
result = crack.compute()
# {'crack_score': 0.50, 'state': 'STABLE', ...}
```

---

### 3. TrendScore (`core/trend_score.py`)

Real-time market stress indicator from high-frequency data (0-1 scale).

**Modules:**
- **A**: Credit Spread (VIX, credit spreads)
- **B**: Equity Volatility
- **C**: Rate Structure
- **D**: Macro Stress

**States:**
- **CALM**: < 0.25
- **WATCH**: 0.25-0.45
- **ALERT**: 0.45-0.65
- **CRITICAL**: > 0.65

**Usage:**
```python
from core import TrendScore

trend = TrendScore()
result = trend.compute()
# {'trend_score': 0.01, 'state': 'CALM', ...}
```

---

## Data Layer

### DataLoader (`data/loader.py`)

Unified data loading with caching and release lag support.

**Key Features:**
- In-memory caching
- Release lag adjustment (RELEASE_LAG config)
- FRED API integration
- Yahoo Finance for Trend data

**Usage:**
```python
from data.loader import DataLoader

loader = DataLoader()

# Load structure factors (with lag)
factors = loader.load_structure_factors(use_lagged=True)

# Load market data
spx = loader.load_spx()
fed_funds = loader.load_fed_funds()

# Generate lagged data
loader.generate_lagged_data()
```

**CLI:**
```bash
python -m data.loader                   # Load from cache
python -m data.loader --refresh         # Re-download all
python -m data.loader --generate-lagged # Generate lagged data
```

---

## Configuration (`config.py`)

Central configuration file containing:

```python
# Release lag (months)
RELEASE_LAG = {
    'V1': 5,   # Z.1 Financial Accounts
    'V2': 6,   # Z.1 Financial Accounts
    'V4': 6,   # BEA NIPA
    'V5': 3,   # Federal Reserve
    'V7': 0,   # Shiller CAPE (real-time)
    'V8': 2,   # Fed Flow of Funds
    'V9': 1,   # SLOOS
}

# FuelScore weights
FUEL_WEIGHTS_IC = {...}   # IC-based weights
FUEL_WEIGHTS_AUC = {...}  # AUC-based weights

# Transform configuration
FACTOR_TRANSFORM = {...}  # Percentile/Z-score settings

# System thresholds
SYSTEM_THRESHOLDS = {...}
```

---

## Validation Module

### Weight Optimizer (`validation/weight_optimizer.py`)

Computes optimal weights using IC or AUC metrics.

**Usage:**
```python
from validation import WeightOptimizer
from data.loader import DataLoader

optimizer = WeightOptimizer(DataLoader())

# Compute weights
ic_weights = optimizer.compute_ic_weights()
auc_weights = optimizer.compute_auc_weights()

# Generate report
report_path = optimizer.generate_report()
```

---

## Dashboard (`dashboard_app.py`)

Streamlit web UI for real-time monitoring.

**Features:**
- System status overview
- Three-layer detail tabs (Fuel/Crack/Trend)
- IC vs AUC weight comparison chart
- Historical trends with S&P 500 overlay
- Weight recalculation button

**Run:**
```bash
streamlit run dashboard_app.py --server.port 8501
```

**URL:** http://localhost:8501

---

## System Orchestrator (`system_orchestrator.py`)

Integrates all three layers into a unified signal.

**Usage:**
```python
from system_orchestrator import SystemOrchestrator

orch = SystemOrchestrator(use_lagged=True)
result = orch.compute_portfolio_action()

# Returns:
# {
#     'system_state': 'NORMAL',      # NORMAL/CAUTIOUS/DEFENSIVE/CRISIS
#     'action': 'HOLD',               # HOLD/DE-RISK/HEDGE/EXIT
#     'risk_budget': 0.75,            # 0.35-1.15
#     'structure': {...},
#     'crack': {...},
#     'trend': {...},
# }
```

---

## Quick Start

```python
# 1. Current system status
from system_orchestrator import SystemOrchestrator
orch = SystemOrchestrator()
print(orch.compute_portfolio_action())

# 2. Individual layer analysis
from core import FuelScore, CrackScore, TrendScore

fuel = FuelScore(weight_scheme='ic')
print(f"FuelScore: {fuel.compute()['fuel_score']:.1f}")

crack = CrackScore()
print(f"CrackScore: {crack.compute()['crack_score']:.2f}σ")

trend = TrendScore()
print(f"TrendScore: {trend.compute()['trend_score']:.2f}")

# 3. IC vs AUC comparison
both = FuelScore().compute_both_schemes()
print(f"IC: {both['ic']['fuel_score']:.1f}, AUC: {both['auc']['fuel_score']:.1f}")
```

---

## File Summary

| File | Lines | Description |
|------|-------|-------------|
| `config.py` | ~150 | Central configuration |
| `data/loader.py` | ~300 | Unified data loading |
| `core/fuel_score.py` | ~330 | FuelScore (dual weights) |
| `core/crack_score.py` | ~350 | CrackScore (ΔZ) |
| `core/trend_score.py` | ~80 | TrendScore wrapper |
| `validation/*.py` | ~400 | IC/AUC calculation |
| `utils/transforms.py` | ~150 | Transform functions |
| `dashboard_app.py` | ~1000 | Streamlit dashboard |
| `system_orchestrator.py` | ~700 | System integration |

**Total: ~32 Python files** (reduced from 45 after refactoring)
