# V5 TDSP - Change-Based Validation Report

Generated: 2025-12-29 15:58:20

## 核心发现

V5 (家庭债务偿还比率 TDSP) 的验证结果:
- **Level Percentile**: AUC ≈ 0.741
- **Best Change**: AUC ≈ 0.684 (delta_4q)

**TDSP 方向解读**:
- TDSP 上升 = 家庭债务负担加重 = 潜在风险
- TDSP 下降 = 家庭去杠杆 = 安全

---

## 因子定义

**Formula**: TDSP = Household Debt Service Payments / Disposable Personal Income

| 属性 | 值 |
|------|-----|
| Series | TDSP |
| Frequency | Quarterly → Monthly |
| Release Lag | 3 months |
| 当前值 | 11.25% |
| 特性 | 正向风险指标 (高 TDSP = 高风险) |

---

## Transform Comparison

### Level-Based (Baseline)

| Transform | Full IC | High Rate IC | Low Rate IC | AUC |
|-----------|---------|--------------|-------------|-----|
| pctl_5y | -0.256 | -0.128 | 0.119 | 0.741 |
| pctl_10y | -0.272 | -0.105 | -0.156 | 0.716 |
| zscore_level | -0.253 | 0.040 | -0.076 | 0.689 |

### Change-Based

| Transform | Full IC | High Rate IC | Low Rate IC | AUC |
|-----------|---------|--------------|-------------|-----|
| delta_4q | -0.204 | 0.043 | 0.135 | 0.684 |
| delta_delta | 0.060 | 0.045 | 0.182 | 0.562 |
| slope_4q | -0.146 | 0.047 | 0.223 | 0.667 |
| delta_zscore | -0.198 | -0.077 | 0.115 | 0.672 |
| consecutive_increases | -0.011 | -0.026 | 0.211 | 0.639 |

---

## 危机检测

| 危机 | 10Y Pctl | Δ4Q | Δ Z-score | 连续上升 |
|------|----------|-----|-----------|----------|
| Dot-com | 74.3% | 0.25 | 0.81 | 3.0 |
| GFC | 100.0% | 0.45 | 0.06 | 3.4 |
| COVID | 16.4% | -0.05 | 0.69 | 1.2 |
| 2022 | 4.1% | -1.00 | -1.08 | 1.2 |

---

## 当前状态

| Metric | Value |
|--------|-------|
| TDSP Raw | 11.25% |
| 10Y Percentile | 42.5% |
| Z-score (Level) | 0.17 |
| Δ4Q | 0.090 |
| Stress Move (Z-score) | 0.17 |

---

## V5 最终定位

### 问题诊断

1. **TDSP 已经结构性下降**: 2008年后持续去杠杆
2. **当前处于历史低位**: 10Y Percentile = 42.5%
3. **Level 指标失效**: COVID/2022 时家庭负担低，无预警能力

### Change 版本分析

- Change-Based transforms 检测 TDSP **上升趋势**
- 如果家庭负担开始反弹，Change 指标会比 Level 更早发出信号

### 适用场景

- **债务周期见顶**: 当 TDSP 从低位开始上升
- **利率上升环境**: 高利率 → TDSP 上升 → 家庭压力
- **不适用**: 外生冲击型危机 (COVID)

### 局限性

- 当前 TDSP 处于历史低位，Level 指标暂时无效
- 需要 TDSP 开始上升趋势才能产生 Change 信号
- 不能预警非债务驱动的危机

---

## 结论

| 版本 | 状态 | 说明 |
|------|------|------|
| Level | **REJECTED** | TDSP 处于历史低位，Level 无效 |
| Change | **CONDITIONAL** | 可监控上升趋势，但当前无信号 |

> **V5 TDSP 当前处于休眠状态**
>
> - Level 指标因 TDSP 历史低位而失效
> - Change 指标可用于监控 TDSP 反弹
> - 当 Δ(4Q) Z-score > 1.5 时发出警告

---

*Generated: 2025-12-29 15:58:20*
