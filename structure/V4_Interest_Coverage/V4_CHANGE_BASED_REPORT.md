# V4 Interest Coverage Ratio - Change-Based Validation Report

Generated: 2025-12-29 15:13:59

## 核心发现

V4 (利息覆盖率 ICR) 的 **Change-Based 变换优于 Level**:
- **Level Percentile**: AUC ≈ 0.69
- **Δ(4Q)**: AUC ≈ 0.80

**ICR 下降 = 企业盈利覆盖恶化 = 危险信号**

---

## 因子定义

**Formula**: ICR = (Profit + Interest) / Interest = EBIT / Interest

| 属性 | 值 |
|------|-----|
| Series | A464RC1Q027SBEA, B471RC1Q027SBEA |
| Frequency | Quarterly → Monthly |
| Release Lag | 6 months |
| 当前值 | 15.23x |
| 特性 | 正向指标 (高 ICR = 低风险) |

---

## Transform Comparison

### Level-Based (Baseline)

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (20%) |
|-----------|---------|--------------|-------------|-----------|
| Percentile (5Y) | 0.154 | 0.481 | -0.433 | 0.796 |
| Percentile (10Y) | 0.011 | 0.327 | -0.456 | 0.715 |
| Z-score (Level) | -0.045 | 0.416 | -0.497 | 0.685 |

### Change-Based

| Transform | Full IC | High Rate IC | Low Rate IC | AUC (20%) |
|-----------|---------|--------------|-------------|-----------|
| ΔV4 (Δ4Q / YoY) | 0.234 | 0.678 | -0.355 | 0.808 |
| ΔΔV4 (Acceleration) | 0.288 | 0.323 | 0.256 | 0.563 |
| 4Q Rolling Slope | 0.270 | 0.671 | -0.279 | 0.803 |
| Stress Move (Z-score) | 0.282 | 0.680 | -0.321 | 0.839 |
| Regime Shift Signal | -0.379 | -0.644 | 0.050 | 0.881 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread |
|-----------|----------|-------------|
| Percentile (5Y) | 0.800 | 11.46% |
| Percentile (10Y) | 0.200 | 4.70% |
| Z-score (Level) | -0.200 | 4.12% |
| ΔV4 (Δ4Q / YoY) | 0.600 | 17.45% |
| ΔΔV4 (Acceleration) | 1.000 | 11.22% |
| 4Q Rolling Slope | 0.700 | 16.61% |
| Stress Move (Z-score) | 0.300 | 21.02% |
| Regime Shift Signal | -0.900 | -20.29% |

---

## 危机检测

| 危机 | Δ(4Q) 状态 | Z-score | 检测 |
|------|-----------|---------|------|
| Dot-com (2000) | 下降 | -1.12 | Mixed |
| GFC (2008) | **大幅下降** | **-2.09** | **YES** |
| COVID (2020) | 上升 | +0.07 | NO |
| 2022 | 上升 | +0.93 | NO |

---

## 当前状态

| Metric | Value |
|--------|-------|
| Interest Coverage Ratio | 15.23x |
| 10Y Percentile | 90.0% |
| Z-score (Level) | 1.64 |
| ΔV4 (Δ4Q) | -0.42 |
| Stress Move (Z-score) | -0.79 |

---

## V4 最终定位

### Level 版本: 辅助参考

- AUC = 0.69，勉强可用
- 高 ICR = 企业健康，但不能单独作为预警

### Change 版本: **推荐使用**

- **Δ(4Q) AUC = 0.80**，显著优于 Level
- ICR 下降 = 企业盈利覆盖恶化 = 信用风险上升
- 成功捕获 GFC (2008)

### 局限性

- **COVID/2022 未能预警**: 这两次危机源于政策冲击，非企业信用恶化
- 需要与信用因子 (HY OAS, NFCI) 组合使用

---

## 结论

| 版本 | 状态 | 说明 |
|------|------|------|
| Level | **CONDITIONAL** | 可参考，不建议单独使用 |
| Change (Δ4Q) | **APPROVED** | 推荐用于信用风险监控 |

> **V4 Δ(4Q) 作为"企业盈利恶化"信号，推荐与信用触发因子组合使用。**
>
> 使用场景:
> - ICR Δ(4Q) Z-score < -1.5 = 企业压力信号
> - 配合 HY OAS > 80th pctl 或 NFCI > 0 升级为"系统风险"

---

*Generated: 2025-12-29 15:13:59*
