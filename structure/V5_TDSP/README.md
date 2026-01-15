# V5 TDSP - Household Debt Service Ratio

**Status: REJECTED (Structural Decline)**

家庭债务偿还占可支配收入比例 (FRED: TDSP)

## Change-Based 验证结果 (2025-12-29 更新)

### Transform Comparison

| Transform | Full IC | High Rate IC | AUC | Status |
|-----------|---------|--------------|-----|--------|
| **Percentile (5Y)** | **-0.256** | -0.128 | **0.741** | Best Level |
| Percentile (10Y) | -0.272 | -0.105 | 0.716 | Level |
| Z-score (Level) | -0.253 | 0.040 | 0.689 | Level |
| Δ4Q | -0.204 | 0.043 | 0.684 | Change |
| Slope (4Q) | -0.146 | 0.047 | 0.667 | Change |
| Δ Z-score | -0.198 | -0.077 | 0.672 | Change |

### 关键发现

1. **Level 优于 Change**: 5Y Pctl AUC=0.741 > Change AUC=0.67-0.68
2. **负IC = 高TDSP → 高MDD**: 高家庭负担 = 危险
3. **结构性失效**: TDSP 从2008年后持续下降，当前处于历史低位
4. **只对债务驱动型危机有效**: GFC ✓, Dot-com ✓, COVID ✗, 2022 ✗

### 危机检测

| 危机 | 10Y Pctl | Δ4Q | Δ Z-score | 检测 |
|------|----------|-----|-----------|------|
| Dot-com (2000) | 74% | +0.25 | +0.81 | YES (Level) |
| **GFC (2008)** | **100%** | +0.45 | +0.06 | **YES (Level)** |
| COVID (2020) | 16% | -0.05 | +0.69 | NO |
| 2022 | 4% | -1.00 | -1.08 | NO |

## 问题诊断

### 1. 结构性去杠杆

TDSP 在 2008 年达到历史高峰 (13.2%) 后，由于：
1. **低利率环境**: 降低债务成本
2. **家庭去杠杆化**: 减少负债
3. **消费者债务结构变化**: 更谨慎的借贷行为

### 2. 当前状态

| 指标 | 值 | 解读 |
|------|-----|------|
| TDSP Raw | 11.25% | 历史中低位 |
| 10Y Percentile | 42.5% | 低于中位数 |
| Δ4Q | +0.09 | 略有上升 |
| Δ Z-score | +0.17 | 正常范围 |

**当前解读**: TDSP处于历史低位，Level指标暂时失效。需要监控是否开始反弹上升趋势。

## 使用建议

### 适用场景

1. **债务驱动型危机**: 家庭过度负债 → 违约风险
2. **利率上升环境**: 高利率 → TDSP 被动上升 → 家庭压力
3. **信贷周期顶部**: 家庭杠杆见顶时的预警

### 不适用场景

- **外生冲击**: COVID 类突发事件
- **资产价格调整**: 2022 类估值收缩
- **当前环境**: TDSP 处于历史低位

### 监控条件

虽然当前Level指标失效，但建议监控以下条件：
- **Δ4Q Z-score > 1.5**: TDSP快速上升信号
- **10Y Pctl > 80%**: TDSP回到高位
- **连续上升 > 4季度**: 持续上升趋势

## 数据源

| Series | 说明 |
|--------|------|
| TDSP | Household Debt Service Payments as % of Disposable Income |

- **Source**: Federal Reserve Board
- **Frequency**: Quarterly
- **Release Lag**: ~3 months
- **History**: 1980-present

## 文件说明

| 文件 | 说明 |
|------|------|
| `V5_CHANGE_BASED_REPORT.md` | Change-Based 完整验证报告 |
| `V5_VALIDATION_10Y.md` | 原始 Level 验证报告 |
| `test_v5_change_based.py` | Change-Based 验证脚本 |
| `test_v5_tdsp.py` | 原始验证脚本 |
| `all_transforms_data.csv` | 所有变换数据 (月度) |
| `transform_results.csv` | Transform 对比结果 |

### 图表

| 图表 | 说明 |
|------|------|
| `V5_SPX_LEVEL_CHANGE_COMBINED.png` | SPX + Level + Change 综合图 |
| `05_rate_regime_ic.png` | 利率环境下 IC 分析 |
| `08_risk_target_auc.png` | AUC 对比分析 |

---

## 结论

V5 TDSP（Household Debt Service Ratio）**作为通用危机预警因子验证失败**，原因是其机制高度特定：它主要刻画**家庭部门利息负担与住房信用周期脆弱性**，对 GFC-like 信用危机有效，但对估值/外生冲击/久期再定价型危机（Dot-com、COVID、2022）缺乏预警能力。

因此 **TDSP 不应作为独立风险警报纳入系统**，而应作为 Fuel 层的"**家庭部门杠杆敏感度**"背景变量，在 Trigger（失业上升、房贷利率跳升、房价动能转负）出现时用于**放大风险评估**。

| 版本 | 状态 | 说明 |
|------|------|------|
| Level | **REJECTED** | 当前TDSP低位，Level失效 |
| Change | **CONDITIONAL** | 可监控上升趋势 |

### 定位

```
# 不作为独立预警
standalone_signal = False

# 作为 Fuel 背景变量
fuel_household_leverage = clamp(tdsp_pctl_10y / 100, 0, 1)

# 当 Trigger 出现时放大风险
triggers = [
    "unemployment_rising",      # 失业率上升
    "mortgage_rate_spike",      # 房贷利率跳升
    "home_price_momentum_neg"   # 房价动能转负
]

# 风险放大
if any(trigger) and fuel_household_leverage > 0.7:
    risk_amplifier = 1.5
```

---

*Version: 2.0*
*Created: 2025-12-25*
*Updated: 2025-12-29 (Change-Based Validation)*
*Best Transform: Percentile (5Y) - AUC=0.741 (当Level有效时)*
