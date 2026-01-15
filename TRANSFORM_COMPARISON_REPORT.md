# Transform Comparison Report

Generated: 2026-01-04 13:30:30

## Summary

Testing 4 transform variants for each factor:
- `pctl_5y`: 5-year rolling percentile
- `pctl_10y`: 10-year rolling percentile
- `zscore_5y`: 5-year rolling Z-score
- `zscore_10y`: 10-year rolling Z-score

### Best Transform per Factor

| Factor | Name | Current | Best IC | IC Score | Best AUC | AUC Score |
|--------|------|---------|---------|----------|----------|-----------|
| V1 | ST Debt Ratio | perc_10y | zscore_10y | 0.1244 | zscore_10y | 0.1335 |
| V4 | Interest Coverage (ICR) | perc_10y (flip) | zscore_5y | 0.1880 | zscore_10y | 0.2053 |
| V5 | TDSP (Debt Service) | perc_5y | pctl_10y | 0.3013 | pctl_5y | 0.1557 |
| V7 | Shiller PE (CAPE) | zsco_10y | zscore_10y | 0.1347 | zscore_10y | 0.0647 |
| V8 | Margin Debt Ratio | zsco_10y | zscore_10y | 0.3584 | zscore_10y | 0.2144 |

---

## V1: ST Debt Ratio

**Current Configuration**: `perc_10y`

**Best IC Transform**: `zscore_10y` (score: 0.1244)
**Best AUC Transform**: `zscore_10y` (score: 0.1335)

### Detailed Comparison

| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |
|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|
| pctl_5y | 0.0564 | 0.0947 | 0.0029 | 0.3260 | 0.86 | 0.6191 | 0.0488 | 0.1191 |
| pctl_10y | 0.1159 | 0.2479 | 0.0045 | 0.0432 | 1.00 | 0.6216 | 0.1159 | 0.1216 |
| zscore_5y | 0.0748 | 0.1053 | 0.0329 | 0.1928 | 0.92 | 0.6269 | 0.0691 | 0.1269 |
| zscore_10y | 0.1244 | 0.2476 | 0.0098 | 0.0299 | 1.00 | 0.6335 | 0.1244 | 0.1335 |

### Recommendation

**Consider switching to `zscore_10y`** - optimal for both IC and AUC.

---

## V4: Interest Coverage (ICR)

**Current Configuration**: `perc_10y (flip)`

**Best IC Transform**: `zscore_5y` (score: 0.1880)
**Best AUC Transform**: `zscore_10y` (score: 0.2053)

### Detailed Comparison

| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |
|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|
| pctl_5y | -0.1775 | -0.4955 | 0.4084 | 0.0019 | 1.00 | 0.8043 | 0.1775 | 0.2042 |
| pctl_10y | -0.0439 | -0.3353 | 0.4323 | 0.4453 | 1.00 | 0.7248 | 0.0439 | 0.2005 |
| zscore_5y | -0.1880 | -0.5205 | 0.3526 | 0.0010 | 1.00 | 0.7693 | 0.1880 | 0.2024 |
| zscore_10y | 0.0070 | -0.3947 | 0.4726 | 0.9032 | 0.00 | 0.7072 | 0.0000 | 0.2053 |

### Recommendation

- IC optimized: `zscore_5y`
- AUC optimized: `zscore_10y`

Choose based on your priority:
- For return prediction: use IC-optimized
- For crash detection: use AUC-optimized

---

## V5: TDSP (Debt Service)

**Current Configuration**: `perc_5y`

**Best IC Transform**: `pctl_10y` (score: 0.3013)
**Best AUC Transform**: `pctl_5y` (score: 0.1557)

### Detailed Comparison

| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |
|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|
| pctl_5y | -0.2972 | -0.5091 | 0.1015 | 0.0000 | 1.00 | 0.7369 | 0.2972 | 0.1557 |
| pctl_10y | -0.3431 | -0.5488 | 0.0539 | 0.0000 | 0.88 | 0.7157 | 0.3013 | 0.1056 |
| zscore_5y | -0.3119 | -0.4541 | 0.0202 | 0.0000 | 0.76 | 0.7164 | 0.2372 | 0.1007 |
| zscore_10y | -0.2913 | -0.4443 | 0.1570 | 0.0000 | 1.00 | 0.6965 | 0.2913 | 0.0797 |

### Recommendation

- IC optimized: `pctl_10y`
- AUC optimized: `pctl_5y`

Choose based on your priority:
- For return prediction: use IC-optimized
- For crash detection: use AUC-optimized

---

## V7: Shiller PE (CAPE)

**Current Configuration**: `zsco_10y`

**Best IC Transform**: `zscore_10y` (score: 0.1347)
**Best AUC Transform**: `zscore_10y` (score: 0.0647)

### Detailed Comparison

| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |
|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|
| pctl_5y | -0.0423 | 0.0457 | -0.2667 | 0.4618 | 1.00 | 0.4032 | 0.0423 | 0.0338 |
| pctl_10y | -0.0903 | 0.0929 | -0.2877 | 0.1154 | 1.00 | 0.5370 | 0.0903 | 0.0370 |
| zscore_5y | -0.0972 | -0.0166 | -0.3306 | 0.0901 | 1.00 | 0.4337 | 0.0972 | 0.0144 |
| zscore_10y | -0.1347 | 0.0131 | -0.2970 | 0.0186 | 1.00 | 0.5647 | 0.1347 | 0.0647 |

### Recommendation

**Consider switching to `zscore_10y`** - optimal for both IC and AUC.

---

## V8: Margin Debt Ratio

**Current Configuration**: `zsco_10y`

**Best IC Transform**: `zscore_10y` (score: 0.3584)
**Best AUC Transform**: `zscore_10y` (score: 0.2144)

### Detailed Comparison

| Variant | IC_full | IC_high | IC_low | p-value | Stability | AUC_full | IC_score | AUC_score |
|---------|---------|---------|--------|---------|-----------|----------|----------|-----------|
| pctl_5y | -0.3575 | -0.4565 | -0.1758 | 0.0000 | 0.88 | 0.7018 | 0.3162 | 0.2018 |
| pctl_10y | -0.3967 | -0.4352 | -0.2529 | 0.0000 | 0.87 | 0.6957 | 0.3440 | 0.1957 |
| zscore_5y | -0.3325 | -0.4997 | -0.0467 | 0.0000 | 0.82 | 0.7099 | 0.2732 | 0.2099 |
| zscore_10y | -0.4266 | -0.4922 | -0.2246 | 0.0000 | 0.84 | 0.7144 | 0.3584 | 0.2144 |

### Recommendation

**Consider switching to `zscore_10y`** - optimal for both IC and AUC.

---

## Final Recommendations

Based on this analysis, consider updating `config.py` with:

```python
FACTOR_TRANSFORM = {
    'V1': {'type': 'zscore', 'window': 120},
    'V4': {'type': 'zscore', 'window': 60, 'flip': True},
    'V5': {'type': 'percentile', 'window': 120},
    'V7': {'type': 'zscore', 'window': 120},
    'V8': {'type': 'zscore', 'window': 120},
}
```
