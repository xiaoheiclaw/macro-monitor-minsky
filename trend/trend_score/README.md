# TrendScore v4.1 - 趋势风险评分系统

## 概述

TrendScore 是一个多因子聚合的趋势风险评分系统，用于监控金融市场的系统性风险水平。

**核心功能**：
- 将 10 个风险因子聚合为统一的趋势热度分数 (0~1)
- 输出四档风险状态：CALM / WATCH / ALERT / CRITICAL
- 支持历史回测和实时监控

**版本历史**：
| 版本 | 主要改进 |
|------|----------|
| v3.0 | 分位数校准、CRITICAL 门槛收紧 |
| v4.0 | 数据驱动权重 (基于 AUC/IC/Lead) |
| v4.1 | 数据质量分层 (NONE/WEAK/OK/STRONG) |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     TrendScore 三层聚合架构                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  因子层 (10个因子)                                            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │A1_VTS│ │A2_SKW│ │A3_MOV│ │B1_FND│ │B2_GCF│ ...          │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘              │
│     │        │        │        │        │                   │
│     ▼        ▼        ▼        ▼        ▼                   │
│  ┌─────────────────────────────────────────────┐            │
│  │ intensity = f(percentile, danger_zone)      │            │
│  │ → 三档 Zone: WATCH / ALERT / CRITICAL       │            │
│  └─────────────────────────────────────────────┘            │
│                         │                                    │
│                         ▼                                    │
│  模块层 (4个模块)                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Module A  │ │Module B  │ │Module C  │ │Module D  │       │
│  │Volatility│ │ Funding  │ │  Credit  │ │   Flow   │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       │            │            │            │              │
│       ▼            ▼            ▼            ▼              │
│  ┌─────────────────────────────────────────────┐            │
│  │ module_heat = 0.4×max + 0.6×weighted_avg    │            │
│  │ → reliability 加权聚合                        │            │
│  └─────────────────────────────────────────────┘            │
│                         │                                    │
│                         ▼                                    │
│  趋势层 (TrendScore)                                         │
│  ┌─────────────────────────────────────────────┐            │
│  │ trend_heat = (Σ W_m × module_heat_m)^1.3    │            │
│  │ → 非线性压缩，放大极端情况                     │            │
│  └─────────────────────────────────────────────┘            │
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────┐            │
│  │ 输出: trend_heat_score, trend_state         │            │
│  │       data_quality, trigger_flags           │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块与因子

### 四大模块

| 模块 | 名称 | 说明 | 因子数 |
|------|------|------|--------|
| **A** | Volatility | 波动率相关指标 | 3 |
| **B** | Funding | 资金面/流动性指标 | 2 |
| **C** | Credit | 信用利差指标 | 2 |
| **D** | Flow | 资金流向指标 | 3 |

### 10个因子详解

| 因子 | 名称 | 含义 | 危险方向 |
|------|------|------|----------|
| **A1_VTS** | VIX Term Structure | VIX期限结构倒挂程度。正值=短期恐慌>长期预期 | 高→危险 |
| **A2_SKEW** | CBOE SKEW Index | 尾部风险定价。低位=市场对下跌保护需求低(自满) | 低→危险 |
| **A3_MOVE** | MOVE Index | 债券波动率指数变化率。快速上升=利率不确定性飙升 | 高→危险 |
| **B1_Funding** | Funding Spread | 银行间资金成本-无风险利率。正值=流动性紧张 | 高→危险 |
| **B2_GCF_IORB** | GCF-IORB Spread | Repo市场压力指标。偏离=货币市场摩擦 | 区间→危险 |
| **C1_HY_Spread** | HY Credit Spread | 高收益债利差。上升=信用风险偏好恶化 | 高→危险 |
| **C2_IG_Spread** | IG Credit Spread | 投资级债利差。上升=连优质信用都被抛售 | 高→危险 |
| **D1_HYG_Flow** | HYG Flow | 高收益债ETF资金流(取负)。正值=资金流出 | **禁用** |
| **D2_LQD_Flow** | LQD Flow | 投资级债ETF资金流(取负)。正值=资金流出 | 高→危险 |
| **D3_TLT_Flow** | TLT Flow | 长期国债ETF资金流(取负)。正值=避险逆转 | 高→危险 |

> 注: D1_HYG_Flow 因验证未通过 (2/5 gates) 已禁用

---

## 数据质量分层 (v4.1)

### 质量级别定义

| coverage_modules | quality_level | 输出内容 | 用途 |
|------------------|---------------|----------|------|
| 0 | **NONE** | INSUFFICIENT_DATA | 无法判断 |
| 1 | **WEAK** | 局部信号 (local_signals) | 局部压力提示 |
| 2 | **OK** | TrendScore + TrendState | 可用于 risk budget |
| 3-4 | **STRONG** | TrendScore + TrendState | 可用于 escalation |

### 历史覆盖率

| 时期 | 可用模块 | quality_level | 说明 |
|------|----------|---------------|------|
| 1986-1990 | B only | WEAK | 仅 Funding 模块 |
| 1991-1997 | A+B | OK | 波动+资金面 |
| 1998-2003 | A+B+C | STRONG | 信用模块上线 |
| 2004+ | A+B+C+D | STRONG | 全模块完整版 |

### 推荐回测窗口

- **Primary**: 1998+ (A+B+C，信用模块上线)
- **Recommended**: 2004+ (全模块完整版)
- **Earliest**: 1991+ (A+B only)

---

## 核心算法

### 1. 强度映射 (intensity.py)

三种映射类型：

```python
# upper: 越高越危险 (适用于 VTS, MOVE, Funding, Spreads)
intensity = (pctl - lower) / (100 - lower)

# lower: 越低越危险 (适用于历史上的 Dealer)
intensity = (upper - pctl) / upper

# band: 区间内危险 (适用于 SKEW, GCF-IORB)
intensity = (pctl - low) / (high - low)  # 区间内
intensity = max(0, 1 - (pctl - high) / decay)  # 超出上界衰减
```

### 2. 三档 Zone

| Zone | 覆盖率目标 | 权重 | 含义 |
|------|-----------|------|------|
| WATCH | 20-30% | 0.4 | 背景监控 |
| ALERT | 10-15% | 0.7 | 风险预警 |
| CRITICAL | 3-7% | 1.0 | 强制行动 |

### 3. 模块聚合公式

```python
module_heat = α × max(intensity_i) + (1-α) × Σ(w_i × intensity_i)
# α = 0.4 (冲击权重)
# w_i = reliability 权重 (基于 AUC/IC)
```

### 4. 跨模块聚合公式

```python
raw_heat = Σ(W_m × module_heat_m) / Σ W_m
trend_heat = raw_heat ^ γ  # γ = 1.3 (非线性压缩)
```

### 5. CRITICAL 门槛 (v3.0)

CRITICAL 状态需要满足以下条件之一：
1. Credit 模块 (C) 达到 CRITICAL
2. 至少 2 个模块 >= ALERT 且 trend_heat > CRITICAL 阈值

---

## 配置说明

### FACTOR_CONFIG 结构

```python
FACTOR_CONFIG = {
    'A1_VTS': {
        'enabled': True,
        'transform': 'pctl_5y',           # 转换方法
        'direction': 'high_is_danger',    # 危险方向
        'zones': {
            'WATCH':    {'zone': (50, 80),  'weight': 0.4},
            'ALERT':    {'zone': (65, 85),  'weight': 0.7},
            'CRITICAL': {'zone': (80, 100), 'weight': 1.0},
        },
    },
    # ...
}
```

### RELIABILITY_CONFIG 参数

```python
RELIABILITY_CONFIG = {
    'auc_weight': 0.5,       # AUC 在 reliability 中的权重
    'ic_weight': 0.3,        # IC 在 reliability 中的权重
    'lead_weight': 0.2,      # Lead 在 reliability 中的权重
    'lead_max': 6,           # 最大提前月数
    'min_reliability': 0.1,  # 因子最低权重下限
    'max_module_weight': 0.55,  # 模块最高权重上限
}
```

### DATA_QUALITY_CONFIG 参数

```python
DATA_QUALITY_CONFIG = {
    'quality_levels': {0: 'NONE', 1: 'WEAK', 2: 'OK', 3: 'STRONG', 4: 'STRONG'},
    'level_confidence': {'NONE': 0.0, 'WEAK': 0.25, 'OK': 0.6, 'STRONG': 1.0},
    'min_modules_for_trend': 2,  # TrendScore 计算最少需要 2 个模块
}
```

---

## 使用示例

### 获取最新 TrendScore

```python
from trend.trend_score import TrendScore

ts = TrendScore()
result = ts.compute_latest()

print(f"TrendScore: {result['trend_heat_score']:.3f}")
print(f"State: {result['trend_state']}")
print(f"Quality: {result['data_quality']['quality_level']}")
```

### 计算历史序列

```python
history = ts.compute_history(freq='D')

# 查看状态分布
print(history['trend_state'].value_counts())

# 按数据质量筛选
trustworthy = history[history['is_trustworthy'] == True]
```

### 校准阈值

```python
# 基于历史数据校准分位数阈值
thresholds = ts.calibrate(history)
print(f"CRITICAL threshold: {thresholds['CRITICAL']:.3f}")
print(f"ALERT threshold: {thresholds['ALERT']:.3f}")
print(f"WATCH threshold: {thresholds['WATCH']:.3f}")
```

---

## API 参考

### TrendScore 类

| 方法 | 说明 |
|------|------|
| `__init__(config=None)` | 初始化，可传入自定义配置 |
| `compute_latest()` | 获取最新 TrendScore |
| `compute_for_date(date, data)` | 计算指定日期的 TrendScore |
| `compute_history(start_date, end_date, freq)` | 计算历史序列 |
| `calibrate(history)` | 基于历史数据校准阈值 |
| `get_thresholds()` | 获取当前阈值 |

### 输出结构

```python
{
    'date': Timestamp,
    'trend_heat_score': float,       # 0~1，趋势热度分数
    'trend_state': str,              # CALM/WATCH/ALERT/CRITICAL/INSUFFICIENT_DATA
    'data_quality': {
        'coverage_modules': int,     # 有效模块数 (0-4)
        'quality_level': str,        # NONE/WEAK/OK/STRONG
        'modules_available': list,   # 可用模块列表
        'modules_missing': list,     # 缺失模块列表
        'confidence': float,         # 置信度 (0-1)
        'is_trustworthy': bool,      # 是否可信 (coverage >= 2)
    },
    'local_signals': {               # 仅 WEAK 模式
        'active_module': str,
        'local_heat': float,
        'local_state': str,
    } or None,
    'module_states': {
        'A': {'heat_score': float, 'state': str, ...},
        'B': {...},
        'C': {...},
        'D': {...},
    },
    'trigger_flags': {
        'any_critical': bool,
        'multi_module_alert': bool,
        'dominant_module': str,
        'alert_modules': list,
        'valid_modules_count': int,
    },
    'calibrated': bool,
}
```

---

## 文件结构

```
trend/trend_score/
├── __init__.py           # 模块入口
├── config.py             # v4.1 配置 (含验证数据)
├── intensity.py          # 强度映射函数
├── trend_score.py        # TrendScore 主类
├── test_trend_score.py   # 单元测试
├── plot_trend_history.py # 历史可视化脚本
├── plot_best_transforms.py # 因子可视化脚本
├── README.md             # 本文档
└── *.png                 # 生成的图表
```

---

## 图表说明

| 图表 | 说明 |
|------|------|
| `trend_history_v3.png` | TrendScore 完整历史与 SPX 对照 |
| `trend_crisis_zoom.png` | 危机期间放大视图 (GFC, COVID, 2022) |
| `best_transforms_vs_spx.png` | 各因子 best transform 与 SPX 对照 |
| `best_transforms_normalized.png` | 所有因子归一化后的叠加图 |

---

## 状态分布目标

| 状态 | 目标占比 | v4.1 实际 |
|------|----------|-----------|
| CALM | 45-60% | 58.9% ✅ |
| WATCH | 20-30% | 19.6% ✅ |
| ALERT | 10-15% | 16.6% ✅ |
| CRITICAL | 3-7% | 4.9% ✅ |

---

*Generated: 2026-01-03 | TrendScore v4.1*
