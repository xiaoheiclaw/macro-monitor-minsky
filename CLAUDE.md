# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Validate a new indicator
FRED_API_KEY='your_key' python test_v*.py

# Check syntax before commit
python -m py_compile your_file.py

# Run all tests in a dimension
for f in test_v*.py; do python "$f"; done
```

## Environment Setup

```bash
# Required environment variable
export FRED_API_KEY='your_fred_api_key'

# Install dependencies
pip install pandas numpy matplotlib fredapi scipy
```

## Project Overview

Macroeconomic indicator validation framework for predicting financial crises. Tests various economic indicators against historical crises (2001 dot-com, 2007 GFC, 2020 COVID) to assess their effectiveness as early warning signals.

## Running Tests

```bash
# Run individual indicator test
python test_v6_shiller_pe.py
python test_v3b_household_debt.py

# Run ALFRED point-in-time backtest (no look-ahead bias)
python test_v1_debt_gdp_alfred.py

# Tests output to V*_Indicator_Name/ directories:
# - 01_all_methods.png (visualization)
# - all_methods_data.csv (calculated metrics)
# - SUMMARY.md (results and conclusions)
```

## Dependencies

```
pandas
numpy
matplotlib
fredapi
scipy
```

FRED API key is hardcoded in `indicator_validation.py`.

## Architecture

### Core Files

- **indicator_validation.py** - Main validation framework with data loading, processing functions, and the 4-step validation pipeline
- **test_v*.py** - Individual indicator test scripts

### lib/ Module (ALFRED Point-in-Time)

Reusable modules for point-in-time backtesting:

- **lib/alfred_data.py** - ALFRED API data loading, month-end as-of sequence construction
  - `ALFREDDataLoader` - Load all releases from ALFRED
  - `build_pit_factor_series()` - Build YoY factor within same vintage
- **lib/transform_layers.py** - Factor transformation pipeline
  - `TransformPipeline` - Winsorize → MAD Z-Score → Percentile/CDF
- **lib/ic_analysis.py** - Information Coefficient analysis
  - `ICAnalyzer` - Spearman/Pearson IC, ICIR, Rolling IC

### Three Indicator Dimensions

Each dimension has specialized processing in `indicator_validation.py`:

| Dimension | Function | Window | Features |
|-----------|----------|--------|----------|
| Cash Flow Pressure | `process_cash_flow_indicator()` | 60 months | Base score (70%) + Velocity (20%) + Acceleration (10%) |
| Duration Mismatch | `process_duration_mismatch_indicator()` | 120 months | Percentile (75%) + Velocity (25%) |
| Valuation | `process_valuation_indicator()` | 180 months | Enhanced percentile (60%) + Velocity (25%) + Acceleration (15%) |

### Validation Pipeline (4 Steps)

1. **Visual Sniff Test** - Overlay indicator vs SPX with NBER recession bands
2. **Lead/Lag Analysis** - Cross-correlation with SPX returns
3. **Redundancy Check** - Correlation matrix between indicators
4. **False Positive Test** - Type I error (false alarms) and Type II error (missed crises)

### Directory Structure

V* directories follow consistent naming:
- `V#_Name/` - Active indicators
- `V#_Name_PASS/` - Rejected indicators (too many false positives)
- Chinese-named folders are localized versions

## Key Conventions

- Alert threshold: `>=90th percentile` (except Interest Coverage uses `<=10th`)
- Forward observation window: 60 days for market impact
- Data sources: FRED API + local CSV files in project root
- Outlier handling: Winsorization at 1st/99th percentiles
- Z-score: MAD-based (robust) rather than standard deviation

## Current Indicator Status

| Indicator | Type I Error | Type II Error | Status |
|-----------|--------------|---------------|--------|
| V2: Interest Coverage | 25% | 33% | BEST - Keep |
| V1: Debt-GDP Gap | 50% | 33% | Keep (lags market) |
| V3b: Household Debt/GDP | 33% | 0% | Conditional (short history) |
| V6: Shiller PE | 75% | 0% | Conditional (high false alarms) |
| V3: Savings Rate | 100% | 33% | PASS - Rejected |
| V4: ST Debt Ratio | 75% | 33% | PASS - Rejected |

## Claude Code Guidelines

### When Adding a New Indicator

1. Copy an existing `test_v*.py` as template
2. Use `lib/alfred_data.py` for point-in-time data (avoid look-ahead bias)
3. Apply `lib/transform_layers.py` for standardization
4. Run the 4-step validation pipeline
5. Save results to `V#_Indicator_Name/` directory

### Code Style

- Use type hints for function signatures
- Follow existing naming conventions (snake_case)
- Add docstrings for public functions
- Use MAD-based z-score (not standard deviation)

### Common Pitfalls

- **Look-ahead bias**: Always use ALFRED point-in-time data for backtests
- **Percentile direction**: Interest Coverage uses <=10th, others use >=90th
- **Window size matters**: Cash Flow (60mo), Duration (120mo), Valuation (180mo)
