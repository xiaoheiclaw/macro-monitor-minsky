# 因子 IC 测试方法论模板

## 概述

本文档总结 V1 Debt-GDP Gap 因子深度验证过程中建立的标准化 IC 测试框架。适用于所有宏观因子的验证。

---

## 6 项核心修正

| # | 修正项 | 说明 | 为什么重要 |
|---|--------|------|------------|
| 1 | **时间对齐规范** | Factor F_t → Return t+1 to t+13 | 避免 look-ahead bias |
| 2 | **对 β 做断点检测** | 而非 IC 序列 | β 更有经济解释性，适合 Chow Test |
| 3 | **HAC 标准误** | Newey-West (lag=11 for 12M) | 处理 overlapping returns 自相关 |
| 4 | **交互项回归** | R = α + β·F + γ·C + δ·(F×C) | 检验条件依赖性，不只分组 IC |
| 5 | **Series Metadata Audit** | 确认 FRED series 定义 | 避免数据定义错误 |
| 6 | **尾部分位回归** | 5% quantile β | 检验因子对左尾的预测力 |

---

## 测试步骤

### Step 0: Series Metadata Audit (P0)

```python
from fredapi import Fred
fred = Fred(api_key=API_KEY)

for series_id in ['YOUR_SERIES']:
    info = fred.get_series_info(series_id)
    print(f"Title: {info['title']}")
    print(f"Units: {info['units']}")
    print(f"Frequency: {info['frequency']}")
```

**输出**: 确认 series 经济定义与预期一致

---

### Step 1: 结构断点分析 (P0)

**目标**: 确认因子效应是否稳定

**方法**:
1. **Rolling β** (10Y window): 观察时间演化
2. **Chow Test**: 候选断点 2010, 2015, 2018
3. **Subsample β**: 分时期估计

```python
from lib.structural_break import analyze_structural_break

results = analyze_structural_break(
    factor, returns,
    candidate_breakpoints=['2010-01-01', '2015-01-01', '2018-01-01'],
    rolling_window=120
)
```

**判定标准**:
- Chow Test p < 0.05 → 存在显著断点
- β 符号变化 → 因子效应反转

---

### Step 2: Regime 交互项检验 (P1)

**目标**: 检验因子是否 regime-dependent

**模型**:
```
R_{t→12M} = α + β·F_t + γ·Condition_t + δ·(F_t × Condition_t) + ε_t
```

**常见 Condition 变量**:
- 利率 (FEDFUNDS)
- 当期回撤 (Drawdown > 5%)
- 波动率 regime

```python
from lib.regime_analysis import run_interaction_regression

result = run_interaction_regression(
    y=forward_return,
    factor=factor,
    condition=fed_funds_rate,
    use_hac=True,
    hac_lag=11
)

# 关键: 看交互项 δ 是否显著
print(f"δ = {result['coefficients']['interaction']}")
print(f"p-value = {result['p_values']['interaction']}")
```

**判定标准**:
- δ 显著 (p < 0.05) → 因子是条件依赖的
- 需分 regime 使用或做 conditional model

---

### Step 3: 风险目标变量检验 (P0)

**目标**: 检验因子是 return factor 还是 risk factor

**目标变量**:
1. Forward Return (12M)
2. Forward Max Drawdown (12M)
3. Forward Realized Volatility (6M/12M)
4. Drawdown Event (binary: MDD < -10%/-15%/-20%)

```python
from lib.regime_analysis import (
    compute_risk_target_ic,
    compute_drawdown_event_auc
)

# IC vs 风险指标
risk_ic = compute_risk_target_ic(factor, spx, horizons=[126, 252])

# AUC for crash event
auc = compute_drawdown_event_auc(factor, spx, threshold=-0.15)
```

**判定标准**:
- AUC > 0.60 → 有效的崩盘预测因子
- IC(MDD) > IC(Return) → 更适合做风险因子

---

### Step 4: 尾部分位检验 (P1)

**目标**: 检验因子对极端下跌的预测力

```python
from lib.hac_inference import compute_tail_quantile_ic

result = compute_tail_quantile_ic(
    factor, price_monthly,
    horizon=12,
    quantile=0.05
)

print(f"Mean β: {result['interpretation']['mean_beta']}")
print(f"5% Quantile β: {result['interpretation']['quantile_beta']}")
```

**判定标准**:
- |Quantile β| > |Mean β| → 尾部效应更强
- 适合做 crash risk indicator

---

### Step 5: Quintile 分析 (P2)

**目标**: 检验非线性/阈值效应

```python
from lib.regime_analysis import run_quintile_analysis

result = run_quintile_analysis(
    factor, forward_return,
    drawdown_events=crash_event,
    n_quantiles=5
)

# 检验单调性
print(f"Spearman: {result['monotonicity']['spearman_corr']}")
print(f"Q5-Q1 Spread: {result['monotonicity']['q5_minus_q1']}")
```

**判定标准**:
- Spearman ≈ -1.0 → 完美单调
- Q5-Q1 spread 显著 → 经济意义明确

---

### Step 6: Bootstrap 稳健性检验 (P2)

**目标**: 验证结果不是小样本偏差

```python
from lib.hac_inference import block_bootstrap_regression

result = block_bootstrap_regression(
    y=forward_return,
    X=pd.DataFrame({'factor': factor}),
    n_bootstrap=500,
    block_size=12
)

print(f"95% CI: [{result['ci_lower']['factor']}, {result['ci_upper']['factor']}]")
print(f"Bootstrap p-value: {result['bootstrap_p_value']['factor']}")
```

**判定标准**:
- CI 不包含 0 → 显著
- Bootstrap p < 0.05 → 稳健

---

## 最终判定框架

### 成功标准

| 条件 | 阈值 | 说明 |
|------|------|------|
| AUC (Crash Event) | > 0.60 | 有效的崩盘预测 |
| HAC p-value | < 0.05 | 统计显著 |
| Bootstrap p-value | < 0.05 | 稳健显著 |
| 交互项显著 | p < 0.05 | 如适用 |

### 结论类型

**类型 1**: Return Alpha Factor
- 全样本 IC 显著且稳定
- 无显著断点
- 可直接用于择时

**类型 2**: Risk Factor
- IC 对 return 弱，对 MDD/Vol 强
- AUC > 0.60
- 用于风险管理/仓位调节

**类型 3**: Conditional Factor
- 存在显著交互项
- 需分 regime 使用
- 建 conditional model

**类型 4**: Unstable/Unusable
- 断点显著且无法解释
- 交互项不显著
- 弃用

---

## 代码模板

```python
#!/usr/bin/env python3
"""
Factor Validation Template
"""

import os
import sys
import pandas as pd
import numpy as np
from fredapi import Fred

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from lib.structural_break import analyze_structural_break
from lib.regime_analysis import (
    run_interaction_regression,
    compute_risk_target_ic,
    compute_drawdown_event_auc,
    run_quintile_analysis,
)
from lib.hac_inference import (
    compute_tail_quantile_ic,
    block_bootstrap_regression,
)

# Configuration
FRED_API_KEY = 'YOUR_KEY'
HAC_LAG = 11  # for 12M overlapping returns

def main():
    # 1. Load data
    factor = load_factor()  # Your factor
    spx = load_spx()
    ffr = load_fed_funds_rate()

    # 2. Compute forward return (tradable)
    spx_monthly = spx.resample('ME').last()
    fwd_return = np.log(spx_monthly.shift(-13) / spx_monthly.shift(-1))

    # 3. Step 0: Metadata audit
    # ...

    # 4. Step 1: Structural break
    sb_results = analyze_structural_break(factor, fwd_return)

    # 5. Step 2: Interaction regression
    interaction = run_interaction_regression(fwd_return, factor, ffr, use_hac=True)

    # 6. Step 3: Risk target
    auc = compute_drawdown_event_auc(factor, spx, threshold=-0.15)

    # 7. Step 4: Tail quantile
    tail = compute_tail_quantile_ic(factor, spx_monthly)

    # 8. Step 5: Quintile
    quintile = run_quintile_analysis(factor, fwd_return)

    # 9. Generate report
    # ...

if __name__ == '__main__':
    main()
```

---

## 输出文件清单

| 文件 | 说明 |
|------|------|
| `04_structural_break.png` | 断点分析图 |
| `05_rate_regime_ic.png` | Regime 交互分析 |
| `08_risk_target_ic.png` | 风险目标变量 |
| `09_quintile_analysis.png` | Quintile 分析 |
| `VALIDATION_RESULTS.md` | 详细验证结果 |

---

*基于 V1 Debt-GDP Gap 因子深度验证建立*
