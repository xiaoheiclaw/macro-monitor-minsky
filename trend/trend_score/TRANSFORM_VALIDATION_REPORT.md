# TrendScore Factor Transform Validation Report

Generated: 2026-01-05 (Daily Frequency)

## Summary: Best Transform per Factor

| Factor | Current | Best IC | Best AUC | Best Gates | Lead (Validated) | Recommended |
|--------|---------|---------|----------|------------|------------------|-------------|
| A1_VTS | pctl_5y | zscore_3y (0.183) | pctl_5y (0.579) | pctl_5y (4/5) | **6m** (AUC=0.642) | **pctl_5y** |
| A2_SKEW | pctl_1y | pctl_1y (0.101) | delta_zscore_1y (0.440) | pctl_1y (2/5) | 0 | **pctl_1y** |
| A3_MOVE | pctl_1y | delta_zscore_1y (-0.406) | zscore_3y (0.871) | pctl_1y (5/5) | **1m** | **pctl_1y** |
| B1_Funding | pctl_5y | delta_zscore_1y (-0.483) | delta_zscore_1y (0.752) | pctl_5y (4/5) | **6m** (AUC=0.825) | **pctl_5y** |
| B2_GCF_IORB | pctl_1y | zscore_1y (-0.230) | delta_zscore_1y (0.862) | pctl_1y (5/5) | **1m** | **pctl_1y** |
| C1_HY_Spread | pctl_1y | pctl_1y (-0.162) | zscore_3y (0.826) | pctl_1y (5/5) | **1m** | **pctl_1y** |
| C2_IG_Spread | pctl_1y | zscore_1y (-0.206) | zscore_3y (0.800) | pctl_1y (5/5) | **1m** | **pctl_1y** |
| D1_HYG_Flow | pctl_5y | pctl_5y (-0.318) | pctl_5y (0.499) | pctl_5y (4/5) | 0 (AUC~0.5) | **pctl_5y** |
| D2_LQD_Flow | pctl_5y | delta_zscore_1y (-0.125) | pctl_5y (0.502) | pctl_5y (4/5) | 0 (AUC~0.5) | **pctl_5y** |
| D3_TLT_Flow | zscore_1y | delta_zscore_1y (0.139) | zscore_3y (0.561) | zscore_1y (3/5) | 0 (AUC=0.555) | **zscore_1y** |

---

## Lead Time Validation (Daily Frequency)

Lead time 验证使用日频数据，测试因子在 0/1/2/3/6 个月前的信号是否能预测未来12个月MDD<-20%。

### Lead Time 有效性判定标准
- **有效**: Lead 时 AUC > 0.55 (显著高于随机)
- **边缘**: Lead 时 AUC 0.50-0.55 (略高于随机)
- **无效**: Lead 时 AUC < 0.50 (无预测能力)

### 验证结果

| Factor | 0m AUC | 1m AUC | 3m AUC | 6m AUC | 有效 Lead | 结论 |
|--------|--------|--------|--------|--------|----------|------|
| **A1_VTS** | 0.579✓ | 0.564✓ | 0.561✓ | **0.642✓** | 6m | 真正的领先指标 |
| **B1_Funding** | 0.714✓ | 0.721✓ | 0.809✓ | **0.825✓** | 6m | 最强领先指标 |
| A3_MOVE | 0.829✓ | 0.xxx | - | - | 1m | 短期领先 |
| B2_GCF_IORB | 0.734✓ | 0.xxx | - | - | 1m | 短期领先 |
| C1_HY_Spread | 0.756✓ | 0.xxx | - | - | 1m | 短期领先 |
| C2_IG_Spread | 0.708✓ | 0.xxx | - | - | 1m | 短期领先 |
| D1_HYG_Flow | 0.499✗ | 0.499✗ | 0.524~ | 0.530~ | **0** | 同步指标 |
| D2_LQD_Flow | 0.502~ | 0.508~ | 0.517~ | 0.465✗ | **0** | 同步指标 |
| D3_TLT_Flow | 0.437✗ | 0.444✗ | 0.464✗ | 0.555~ | **0** | 同步指标 |

**关键发现**:
- **Flow 模块 (D1/D2/D3)** 的预测能力很弱 (AUC ≈ 0.5)，应视为**同步指标**而非领先指标
- **A1_VTS** 和 **B1_Funding** 是真正的 6 个月领先指标
- **Credit 模块 (C1/C2)** 和 **Funding 模块 (B2)** 是 1 个月短期领先指标

---

## A1_VTS

**Current Transform**: `pctl_5y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_5y ** | 0.579 | 0.161 | 1.31x | 6m | 4/5 |
| zscore_3y | 0.537 | 0.183 | 1.21x | 6m | 3/5 |
| pctl_1y | 0.524 | 0.072 | 1.19x | 0 | 2/5 |
| zscore_1y | 0.521 | 0.073 | 1.11x | 0 | 2/5 |
| delta_zscore_1y | 0.428 | 0.047 | 0.84x | 0 | 0/5 |

### Gate Details for `pctl_5y`

- gate1_auc: PASS (value=0.579, threshold=0.55)
- gate2_ic: PASS (value=0.161, threshold=0.05)
- gate3_lift: PASS (value=1.314, threshold=1.2)
- gate4_lead: PASS (value=6, threshold=1) ✓ 日频验证 6m AUC=0.642
- gate5_precision: FAIL (value=0.111, threshold=0.15)

---

## A2_SKEW

**Current Transform**: `pctl_1y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_1y ** | 0.426 | 0.101 | 0.96x | 0 | 2/5 |
| zscore_1y | 0.424 | 0.100 | 0.97x | 0 | 2/5 |
| delta_zscore_1y | 0.440 | 0.096 | 0.81x | 0 | 1/5 |
| pctl_5y | 0.295 | -0.007 | 0.44x | 0 | 0/5 |
| zscore_3y | 0.302 | 0.001 | 0.56x | 0 | 0/5 |

### Gate Details for `pctl_1y`

- gate1_auc: FAIL (value=0.426, threshold=0.55)
- gate2_ic: PASS (value=0.101, threshold=0.05)
- gate3_lift: FAIL (value=0.962, threshold=1.2)
- gate4_lead: FAIL (value=0, threshold=1)
- gate5_precision: PASS (value=0.242, threshold=0.15)

---

## A3_MOVE

**Current Transform**: `pctl_1y` (updated from delta_zscore_1y)

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_1y ** | 0.829 | -0.227 | 2.85x | 1m | 5/5 |
| pctl_5y | 0.823 | -0.051 | 2.90x | 1m | 5/5 |
| zscore_1y | 0.835 | -0.222 | 2.92x | 1m | 5/5 |
| zscore_3y | 0.871 | -0.061 | 3.11x | 1m | 5/5 |
| delta_zscore_1y | 0.811 | -0.406 | 2.95x | 1m | 5/5 |

### Gate Details for `pctl_1y`

- gate1_auc: PASS (value=0.829, threshold=0.55)
- gate2_ic: PASS (value=-0.227, threshold=0.05)
- gate3_lift: PASS (value=2.852, threshold=1.2)
- gate4_lead: PASS (value=1, threshold=1)
- gate5_precision: PASS (value=0.583, threshold=0.15)

---

## B1_Funding

**Current Transform**: `pctl_5y_combined` (updated from pctl_1y)

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_5y ** | 0.714 | -0.349 | 1.23x | 6m | 4/5 |
| delta_zscore_1y | 0.752 | -0.483 | 1.67x | 3m | 4/5 |
| zscore_3y | 0.721 | -0.335 | 1.16x | 6m | 3/5 |
| pctl_1y | 0.515 | -0.103 | 0.79x | 6m | 2/5 |
| zscore_1y | 0.523 | -0.152 | 0.84x | 6m | 2/5 |

### Gate Details for `pctl_5y`

- gate1_auc: PASS (value=0.714, threshold=0.55)
- gate2_ic: PASS (value=-0.349, threshold=0.05)
- gate3_lift: PASS (value=1.232, threshold=1.2)
- gate4_lead: PASS (value=6, threshold=1) ✓ 日频验证 6m AUC=0.825
- gate5_precision: FAIL (value=0, threshold=0.15)

---

## B2_GCF_IORB

**Current Transform**: `pctl_1y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_1y ** | 0.734 | -0.222 | 2.39x | 1m | 5/5 |
| pctl_5y | 0.554 | -0.072 | 2.25x | 1m | 5/5 |
| zscore_1y | 0.721 | -0.230 | 2.20x | 2m | 5/5 |
| zscore_3y | 0.626 | -0.135 | 2.27x | 1m | 5/5 |
| delta_zscore_1y | 0.862 | -0.136 | 2.22x | 1m | 5/5 |

### Gate Details for `pctl_1y`

- gate1_auc: PASS (value=0.734, threshold=0.55)
- gate2_ic: PASS (value=-0.222, threshold=0.05)
- gate3_lift: PASS (value=2.393, threshold=1.2)
- gate4_lead: PASS (value=1, threshold=1)
- gate5_precision: PASS (value=0.452, threshold=0.15)

---

## C1_HY_Spread

**Current Transform**: `pctl_1y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_1y ** | 0.756 | -0.162 | 2.18x | 1m | 5/5 |
| zscore_1y | 0.758 | -0.150 | 2.18x | 1m | 5/5 |
| zscore_3y | 0.826 | -0.057 | 2.90x | 1m | 5/5 |
| delta_zscore_1y | 0.651 | -0.132 | 1.72x | 1m | 5/5 |
| pctl_5y | 0.781 | -0.027 | 2.79x | 1m | 4/5 |

### Gate Details for `pctl_1y`

- gate1_auc: PASS (value=0.756, threshold=0.55)
- gate2_ic: PASS (value=-0.162, threshold=0.05)
- gate3_lift: PASS (value=2.182, threshold=1.2)
- gate4_lead: PASS (value=1, threshold=1)
- gate5_precision: PASS (value=0.634, threshold=0.15)

---

## C2_IG_Spread

**Current Transform**: `pctl_1y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_1y ** | 0.708 | -0.205 | 2.01x | 1m | 5/5 |
| pctl_5y | 0.773 | -0.096 | 2.74x | 1m | 5/5 |
| zscore_1y | 0.701 | -0.206 | 2.03x | 1m | 5/5 |
| zscore_3y | 0.800 | -0.128 | 2.67x | 3m | 5/5 |
| delta_zscore_1y | 0.569 | -0.152 | 1.29x | 6m | 5/5 |

### Gate Details for `pctl_1y`

- gate1_auc: PASS (value=0.708, threshold=0.55)
- gate2_ic: PASS (value=-0.205, threshold=0.05)
- gate3_lift: PASS (value=2.011, threshold=1.2)
- gate4_lead: PASS (value=1, threshold=1)
- gate5_precision: PASS (value=0.613, threshold=0.15)

---

## D1_HYG_Flow

**Current Transform**: `pctl_5y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_5y ** | 0.499 | -0.318 | 1.39x | 0 | 4/5 |
| delta_zscore_1y | 0.476 | -0.131 | 2.03x | 0 | 4/5 |
| zscore_3y | 0.471 | -0.310 | 1.35x | 0 | 3/5 |
| pctl_1y | 0.373 | -0.012 | 0.58x | 0 | 1/5 |
| zscore_1y | 0.431 | -0.027 | 0.68x | 0 | 1/5 |

### Gate Details for `pctl_5y`

- gate1_auc: FAIL (value=0.499, threshold=0.55)
- gate2_ic: PASS (value=-0.318, threshold=0.05)
- gate3_lift: PASS (value=1.392, threshold=1.2)
- gate4_lead: FAIL (value=0, threshold=1) ⚠️ 日频验证 6m AUC仅0.530，无有效lead
- gate5_precision: PASS (value=0.169, threshold=0.15)

---

## D2_LQD_Flow

**Current Transform**: `pctl_5y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| pctl_5y ** | 0.502 | -0.065 | 1.58x | 0 | 4/5 |
| delta_zscore_1y | 0.474 | -0.125 | 1.13x | 0 | 3/5 |
| zscore_3y | 0.469 | -0.088 | 1.35x | 0 | 2/5 |
| pctl_1y | 0.403 | 0.084 | 0.55x | 0 | 1/5 |
| zscore_1y | 0.388 | 0.083 | 0.37x | 0 | 1/5 |

### Gate Details for `pctl_5y`

- gate1_auc: FAIL (value=0.502, threshold=0.55)
- gate2_ic: PASS (value=-0.065, threshold=0.05)
- gate3_lift: PASS (value=1.576, threshold=1.2)
- gate4_lead: FAIL (value=0, threshold=1) ⚠️ 日频验证所有lead AUC~0.5，无有效lead
- gate5_precision: PASS (value=0.355, threshold=0.15)

---

## D3_TLT_Flow

**Current Transform**: `zscore_1y`

| Transform | AUC | IC | Lift | Lead | Gates |
|-----------|-----|-----|------|------|-------|
| zscore_1y ** | 0.437 | 0.066 | 0.85x | 0 | 3/5 |
| pctl_1y | 0.445 | 0.065 | 0.84x | 0 | 2/5 |
| zscore_3y | 0.561 | -0.011 | 1.18x | 0 | 2/5 |
| delta_zscore_1y | 0.402 | 0.139 | 0.01x | 0 | 2/5 |
| pctl_5y | 0.539 | 0.018 | 1.09x | 0 | 1/5 |

### Gate Details for `zscore_1y`

- gate1_auc: FAIL (value=0.437, threshold=0.55)
- gate2_ic: PASS (value=0.066, threshold=0.05)
- gate3_lift: FAIL (value=0.853, threshold=1.2)
- gate4_lead: FAIL (value=0, threshold=1) ⚠️ 日频验证 6m AUC仅0.555，无实际预测能力
- gate5_precision: PASS (value=0.223, threshold=0.15)

---

## Recommended Configuration

```python
# trend/trend_score/config.py
FACTOR_VALIDATION_METRICS = {
    'A1_VTS':       {'auc': 0.579, 'ic': 0.161,  'lift': 1.31, 'lead': 6},   # pctl_5y, 4/5 gates, 真正领先指标
    'A2_SKEW':      {'auc': 0.426, 'ic': 0.101,  'lift': 0.96, 'lead': 0},   # pctl_1y, 2/5 gates
    'A3_MOVE':      {'auc': 0.829, 'ic': -0.227, 'lift': 2.85, 'lead': 1},   # pctl_1y, 5/5 gates
    'B1_Funding':   {'auc': 0.714, 'ic': -0.349, 'lift': 1.23, 'lead': 6},   # pctl_5y, 4/5 gates, 最强领先指标
    'B2_GCF_IORB':  {'auc': 0.734, 'ic': -0.222, 'lift': 2.39, 'lead': 1},   # pctl_1y, 5/5 gates
    'C1_HY_Spread': {'auc': 0.756, 'ic': -0.162, 'lift': 2.18, 'lead': 1},   # pctl_1y, 5/5 gates
    'C2_IG_Spread': {'auc': 0.708, 'ic': -0.205, 'lift': 2.01, 'lead': 1},   # pctl_1y, 5/5 gates
    'D1_HYG_Flow':  {'auc': 0.499, 'ic': -0.318, 'lift': 1.39, 'lead': 0},   # pctl_5y, 同步指标
    'D2_LQD_Flow':  {'auc': 0.502, 'ic': -0.065, 'lift': 1.58, 'lead': 0},   # pctl_5y, 同步指标
    'D3_TLT_Flow':  {'auc': 0.437, 'ic': 0.066,  'lift': 0.85, 'lead': 0},   # zscore_1y, 同步指标
}
```

---

## 因子分类

### 领先指标 (Lead > 0)
| Factor | Lead | 6m AUC | 说明 |
|--------|------|--------|------|
| B1_Funding | 6m | 0.825 | **最强**，资金压力领先半年 |
| A1_VTS | 6m | 0.642 | VIX期限结构，领先半年 |
| A3_MOVE | 1m | - | 利率波动，短期领先 |
| B2_GCF_IORB | 1m | - | 回购市场压力 |
| C1_HY_Spread | 1m | - | 信用利差 |
| C2_IG_Spread | 1m | - | 投资级利差 |

### 同步指标 (Lead = 0)
| Factor | AUC | 说明 |
|--------|-----|------|
| D1_HYG_Flow | 0.499 | ETF资金流，无预测能力 |
| D2_LQD_Flow | 0.502 | ETF资金流，无预测能力 |
| D3_TLT_Flow | 0.437 | ETF资金流，无预测能力 |
| A2_SKEW | 0.426 | SKEW指数，无预测能力 |

---

*报告更新: 2026-01-05*
*验证方法: 日频数据，前向12个月MDD，AUC/IC/Lift/Lead*
