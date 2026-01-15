# Unified Fuel Score Report

Generated: 2025-12-31 16:26:47

## Summary

| Metric | Value |
|--------|-------|
| **Current Fuel Score** | **54.9** |
| Latest Date | 2026-01-31 |
| Signal | NEUTRAL |

---

## Factor Transform Configuration

| Factor | Transform | Window | Direction |
|--------|-----------|--------|-----------|
| V1 | Percentile | 10Y | ST Debt high = Fuel high |
| V2 | Percentile | 10Y | Uninsured high = Fuel high |
| V4 | Percentile (Flipped) | 10Y | ICR low = Fuel high |
| V5 | Percentile | 5Y | TDSP high = Fuel high |
| V7 | Z-score | 10Y | CAPE high = Fuel high |
| V8 | Z-score | 10Y | Margin Debt high = Fuel high |
| V9 | Percentile | 10Y | CRE Tightening high = Fuel high |

---

## IC vs Forward 12M Return

| Factor | IC | p-value | Significance |
|--------|-----|---------|--------------|
| V1 | 0.116 | 0.0432 | ** |
| V2 | -0.008 | 0.9023 |  |
| V4 | -0.044 | 0.4453 |  |
| V5 | -0.297 | 0.0000 | *** |
| V7 | -0.135 | 0.0186 | ** |
| V8 | -0.427 | 0.0000 | *** |

---

## IC by Rate Regime

| Factor | Full IC | High Rate IC | Low Rate IC | Stability |
|--------|---------|--------------|-------------|-----------|
| V1 | 0.116 | 0.248 | 0.005 | 1.00 |
| V2 | -0.008 | 0.451 | -0.156 | 0.00 |
| V4 | -0.044 | -0.335 | 0.432 | 1.00 |
| V5 | -0.297 | -0.509 | 0.101 | 1.00 |
| V7 | -0.135 | 0.013 | -0.297 | 1.00 |
| V8 | -0.427 | -0.492 | -0.225 | 0.84 |

---

## AUC (Drawdown Prediction)

| Factor | MDD<-10% | MDD<-15% | MDD<-20% |
|--------|----------|----------|----------|
| V1 | 0.623 | 0.569 | 0.622 |
| V2 | 0.485 | 0.337 | 0.477 |
| V4 | 0.622 | 0.667 | 0.725 |
| V5 | 0.583 | 0.644 | 0.737 |
| V7 | 0.671 | 0.560 | 0.565 |
| V8 | 0.562 | 0.617 | 0.714 |

---

## Final Weights

| Factor | Base Weight (|IC|) | Stability | Final Weight |
|--------|-------------------|-----------|--------------|
| V1 | 0.116 | 1.00 | 0.122 (12.2%) |
| V2 | 0.008 | 0.00 | 0.000 (0.0%) |
| V4 | 0.044 | 1.00 | 0.046 (4.6%) |
| V5 | 0.297 | 1.00 | 0.313 (31.3%) |
| V7 | 0.135 | 1.00 | 0.142 (14.2%) |
| V8 | 0.427 | 0.84 | 0.377 (37.7%) |

---

## Current Factor Values

| Factor | Raw Value | Fuel Score | Transform |
|--------|-----------|------------|-----------|
| V1 | - | 66.7 | Percentile(10Y) |
| V2 | - | 86.7 | Percentile(10Y) |
| V4 | - | 10.8 | Percentile(10Y) Flipped |
| V5 | - | 83.3 | Percentile(5Y) |
| V7 | - | 99.6 | Zscore(10Y) |
| V8 | - | 16.2 | Zscore(10Y) |

---

## Fuel Score Formula

```python
# Step 1: Base weight
w_i* = |IC_i|

# Step 2: Stability penalty
s_i = min(1, (|IC_high| + |IC_low|) / (2 * |IC_full|))

# Step 3: Normalize
w_i = (w_i* × s_i) / Σ(w_j* × s_j)

# Step 4: Weighted sum
FuelScore = Σ(w_i × fuel_i)  # 0-100 range
```

---

## Signal Interpretation

| Fuel Score Range | Signal | Interpretation |
|------------------|--------|----------------|
| 80-100 | **EXTREME HIGH** | 极端高风险，多因子共振 |
| 60-80 | HIGH | 高风险，需警惕 |
| 40-60 | NEUTRAL | 中性 |
| 20-40 | LOW | 低风险 |
| 0-20 | **EXTREME LOW** | 极端低风险，安全期 |

---

*Version: 3.0*
*Framework: Unified Fuel Score (Factor-Specific Transforms)*
*Data: Lagged (release lag adjusted)*
