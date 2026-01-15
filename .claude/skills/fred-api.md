# FRED/ALFRED API 使用规范

## 数据源选择

| 场景 | 使用 | 原因 |
|------|------|------|
| 实时分析 | FRED API | 获取最新数据 |
| 回测验证 | ALFRED API | 避免 look-ahead bias |

## ALFRED Point-in-Time 数据

```python
from lib.alfred_data import ALFREDDataLoader, build_pit_factor_series

# 加载历史所有 vintage
loader = ALFREDDataLoader(api_key=FRED_API_KEY)
all_vintages = loader.get_all_vintages(series_id='GFDEBTN')

# 构建月末 as-of 序列
pit_series = build_pit_factor_series(
    all_vintages,
    transform='yoy'  # 同 vintage 内计算 YoY
)
```

## 常用 FRED 序列 ID

| 指标 | Series ID | 频率 |
|------|-----------|------|
| 联邦债务/GDP | GFDEGDQ188S | Quarterly |
| 企业利息覆盖率 | BOGZ1FA106110005Q | Quarterly |
| 家庭债务/GDP | HDTGPDUSQ163N | Quarterly |
| Shiller PE | CAPE (自定义) | Monthly |
| 10Y Treasury | DGS10 | Daily |
| 2Y Treasury | DGS2 | Daily |

## 数据处理流程

1. **获取原始数据** - FRED/ALFRED API
2. **频率对齐** - 统一到月频 (month-end)
3. **缺失值处理** - forward fill (不超过 3 个月)
4. **异常值处理** - Winsorize at 1st/99th percentiles
5. **标准化** - MAD-based Z-score
6. **百分位转换** - Rolling window percentile
