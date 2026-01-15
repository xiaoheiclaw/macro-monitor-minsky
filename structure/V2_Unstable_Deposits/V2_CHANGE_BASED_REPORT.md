# V2 Unstable Deposits Ratio - Change-Based Validation Report

Generated: 2025-12-29 15:01:30

## 核心问题

V2 (不稳定存款比率) 存在**结构性断裂**:
- 2000/2008: **低比率**时崩盘 (Z < -1.5)
- 2020后: COVID刺激导致存款激增，结构完全改变
- 2022: **高比率**时无预警 (Z > +3)

**方向不一致**导致 Level 版本不可用。

### 关键观察: 2008年后结构性变化

**存款比例自2008年之后从未回到历史低位**:
- 2008年前: 存款比率在较低水平波动，低比率与风险相关
- 2008 GFC后: 存款比率大幅上升，从未回落
- 2020 COVID后: 再次激增，达到历史高位

这意味着:
1. **无样本外验证**: 2008年之后没有"低存款比率"的观测点
2. **"安全指标"失效**: 高存款比率本应代表稳定，但2022年崩盘时存款处于历史高位
3. **历史关系不可复制**: 2000/2008的"低→崩盘"模式在现代环境中无法验证

---

## 因子定义

**Formula**: WDDNS / DPSACBW027SBOG * 100 (活期存款 / 总存款)

| 属性 | 值 |
|------|-----|
| Frequency | Weekly → Monthly |
| Release Lag | 1 months |
| 当前值 | 35.96% |

---

## Transform Comparison

### Level-Based (Baseline)

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (20%) |
|-----------|---------|--------------|-------------|-----------|
| Percentile (5Y) | 0.363 | 0.459 | -0.008 | 0.717 |
| Percentile (10Y) | 0.374 | 0.462 | 0.015 | 0.706 |
| Z-score (Level) | 0.386 | 0.620 | -0.077 | 0.736 |

### Change-Based

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (20%) |
|-----------|---------|--------------|-------------|-----------|
| ΔV2 (Δ12M / YoY) | 0.320 | 0.384 | -0.016 | 0.670 |
| ΔΔV2 (Acceleration) | 0.030 | -0.031 | 0.055 | 0.504 |
| 12M Rolling Slope | 0.309 | 0.326 | -0.029 | 0.633 |
| Stress Move (Z-score) | 0.124 | -0.037 | 0.048 | 0.606 |
| Regime Shift Signal | 0.070 | -0.012 | 0.116 | 0.556 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread |
|-----------|----------|-------------|
| Percentile (5Y) | 0.900 | 14.53% |
| Percentile (10Y) | 0.700 | 14.55% |
| Z-score (Level) | 0.700 | 19.27% |
| ΔV2 (Δ12M / YoY) | 1.000 | 16.55% |
| ΔΔV2 (Acceleration) | 0.100 | 3.48% |
| 12M Rolling Slope | 0.900 | 15.39% |
| Stress Move (Z-score) | 0.500 | 7.92% |
| Regime Shift Signal | 0.800 | 9.44% |

---

## 当前状态

| Metric | Value |
|--------|-------|
| Unstable Deposits Ratio | 35.96% |
| 10Y Percentile | 100.0% |
| Z-score (Level) | 1.82 |
| ΔV2 (Δ12M) | 4.45% |
| Stress Move (Z-score) | 0.82 |

---

## V2 最终定位

### Level 版本: 不可用

由于**结构性断裂**，Level 版本在不同危机中方向不一致:
- 2000/2008: 低位崩盘 (low → crash)
- 2022: 高位无预警

**结论**: Level 版本不应使用。

### Change 版本: 待观察

Change-Based 变换可能捕捉"冲击"而非绝对位置，但需要更多验证。

---

## 结论

| 版本 | 状态 | 说明 |
|------|------|------|
| Level | **REJECTED** | 结构性断裂，方向不一致 |
| Change | **REJECTED** | AUC不如Level，无附加价值 |

> **V2 因结构性断裂不推荐使用。**
>
> 核心问题: **存款比例自2008年之后从未低过**
> - 2008年前的"低存款→高风险"关系无法在现代环境验证
> - 2020后存款激增至历史高位，2022崩盘时无任何预警
> - Level/Change两个版本均无法解决这个根本性问题
>
> **结论**: V2 作为结构层因子**完全失效**，不应纳入风险框架。

---

*Generated: 2025-12-29 15:01:30*
