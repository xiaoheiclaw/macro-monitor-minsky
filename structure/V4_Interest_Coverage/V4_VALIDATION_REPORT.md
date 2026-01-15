# V4 Interest Coverage Ratio (ICR) - Validation Report

Generated: 2025-12-30 22:23:07 (Updated: 2025-12-30)

## Factor Definition

**Series**: Interest Coverage Ratio = EBIT / Interest
- A464RC1Q027SBEA: Profit Before Tax (Nonfinancial Corp)
- B471RC1Q027SBEA: Net Interest (Nonfinancial Corp)

| 属性 | 值 |
|------|-----|
| Units | Ratio (x) |
| Frequency | Quarterly |
| Data Start | 1947 |
| Release Lag | 6 months |

**机制**: ICR下降 = 企业盈利覆盖恶化 = 信用风险上升

**定位**: **Trigger (企业信用压力)** - 作为独立触发信号

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **ICR** | **14.07x** | - |
| **Δ4Q Z-score** | **-1.43** | **ORANGE** |

**当前系统输出**: ICR明显下降，企业压力上升

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward MDD

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Percentile (5Y) | 0.179 | 0.0017 | 0.500 | -0.414 |
| Percentile (10Y) | 0.042 | 0.4636 | 0.338 | -0.433 |
| Z-score (Level) | -0.006 | 0.9213 | 0.428 | -0.462 |
| Δ4Q (YoY Change) | 0.273 | 0.0000 | 0.703 | -0.311 |
| Stress Move (Δ Z-score) | 0.321 | 0.0000 | 0.700 | -0.276 |
| Regime Shift Signal | -0.408 | 0.0000 | -0.682 | 0.040 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Percentile (5Y) | 0.284 | 0.240 | 0.204 |
| Percentile (10Y) | 0.398 | 0.346 | 0.284 |
| Z-score (Level) | 0.451 | 0.374 | 0.314 |
| Δ4Q (YoY Change) | 0.308 | 0.300 | 0.192 |
| Stress Move (Δ Z-score) | 0.277 | 0.262 | 0.161 |
| Regime Shift Signal | 0.687 | 0.729 | 0.882 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Percentile (5Y) | 0.800 | 11.46% | 0.80 |
| Percentile (10Y) | 0.200 | 4.70% | 0.20 |
| Z-score (Level) | -0.200 | 4.12% | 0.20 |
| Δ4Q (YoY Change) | 0.600 | 17.45% | 0.60 |
| Stress Move (Δ Z-score) | 0.300 | 21.02% | 0.30 |
| Regime Shift Signal | -0.900 | -20.29% | 0.90 |

---

## Best Transform: Regime Shift Signal

**用于 Trigger 信号**

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.729 | > 0.65 | **PASS** |
| AUC (20%) | 0.882 | > 0.65 | **PASS** |
| IC (Full) | -0.408 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | -20.29% | > 10% | **PASS** |
| Monotonicity | 0.90 | >= 0.7 | **PASS** |

---

## 关键发现

1. **ICR Δ4Q (变化) 优于 Level (水平)**
   - 变化率捕捉"企业盈利正在恶化"的信号
   - 水平值只能说明当前状态，无法预测趋势

2. **高利率环境下信号更强**
   - 高利率期间企业利息负担更重
   - ICR下降的危险性在高利率环境下更显著

3. **作为 Trigger (触发信号)**
   - ICR大幅下降 = 企业信用压力 = 可能引发信贷危机
   - 历史案例: GFC (2008) 前ICR大幅下降

---

## Signal Logic

```python
def get_v4_signal(delta_zscore):
    '''
    V4 ICR Signal - 企业盈利覆盖变化

    ICR下降 = 企业盈利恶化 = 危险信号
    正向指标的负变化 = 风险上升
    '''
    if delta_zscore < -1.5:
        return "RED"       # ICR大幅下降，企业严重承压
    elif delta_zscore < -1.0:
        return "ORANGE"    # ICR明显下降，需警惕
    elif delta_zscore < 0:
        return "YELLOW"    # ICR下降中
    else:
        return "GREEN"     # ICR上升或稳定
```

### Signal Matrix

| Δ4Q Z-score | Signal | 含义 |
|-------------|--------|------|
| Z < -1.5 | **RED** | ICR大幅下降，企业严重承压 |
| -1.5 ≤ Z < -1.0 | ORANGE | ICR明显下降，需警惕 |
| -1.0 ≤ Z < 0 | YELLOW | ICR下降中，关注趋势 |
| Z ≥ 0 | GREEN | ICR稳定或上升 |

---

## 危机检测回顾

| 危机 | ICR Δ4Q Z-score | Signal | 检测 |
|------|-----------------|--------|------|
| Dot-com (2000) | -1.12 | ORANGE | ✓ (但较弱) |
| GFC (2008) | **-2.09** | **RED** | **✓** |
| COVID (2020) | +0.07 | GREEN | ✗ (政策支持) |
| 2022 Rate Hike | +0.93 | GREEN | ✗ (企业盈利好) |

**关键洞察**: V4 主要捕获**企业信用恶化**类型的危机 (如GFC)，对政策冲击 (COVID) 和利率冲击 (2022) 预警能力有限。

---

## Combination with Other Factors

```python
# ==========================================
# V4 RED: 企业信用危机 (立即行动)
# ==========================================

# V4 + V9 组合: 信贷危机
if v4_signal == "RED" and v9_signal == "CREDIT_TIGHTENING_SHOCK":
    # 企业盈利恶化 + 银行收紧贷款 = 信贷危机
    credit_crisis_risk = "CRITICAL"
    action = "立即降低风险敞口"

# V4 + V8 组合: 杠杆危机
if v4_signal == "RED" and v8_combined == "CRITICAL":
    # 企业盈利恶化 + 高杠杆急升 = 2008式危机
    leverage_crisis_risk = "CRITICAL"
    action = "立即清仓或重度对冲"

# ==========================================
# V4 ORANGE/YELLOW: 关注企业压力
# ==========================================

# V4 下降 + 高估值
if v4_signal in ["ORANGE", "YELLOW"] and v7_fuel == "EXTREME_HIGH":
    # 企业盈利下降 + 高估值 = 回调风险
    warning = "企业盈利支撑减弱，估值面临压力"
    action = "降低风险敞口，等待确认"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| A464RC1Q027SBEA | Profit Before Tax (Nonfinancial Corp) | BEA NIPA |
| B471RC1Q027SBEA | Net Interest (Nonfinancial Corp) | BEA NIPA |

---

*Version: 2.0*
*Validated: {datetime.now().strftime('%Y-%m-%d')}*
*Framework: V1 Complete Validation*
*定位: Trigger (企业信用压力)*
