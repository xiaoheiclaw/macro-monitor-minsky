# V7 Shiller PE (CAPE)

**Status: REJECTED (AUC < 0.6)**

Shiller 周期调整市盈率 = S&P 500 Price / 10-Year Avg Inflation-Adjusted Earnings

## 验证结果 (2025-12-29)

### Transform Comparison

| Transform | Full IC | AUC (15%) | AUC (20%) | Status |
|-----------|---------|-----------|-----------|--------|
| **Percentile (5Y)** | 0.045 | 0.531 | 0.590 | **RANDOM** |
| Percentile (10Y) | -0.130 | 0.536 | 0.540 | RANDOM |
| Z-score (Level) | -0.166 | 0.559 | 0.570 | WEAK |
| Δ12M (YoY) | 0.064 | 0.510 | 0.663 | RANDOM |
| ΔΔ12M (Acceleration) | 0.177 | 0.566 | 0.635 | WEAK |
| 12M Rolling Slope | 0.041 | 0.513 | 0.640 | RANDOM |
| **Stress Move (Z-score)** | 0.123 | 0.537 | **0.715** | RANDOM/WEAK |
| Regime Shift Signal | 0.139 | 0.545 | 0.600 | RANDOM |

### 关键发现

1. **所有 Transform AUC (15%) < 0.6**: 没有一个变换能有效预测 15% 回撤
2. **20% 回撤稍好**: Stress Move AUC=0.715, 但 15% 阈值下仍为 0.537
3. **低利率环境下有信号**: Low Rate IC 显著为负 (-0.35 ~ -0.43)
4. **高利率环境下无效**: High Rate IC ≈ 0 或正值

### Quintile 分析

| Transform | Q1 Crash | Q5 Crash | Q5-Q1 | 单调性 |
|-----------|----------|----------|-------|--------|
| Percentile (5Y) | 43.8% | 24.1% | -19.7% | 无 |
| Percentile (10Y) | 47.6% | 47.5% | -0.1% | 无 |
| Z-score (Level) | 52.5% | 60.7% | +8.2% | 无 |
| Δ12M | 62.3% | 55.7% | -6.6% | 无 |

**观察**: Quintile 崩盘率没有明显单调关系，各分位崩盘率差异不稳定。

### 利率环境分析

| Transform | Full IC | High Rate IC | Low Rate IC |
|-----------|---------|--------------|-------------|
| Percentile (10Y) | -0.119 | +0.093 | **-0.345** |
| Z-score (Level) | -0.164 | +0.021 | **-0.372** |
| Δ12M | -0.069 | +0.075 | **-0.435** |

**关键发现**: CAPE 只在**低利率环境**下有负 IC（高 CAPE → 低回报），在高利率环境下完全失效。

## 当前状态 (2025-12)

| 指标 | 值 | 解读 |
|------|-----|------|
| CAPE Raw | 38.5 | 历史高位 |
| 10Y Percentile | 95%+ | 极端高估 |
| vs 均值 (17.7) | +117% | 远超均值 |

**但这意味着什么？** 根据验证结果:
- 高 CAPE 不能预测短期崩盘 (AUC ≈ 0.5)
- 高 CAPE 可能意味着长期回报较低（但这不在本验证范围内）

## 与 V4 对比

| 因子 | Best AUC (15%) | Best AUC (20%) | Status |
|------|----------------|----------------|--------|
| V4 ICR (Δ4Q) | **0.808** | **0.839** | **APPROVED** |
| V7 CAPE | 0.566 | 0.715 | REJECTED |

V4 在企业信用压力上有强预测力，V7 则没有。

## 使用建议

### 不应该用于

- **危机预警**: AUC < 0.6，无法有效预测 15% 回撤
- **短期择时**: 高 CAPE 不等于即将崩盘
- **高利率环境**: IC ≈ 0，完全无效

### 可能适用于

- **低利率环境下的长期配置参考**: IC = -0.35 ~ -0.43
- **估值背景参考**: 了解当前市场估值水平
- **10年期回报预测**: CAPE 与 10 年期回报有明确负相关（但需要另外验证）

## 数据源

| Series | 说明 |
|--------|------|
| CAPE | Shiller PE Ratio (Robert Shiller) |

- **Source**: Robert Shiller / Yale
- **Frequency**: Monthly
- **Release Lag**: 0 months (实时)
- **History**: 1881-present (144年)

## 文件说明

| 文件 | 说明 |
|------|------|
| `test_v7_change_based.py` | 验证脚本 |
| `V7_CHANGE_BASED_REPORT.md` | 详细验证报告 |
| `all_transforms_data.csv` | Transform 数据 |

### 图表

| 图表 | 说明 |
|------|------|
| `V7_SPX_PCTL_CHANGE_COMBINED.png` | SPX + Level + Change 综合图 |
| `05_rate_regime_ic.png` | 利率环境 IC 分析 |
| `08_risk_target_auc.png` | AUC 对比分析 |
| `09_quintile_analysis.png` | Quintile 分析 |

---

## 结论

**V7 Shiller PE (CAPE) 作为危机预警因子验证为 REJECTED**

| Metric | Value | 标准 | 结果 |
|--------|-------|------|------|
| Best AUC (15%) | 0.566 | > 0.65 | **FAIL** |
| Best AUC (20%) | 0.715 | > 0.65 | PASS (仅20%阈值) |
| Quintile 单调性 | 无 | 需要 | **FAIL** |
| 高利率有效性 | IC ≈ 0 | 需要正/负 IC | **FAIL** |

### 核心问题

1. **预测能力弱**: 所有 Transform 的 AUC (15%) 都 < 0.6
2. **无单调关系**: Quintile 崩盘率没有随 CAPE 单调变化
3. **环境依赖强**: 只在低利率环境下有微弱信号
4. **长周期 vs 短周期**: CAPE 可能预测 10 年回报，但不能预测 12 个月回撤

### 最终定位

```
# V7 CAPE 不纳入危机预警系统
standalone_signal = False
fuel_factor = False  # 验证失败，不作为 Fuel

# 仅作为背景参考
background_reference = True
use_case = "长期资产配置参考 (非择时)"
```

---

*Version: 3.0*
*Created: 2025-12-24*
*Updated: 2025-12-29 (V4-style validation - REJECTED)*
*Best AUC: 0.715 (20% threshold only), 0.566 (15% threshold)*
