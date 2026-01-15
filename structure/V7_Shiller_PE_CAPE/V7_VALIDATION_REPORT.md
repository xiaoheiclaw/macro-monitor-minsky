# V7 Shiller PE (CAPE) - Validation Report

Generated: 2025-12-30 21:55:43 (Updated: 2025-12-30)

## Factor Definition

**Series**: Shiller Cyclically Adjusted PE Ratio (CAPE)
- Price / 10-Year Average Inflation-Adjusted Earnings

| 属性 | 值 |
|------|-----|
| Units | Ratio |
| Frequency | Monthly |
| Data Start | 1881 |
| Release Lag | 0 months (Real-time) |

**机制**: 高 CAPE = 高估值 → 高燃料存量 → 回撤深度放大器

**定位**: **Fuel (估值燃料)** - 不作为独立 Trigger，用于风险预算与 Trigger 放大

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **CAPE** | **38.5** | - |
| **Z-score (10Y)** | **1.98** | **EXTREME_HIGH** |
| **Risk Budget** | - | **CONSERVATIVE** |
| **Trigger Amplifier** | - | **2.0x** |

**当前系统输出**: 估值燃料处于极端高位，风险预算应保持保守；若出现信用利差扩大、动量转负或银行收紧等 Trigger，应快速升级为防御模式。

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward MDD

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Z-score (Level) | -0.540 | 0.0000 | -0.492 | -0.636 |
| Percentile (10Y) | -0.442 | 0.0000 | -0.481 | -0.464 |
| Percentile (5Y) | -0.431 | 0.0000 | -0.407 | -0.485 |
| Δ12M (YoY) | -0.298 | 0.0017 | -0.019 | -0.532 |
| Stress Move (Δ Z-score) | -0.288 | 0.0024 | -0.011 | -0.520 |
| U-Shape |Pctl-50| | -0.435 | 0.0000 | -0.481 | -0.458 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Z-score (Level) | 0.701 | 0.724 | 0.681 |
| Percentile (10Y) | 0.680 | 0.655 | 0.637 |
| Percentile (5Y) | 0.635 | 0.614 | 0.607 |
| Δ12M (YoY) | 0.645 | 0.646 | 0.576 |
| Stress Move (Δ Z-score) | 0.627 | 0.594 | 0.556 |
| U-Shape |Pctl-50| | 0.675 | 0.654 | 0.637 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Z-score (Level) | -0.700 | -24.78% | 0.70 |
| Percentile (10Y) | -0.900 | -19.54% | 0.90 |
| Percentile (5Y) | -1.000 | -20.34% | 1.00 |
| Δ12M (YoY) | -0.600 | -13.59% | 0.60 |
| Stress Move (Δ Z-score) | -0.600 | -14.87% | 0.60 |
| U-Shape |Pctl-50| | -0.900 | -19.54% | 0.90 |

---

## Best Transform: Z-score (Level)

**用于 Fuel Level / 风险预算**

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.724 | > 0.65 | **PASS** |
| AUC (20%) | 0.681 | > 0.65 | **PASS** |
| IC (Full) | -0.540 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | -24.78% | > 10% | **PASS** |
| Monotonicity | 0.70 | >= 0.7 | **PASS** (边界) |

**注**: Δ12M/Stress Move 仅用于监控估值加速，不作为独立信号。

---

## 关键发现

1. **CAPE Level (10Y Z-score) 对未来 12M MDD 具有显著预测力**
   - IC = -0.540 (p < 0.0001)
   - AUC@15% = 0.724, AUC@20% = 0.681
   - Q5-Q1 Spread = -24.78% (最高分位组崩盘率显著更高)

2. **CAPE 在高利率与低利率环境下均有效，但低利率期更强**
   - High Rate IC = -0.492
   - Low Rate IC = -0.636

3. **不适合作为短期择时 Trigger**
   - 高估值可能持续较长时间，单独使用会产生较高误报率与机会成本
   - 正确定位为 **Fuel (估值燃料)** 指标，用于风险预算与 Trigger 出现后的风险放大

---

## Signal Logic (Fuel + Amplifier)

### Fuel Level Signal

```python
def get_v7_fuel(zscore_level):
    """
    V7 CAPE Fuel Signal - 估值燃料存量

    用于风险预算，不作为独立 Trigger
    高估值 = 高燃料 → Trigger 出现时回撤更深、持续更久
    """
    if zscore_level > 1.5:
        return "EXTREME_HIGH"    # 极端高估
    elif zscore_level > 1.0:
        return "HIGH"            # 高估
    elif zscore_level < -1.5:
        return "EXTREME_LOW"     # 极端低估
    elif zscore_level < -1.0:
        return "LOW"             # 低估
    else:
        return "NEUTRAL"         # 中性
```

### Risk Budget

```python
def get_risk_budget(zscore_level):
    """
    基于估值燃料的风险预算系数

    返回 risk_cap: 风险预算乘数，不是绝对仓位
    具体仓位由策略自身的 risk unit / volatility targeting 转换
    """
    if zscore_level > 1.5:
        return {"level": "CONSERVATIVE", "risk_cap": 0.5}
    elif zscore_level > 1.0:
        return {"level": "CAUTIOUS", "risk_cap": 0.7}
    elif zscore_level < -1.0:
        return {"level": "AGGRESSIVE", "risk_cap": 1.2}
    else:
        return {"level": "NEUTRAL", "risk_cap": 1.0}
```

### Trigger Amplifier

```python
def trigger_amplifier(zscore_level, trigger_active: bool):
    """
    仅在 Trigger 出现时生效的放大系数

    Args:
        zscore_level: V7 CAPE Z-score
        trigger_active: 是否有 Trigger 信号 (V4/V8/V9 等)

    Returns:
        放大系数 (1.0-2.0)

    注意:
        - 只在 trigger_active=True 时生效
        - 多个 Fuel 的 Amplifier 不应无限叠加，建议设置总上限
    """
    if not trigger_active:
        return 1.0  # 无 Trigger 时不放大
    if zscore_level > 1.5:
        return 2.0    # 2倍放大
    elif zscore_level > 1.0:
        return 1.5    # 1.5倍放大
    else:
        return 1.0    # 无放大
```

### Signal Matrix

| Z-score | Fuel Level | Risk Cap | Amplifier (仅 Trigger 时) |
|---------|------------|----------|---------------------------|
| Z > 1.5 | **EXTREME_HIGH** | 0.5 | 2.0x |
| 1.0 < Z ≤ 1.5 | HIGH | 0.7 | 1.5x |
| -1.0 ≤ Z ≤ 1.0 | NEUTRAL | 1.0 | 1.0x |
| -1.5 ≤ Z < -1.0 | LOW | 1.2 | 1.0x |
| Z < -1.5 | EXTREME_LOW | 1.2 | 1.0x |

**注**: `risk_cap` 是风险预算系数，不是绝对仓位。具体仓位由策略的 volatility targeting 或 risk unit 转换。

---

## 使用建议

### 作为 Fuel (风险预算系数)

`risk_cap` 用于调整策略的风险预算上限：

| Fuel Level | risk_cap | 含义 |
|------------|----------|------|
| EXTREME_HIGH | 0.5 | 风险预算减半，建议持有对冲 |
| HIGH | 0.7 | 风险预算降低 30% |
| NEUTRAL | 1.0 | 正常风险预算 |
| LOW/EXTREME_LOW | 1.2 | 可适度提高风险预算 |

**生产公式**: `实际风险敞口 = 策略基础敞口 × risk_cap`

### 作为 Amplifier (触发放大器)

**仅在 Trigger 出现时生效**：

1. **生效条件**: `trigger_active = True` (V4/V8/V9 等发出信号)
2. **放大对象**: Trigger 的风险响应强度
3. **上限约束**: 多个 Fuel 的 Amplifier 不应无限叠加

```python
# 示例：多 Fuel 的 Amplifier 叠加上限
total_amplifier = min(
    v7_amplifier * v8_amplifier,  # 估值 × 杠杆
    MAX_AMPLIFIER_CAP  # 建议上限 3.0
)
```

### 不作为独立 Trigger

- CAPE 不单独发出"崩盘预警"
- 必须与 Trigger (V4, V8, V9 等) 联动
- 低估值区间提高长期预期收益，但短期可能继续下跌（价值陷阱）

---

## Combination with Other Factors

```python
# ==========================================
# V7 作为 Fuel / Amplifier
# ==========================================

# 与 V4 ICR 组合
if v4_signal == "RED" and v7_fuel == "EXTREME_HIGH":
    # 盈利恶化 + 极端高估 = 深度回撤
    action = "立即大幅减仓"
    expected_mdd = "可能超过 -30%"

# 与 V8 Margin Debt 组合
if v8_combined == "CRITICAL" and v7_fuel in ["HIGH", "EXTREME_HIGH"]:
    # 杠杆急升 + 高估值 = 系统性风险放大
    action = "立即清仓或重度对冲"

# 与 V9 CRE Lending 组合
if v9_signal == "CREDIT_TIGHTENING_SHOCK" and v7_fuel == "EXTREME_HIGH":
    # 信贷收紧 + 极端高估 = 2000/2008 式崩盘
    action = "立即进入防御模式"
    amplified_response = True

# ==========================================
# 低估值环境下的机会
# ==========================================

if v7_fuel == "EXTREME_LOW":
    # 长期配置机会，但需要 Trigger 确认底部
    opportunity = "长期买入机会"
    caveat = "短期可能继续下跌，等待 Trigger 确认"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| CAPE | Shiller PE Ratio | Robert Shiller / Yale |

---

*Version: 2.1*
*Validated: 2025-12-30*
*Framework: V1 Complete Validation*
*定位: Fuel (估值燃料) - 风险预算 + Trigger 放大器*
