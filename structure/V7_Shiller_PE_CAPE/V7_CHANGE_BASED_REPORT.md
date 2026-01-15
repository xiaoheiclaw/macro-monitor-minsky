# V7 Shiller PE (CAPE) - Change-Based Validation Report

Generated: 2025-12-29 21:46:26

## 核心发现

V7 (CAPE) 的验证结果：

| Metric | Level | Change |
|--------|-------|--------|
| Best AUC (15%) | 0.559 | 0.566 |

---

## 因子定义

**Formula**: CAPE = S&P 500 Price / 10-Year Avg Inflation-Adjusted Earnings

| 属性 | 值 |
|------|-----|
| Source | Robert Shiller |
| Frequency | Monthly |
| Release Lag | 0 months (实时) |
| 当前值 | 38.5 |
| 特性 | 逆向指标 (高 CAPE = 高风险) |

---

## Transform Comparison

### Level-Based

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (15%) |
|-----------|---------|--------------|-------------|-----------|
| Percentile (5Y) | -0.097 | 0.014 | -0.346 | 0.531 |
| Percentile (10Y) | -0.119 | 0.093 | -0.345 | 0.536 |
| Z-score (Level) | -0.164 | 0.021 | -0.372 | 0.559 |

### Change-Based

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (15%) |
|-----------|---------|--------------|-------------|-----------|
| Δ12M (YoY) | -0.069 | 0.075 | -0.435 | 0.510 |
| ΔΔ12M (Acceleration) | 0.135 | 0.209 | -0.146 | 0.566 |
| 12M Rolling Slope | -0.050 | 0.117 | -0.429 | 0.513 |
| Stress Move (Z-score) | -0.007 | 0.126 | -0.418 | 0.537 |
| Regime Shift Signal | 0.134 | 0.354 | -0.227 | 0.545 |

### Quintile Analysis

| Transform | Spearman | Q5-Q1 Crash Spread |
|-----------|----------|-------------------|
| Percentile (5Y) | -0.100 | -19.6% |
| Percentile (10Y) | -0.400 | -0.1% |
| Z-score (Level) | -0.300 | +8.2% |
| Δ12M (YoY) | 0.400 | -6.6% |
| ΔΔ12M (Acceleration) | 0.900 | -23.0% |
| 12M Rolling Slope | 0.800 | +3.3% |
| Stress Move (Z-score) | 0.500 | -8.2% |
| Regime Shift Signal | 0.700 | -8.2% |

---

## 当前状态

| Metric | Value |
|--------|-------|
| CAPE Raw | 38.5 |
| 10Y Percentile | 95.8% |
| Z-score (Level) | 1.98 |
| Δ12M | 7.00 |
| Stress Move (Z-score) | 1.24 |

---

## V7 定位

### 验证结论

基于 AUC 和 Quintile 分析:

1. **Level vs Change**: 待验证结果确定
2. **预测能力**: AUC > 0.65 为有效, < 0.55 为无效
3. **Q5-Q1 Crash Spread**: > 5% 为显著差异

### 使用建议

- **长期配置参考**: CAPE 与 10 年期回报有明确负相关
- **短期择时**: 不推荐单独使用
- **与其他因子组合**: 作为估值背景参考

---

*Generated: 2025-12-29 21:46:26*
