# V9 CRE Lending Standards - Validation Report

Generated: 2025-12-30 16:25:10

## Factor Definition

**Series**: SLOOS CRE Lending Standards (Equal-Weight Average)
- DRTSCLCC: Construction & Land Development
- DRTSCILM: Multifamily
- DRTSCIS: Nonfarm Nonresidential

| 属性 | 值 |
|------|-----|
| Units | Net % Tightening |
| Frequency | Quarterly |
| Data Start | 1990 |
| Release Lag | 1 month |

**机制**: 银行收紧 CRE 贷款标准 = 信贷紧缩信号 = 危机前兆

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **V9 Level** | **6.33** | GREEN |
| **Z-score (10Y)** | **-0.14** | GREEN |

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward MDD

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Z-score (10Y) | 0.187 | 0.0014 | -0.061 | 0.497 |
| Percentile (10Y) | 0.362 | 0.0000 | 0.296 | 0.521 |
| Percentile (5Y) | 0.131 | 0.0271 | -0.231 | 0.492 |
| U-Shape |Pctl-50| | 0.169 | 0.0107 | 0.326 | 0.008 |
| Δ4Q (YoY) | 0.072 | 0.2107 | -0.144 | 0.406 |
| Stress Move (Δ4Q Z-score) | 0.183 | 0.0022 | -0.088 | 0.533 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Z-score (10Y) | 0.670 | 0.640 | 0.749 |
| Percentile (10Y) | 0.524 | 0.483 | 0.605 |
| Percentile (5Y) | 0.670 | 0.599 | 0.740 |
| U-Shape |Pctl-50| | 0.506 | 0.549 | 0.750 |
| Δ4Q (YoY) | 0.510 | 0.475 | 0.690 |
| Stress Move (Δ4Q Z-score) | 0.478 | 0.448 | 0.636 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Z-score (10Y) | 0.100 | 0.42% | 0.10 |
| Percentile (10Y) | 0.700 | 13.14% | 0.70 |
| Percentile (5Y) | -0.200 | 0.88% | 0.20 |
| U-Shape |Pctl-50| | 0.600 | 3.01% | 0.60 |
| Δ4Q (YoY) | -0.600 | -3.20% | 0.60 |
| Stress Move (Δ4Q Z-score) | 0.100 | 1.52% | 0.10 |

---

## Best Transform: U-Shape |Pctl-50|

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.549 | > 0.65 | FAIL |
| AUC (20%) | 0.750 | > 0.65 | **PASS** |
| IC (Full) | 0.169 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | 3.01% | > 10% | FAIL |
| Monotonicity | 0.60 | > 0.7 | FAIL |

---

## Historical Crisis Detection

| Crisis | V9 Level | Z-score | Signal Type | Detection |
|--------|----------|---------|-------------|-----------|
| 2000 Dot-com | ~8 | ~0.3 | Neutral | ✗ |
| 2008 GFC | **>60** | **>2.0** | **Tightening** | **✓** |
| 2020 COVID | **>40** | **>2.0** | **Tightening** | **✓** |
| 2022 Rate Hike | **<-20** | **<-1.5** | **Over-Easing** | **✓** |

---

## Signal Logic

```python
def get_v9_signal(zscore):
    """
    V9 双向信号 - 区分收紧和放松的不同风险类型

    收紧 (Z > 1.5): 立即型风险 - 银行已观察到问题，信贷紧缩正在发生
    放松 (Z < -1.5): 延迟型风险 - 银行过度乐观，泡沫正在积累
    """
    if zscore > 1.5:
        return "CREDIT_TIGHTENING_SHOCK"   # 立即型风险：信贷紧缩冲击
    elif zscore < -1.5:
        return "CREDIT_EASING_DISTORTION"  # 延迟型风险：信贷扭曲/泡沫
    elif zscore > 1.0:
        return "YELLOW_TIGHTENING"         # 收紧中，需观察
    elif zscore < -1.0:
        return "YELLOW_EASING"             # 过度放松中，需观察
    else:
        return "GREEN"                     # 正常区间，低风险
```

### Signal Interpretation

| V9 Z-score | Signal | Risk Type | Interpretation |
|------------|--------|-----------|----------------|
| Z > 1.5 | **CREDIT_TIGHTENING_SHOCK** | 立即型 | 银行严重收紧贷款，信贷危机正在发生 |
| Z < -1.5 | **CREDIT_EASING_DISTORTION** | 延迟型 | 银行过度放松，泡沫风险积累中 |
| 1.0 < Z < 1.5 | YELLOW_TIGHTENING | 预警 | 信贷收紧趋势，需密切观察 |
| -1.5 < Z < -1.0 | YELLOW_EASING | 预警 | 信贷过度宽松，潜在泡沫 |
| \|Z\| < 1.0 | GREEN | 正常 | 信贷条件正常 |

### 两种风险的本质区别

| 特征 | TIGHTENING_SHOCK | EASING_DISTORTION |
|------|------------------|-------------------|
| **时效性** | 立即型 (3-6个月) | 延迟型 (12-24个月) |
| **机制** | 银行已看到风险，主动收紧 | 银行过度乐观，风险在积累 |
| **历史案例** | 2008 GFC, 2020 COVID | 2021-2022 (放松后崩盘) |
| **应对策略** | 立即降低风险敞口 | 建立防御仓位，等待触发 |

---

## Combination with Other Factors

```python
# ==========================================
# V9 TIGHTENING_SHOCK 组合 (立即型风险)
# ==========================================

# V9 + V4 组合: 信贷危机
if v9_signal == "CREDIT_TIGHTENING_SHOCK" and v4_signal == "RED":
    # 银行收紧贷款 + 企业盈利恶化 = 信贷危机
    credit_crisis_risk = "CRITICAL"
    action = "立即降低风险敞口"

# V9 + V8 组合: 杠杆崩塌
if v9_signal == "CREDIT_TIGHTENING_SHOCK" and v8_signal == "RED":
    # 银行收紧 + 杠杆过高 = 强制平仓风险
    leverage_risk = "CRITICAL"
    action = "立即减仓"

# ==========================================
# V9 EASING_DISTORTION 组合 (延迟型风险)
# ==========================================

# V9 过度放松 + V8 杠杆急升: 泡沫形成
if v9_signal == "CREDIT_EASING_DISTORTION" and v8_signal == "RED":
    # 信贷宽松 + 杠杆堆积 = 泡沫正在形成
    bubble_risk = "HIGH"
    action = "建立防御仓位，但不必立即减仓"
    timing = "12-24个月内可能出现调整"

# V9 过度放松 单独: 中期预警
if v9_signal == "CREDIT_EASING_DISTORTION":
    # 银行过度乐观，风险在积累
    bubble_warning = "ELEVATED"
    action = "提高警惕，关注其他触发因素"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| DRTSCLCC | CRE - Construction & Land | FRED/SLOOS |
| DRTSCILM | CRE - Multifamily | FRED/SLOOS |
| DRTSCIS | CRE - Nonfarm Nonres | FRED/SLOOS |

---

*Version: 1.0*
*Validated: 2025-12-30*
*Framework: V1 Complete Validation*
