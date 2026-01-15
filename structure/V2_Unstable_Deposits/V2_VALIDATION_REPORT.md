# V2 Uninsured Deposits Ratio - Validation Report

Generated: 2025-12-30 22:54:48

## Factor Definition

**Series**: Uninsured Deposits / Time & Savings Deposits (Z.1)
- BOGZ1FL763139105Q: Total Uninsured Checkable and Time and Savings Deposits
- BOGZ1FL763130005Q: Total Time and Savings Deposits

| 属性 | 值 |
|------|-----|
| Units | Percent (%) |
| Frequency | Quarterly → Monthly (forward-filled) |
| Data Start | 2001Q4 |
| Release Lag | 6 months (Z.1 quarterly) |

**机制**: 高未保险存款比例 = 银行挤兑风险 (SVB 2023)

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **V2 Ratio** | **41.94%** | - |
| **10Y Percentile** | **67.5%** | **ELEVATED** |
| **Z-score (Level)** | **-0.14** | - |
| **Δ12M Z-score** | **1.06** | - |

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward Return

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Percentile (5Y) | -0.067 | 0.4615 | 0.084 | -0.154 |
| Percentile (10Y) | -0.237 | 0.0253 | -0.054 | -0.263 |
| Z-score (Level) | -0.144 | 0.0945 | 0.107 | -0.283 |
| Δ12M Z-score (YoY Change) | 0.004 | 0.9674 | -0.144 | 0.083 |
| Δ24M Z-score (2Y Change) | -0.043 | 0.6360 | 0.129 | -0.147 |
| YoY % Change | -0.107 | 0.1897 | -0.163 | -0.121 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Percentile (5Y) | 0.460 | 0.352 | 0.579 |
| Percentile (10Y) | 0.544 | 0.444 | 0.610 |
| Z-score (Level) | 0.478 | 0.331 | 0.482 |
| Δ12M Z-score (YoY Change) | 0.338 | 0.358 | 0.527 |
| Δ24M Z-score (2Y Change) | 0.372 | 0.295 | 0.489 |
| YoY % Change | 0.303 | 0.337 | 0.522 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Percentile (5Y) | 0.300 | 0.25% | 0.30 |
| Percentile (10Y) | -0.400 | -3.21% | 0.40 |
| Z-score (Level) | -0.400 | -4.84% | 0.40 |
| Δ12M Z-score (YoY Change) | 0.300 | 2.23% | 0.30 |
| Δ24M Z-score (2Y Change) | 0.100 | 8.18% | 0.10 |
| YoY % Change | -0.100 | -2.69% | 0.10 |

---

## Best Transform: Percentile (10Y)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.444 | > 0.65 | FAIL |
| AUC (20%) | 0.610 | > 0.65 | FAIL |
| IC (Full) | -0.237 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | -3.21% | > 10% | FAIL |
| Monotonicity | 0.40 | > 0.7 | FAIL |

---

## Signal Logic

```python
def get_v2_signal(pctl_10y):
    '''
    V2 Uninsured Deposits 银行挤兑风险信号

    高未保险存款比例 = 银行挤兑风险 (SVB 2023)
    方向: 高值 = 高风险
    '''
    if pctl_10y > 80:
        return "HIGH_RISK"      # 未保险存款高，挤兑风险大
    elif pctl_10y > 60:
        return "ELEVATED"       # 偏高，需关注
    elif pctl_10y > 40:
        return "NORMAL"         # 正常范围
    else:
        return "LOW_RISK"       # 未保险存款低，风险小
```

### Signal Interpretation

| V2 10Y Pctl | Signal | Risk Type | Interpretation |
|-------------|--------|-----------|----------------|
| Pctl > 80% | **HIGH_RISK** | 高风险 | 未保险存款历史高位，挤兑风险大 |
| 60-80% | ELEVATED | 观察 | 偏高，需监控 |
| 40-60% | NORMAL | 正常 | 正常范围 |
| < 40% | LOW_RISK | 安全 | 未保险存款低，风险小 |

### 核心机制

**高未保险存款比例 = 银行挤兑风险**

SVB 2023危机验证:
1. SVB未保险存款比例高达93%
2. 存款人知道自己的钱没有FDIC保护
3. 一旦恐慌，未保险存款最先逃离
4. 银行被迫亏本出售资产

---

## Combination with Other Factors

```python
# V2 + V5 组合: 系统性脆弱
if v2_signal == "HIGH_RISK" and v5_signal == "HIGH_DEBT":
    # 银行未保险存款高 + 家庭高负债 = 系统性脆弱
    system_fragility = "CRITICAL"
    action = "关注金融板块风险"

# V2 + 利率上升
if v2_signal == "HIGH_RISK" and fed_hiking:
    # 未保险存款高 + 加息 = SVB类风险
    bank_run_risk = "HIGH"
    action = "避开高未保险存款的区域性银行"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| BOGZ1FL763139105Q | Total Uninsured Checkable and Time and Savings Deposits | FRED/Z.1 Financial Accounts |
| BOGZ1FL763130005Q | Total Time and Savings Deposits | FRED/Z.1 Financial Accounts |

---

*Version: 3.0 (Redefined with Z.1 Data)*
*Validated: 2025-12-30*
*Framework: V1 Complete Validation*
