# 指标验证流程 (Validation Pipeline)

## 4-Step Validation Framework

### Step 1: Visual Sniff Test

目的：直观检查指标与市场的关系

```python
# 叠加指标 vs SPX，标注 NBER recession bands
plot_indicator_vs_market(
    indicator_series,
    spx_series,
    recession_bands=NBER_RECESSIONS
)
```

输出：`01_all_methods.png`

### Step 2: Lead/Lag Analysis

目的：确定指标的领先/滞后特性

```python
# 计算与 SPX 收益率的交叉相关
cross_corr = calculate_lead_lag(
    indicator_series,
    spx_returns,
    max_lag=24  # months
)
# 负 lag = 指标领先
```

理想结果：指标领先市场 6-12 个月

### Step 3: Redundancy Check

目的：检查与现有指标的相关性

```python
# 计算指标间相关矩阵
correlation_matrix = pd.DataFrame({
    'V1': debt_gdp,
    'V2': interest_coverage,
    'NEW': new_indicator
}).corr()
```

阈值：相关系数 < 0.7 才保留

### Step 4: False Positive Test

目的：评估预测准确性

| 错误类型 | 定义 | 可接受阈值 |
|----------|------|-----------|
| Type I (假阳性) | 警报但无危机 | < 50% |
| Type II (假阴性) | 危机但无警报 | < 33% |

```python
# 计算错误率
type_i_error = false_alarms / total_alarms
type_ii_error = missed_crises / total_crises
```

## 判定标准

| 结果 | Type I | Type II | 决策 |
|------|--------|---------|------|
| PASS | > 50% | Any | 拒绝 |
| Conditional | 33-50% | < 33% | 条件保留 |
| Keep | < 33% | < 33% | 保留 |
| BEST | < 25% | < 33% | 最佳 |

## 输出目录结构

```
V#_Indicator_Name/
├── 01_all_methods.png      # 可视化
├── all_methods_data.csv    # 计算数据
└── SUMMARY.md              # 结论报告
```
