# V5 TDSP (Household Debt Service Ratio) - Validation Report

Generated: 2025-12-30 22:01:37

## Factor Definition

**Series**: TDSP - Household Debt Service Payments as % of Disposable Personal Income

| 属性 | 值 |
|------|-----|
| Units | Percent (%) |
| Frequency | Quarterly |
| Data Start | 1980 |
| Release Lag | 3 months |

**机制**: 高债务负担 = 家庭脆弱 = 对冲击敏感

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **TDSP Raw** | **11.25%** | - |
| **10Y Percentile** | **42.5%** | **NORMAL** |
| **Z-score (Level)** | **0.17** | - |
| **Δ4Q Z-score** | **0.17** | - |

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward MDD

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Percentile (5Y) | -0.312 | 0.0000 | -0.597 | 0.161 |
| Percentile (10Y) | -0.344 | 0.0000 | -0.609 | 0.130 |
| Z-score (Level) | -0.277 | 0.0000 | -0.444 | 0.231 |
| Δ4Q Z-score (YoY Change) | -0.171 | 0.0028 | -0.006 | -0.068 |
| Δ8Q Z-score (2Y Change) | -0.043 | 0.4593 | 0.302 | 0.161 |
| YoY % Change | -0.241 | 0.0000 | -0.117 | -0.037 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Percentile (5Y) | 0.584 | 0.646 | 0.737 |
| Percentile (10Y) | 0.565 | 0.677 | 0.715 |
| Z-score (Level) | 0.548 | 0.662 | 0.688 |
| Δ4Q Z-score (YoY Change) | 0.625 | 0.601 | 0.674 |
| Δ8Q Z-score (2Y Change) | 0.586 | 0.516 | 0.593 |
| YoY % Change | 0.595 | 0.608 | 0.675 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Percentile (5Y) | -0.500 | -25.52% | 0.50 |
| Percentile (10Y) | -0.400 | -22.92% | 0.40 |
| Z-score (Level) | -0.600 | -19.45% | 0.60 |
| Δ4Q Z-score (YoY Change) | -0.700 | -9.84% | 0.70 |
| Δ8Q Z-score (2Y Change) | -0.700 | -4.61% | 0.70 |
| YoY % Change | -0.600 | -12.44% | 0.60 |

---

## Best Transform: Percentile (5Y)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.646 | > 0.65 | FAIL |
| AUC (20%) | 0.737 | > 0.65 | **PASS** |
| IC (Full) | -0.312 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | -25.52% | > 10% | **PASS** |
| Monotonicity | 0.50 | > 0.7 | FAIL |

---

## Signal Logic

```python
def get_v5_signal(pctl_10y):
    '''
    V5 TDSP 家庭债务风险信号

    高债务负担 = 家庭脆弱 = 对冲击敏感
    '''
    if pctl_10y > 80:
        return "HIGH_DEBT"     # 家庭债务负担历史高位
    elif pctl_10y > 60:
        return "ELEVATED"      # 偏高，需关注
    elif pctl_10y > 40:
        return "NORMAL"        # 正常范围
    else:
        return "LOW_DEBT"      # 家庭债务负担低，相对安全
```

### Signal Interpretation

| V5 10Y Pctl | Signal | Risk Type | Interpretation |
|-------------|--------|-----------|----------------|
| Pctl > 80% | **HIGH_DEBT** | 高风险 | 家庭债务历史高位，对冲击敏感 |
| 60-80% | ELEVATED | 观察 | 债务偏高，需监控 |
| 40-60% | NORMAL | 正常 | 债务负担正常 |
| < 40% | LOW_DEBT | 安全 | 债务负担低，韧性强 |

### 核心机制

**高债务负担 = 家庭脆弱**

当家庭债务负担高时:
1. 可支配收入减少，消费能力下降
2. 对利率上升更敏感
3. 对收入冲击（失业）缺乏缓冲

**特点**:
- 主要预警**信用危机**（如GFC）
- 对**估值泡沫**（Dot-com）和**外生冲击**（COVID）预警能力弱
- 建议作为**背景变量**而非独立预警

---

## Combination with Other Factors

```python
# V5 + V8 组合: 杠杆叠加风险
if v5_signal == "HIGH_DEBT" and v8_signal == "LEVERAGE_SURGE":
    # 家庭+投资者双高杠杆 = 系统性脆弱
    system_fragility = "CRITICAL"
    action = "降低风险敞口"

# V5 + 利率上升
if v5_signal == "HIGH_DEBT" and fed_hiking:
    # 高债务 + 加息 = 家庭压力上升
    household_stress = "HIGH"
    action = "关注消费板块"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| TDSP | Household Debt Service Payments as % of DPI | FRED/Federal Reserve |

---

*Version: 1.0*
*Validated: 2025-12-30*
*Framework: V1 Complete Validation*
