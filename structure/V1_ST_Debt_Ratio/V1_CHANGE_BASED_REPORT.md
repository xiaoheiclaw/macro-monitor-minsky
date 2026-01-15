# V1 ST Debt Ratio - Change-Based Validation Report

Generated: 2025-12-29 14:22:26

## 核心理念

**Level 百分位对预警最不友好**。对同步/滞后指标，真正有用的是：
- ΔV1（Δ4Q / YoY 变化）
- ΔΔV1（二阶变化 / 加速度）
- 4Q 移动斜率

危机中最典型的特征不是"高"，而是**"短期快速跳升"**。

---

## 因子定义

**Series**: `BOGZ1FL104140006Q` - Nonfinancial Corporate Business; Short-Term Debt / Total Debt

| 属性 | 值 |
|------|-----|
| Frequency | Quarterly |
| Release Lag | 5 months |
| 当前值 | 29.50% |

---

## Transform Comparison

### IC (Information Coefficient)

| Transform | Full IC | High Rate IC | Low Rate IC |
|-----------|---------|--------------|-------------|
| ΔV1 (Δ4Q / YoY) | 0.035 | -0.005 | 0.201 |
| ΔΔV1 (Acceleration) | -0.153 | -0.099 | -0.190 |
| 4Q Rolling Slope | -0.027 | -0.066 | 0.126 |
| Stress Move (Z-score) | -0.009 | -0.135 | 0.275 |
| Regime Shift Signal | -0.191 | -0.215 | -0.102 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| ΔV1 (Δ4Q / YoY) | 0.533 | 0.499 | 0.595 |
| ΔΔV1 (Acceleration) | 0.497 | 0.533 | 0.471 |
| 4Q Rolling Slope | 0.531 | 0.513 | 0.610 |
| Stress Move (Z-score) | 0.520 | 0.503 | 0.590 |
| Regime Shift Signal | 0.501 | 0.531 | 0.583 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread |
|-----------|----------|-------------|
| ΔV1 (Δ4Q / YoY) | -0.600 | -1.11% |
| ΔΔV1 (Acceleration) | -0.900 | -5.44% |
| 4Q Rolling Slope | -0.400 | -2.02% |
| Stress Move (Z-score) | -0.200 | -4.38% |
| Regime Shift Signal | -0.300 | -1.74% |

---

## Best Transform: 4Q Rolling Slope

| Metric | Value |
|--------|-------|
| AUC (20% MDD) | 0.610 |
| Full IC | -0.027 |
| High Rate IC | -0.066 |

---

## 当前状态

| Metric | Value | Signal |
|--------|-------|--------|
| ST Debt Ratio | 29.50% | - |
| ΔV1 (Δ4Q / YoY) | -0.524 |  |
| Stress Move (Z-score) | -0.509 |  |
| Regime Shift Signal | 1.000 |  |

---

## 结论

- **Level百分位** (pctl_10y) 作为baseline对比
- **变化类变换** 预期有更好的预警价值
- **Stress Move**: ΔV1 > 2σ = 预警信号
- **Regime Shift**: 连续 2-3 季度上升 = 预警信号

---

*Generated: 2025-12-29 14:22:26*
