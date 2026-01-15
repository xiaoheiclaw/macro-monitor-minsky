# Indicator System PRD
## 宏观经济指标验证框架 - 产品需求文档

**版本**: 1.0
**日期**: 2026-01-15
**状态**: Active

---

## 1. 产品概述

### 1.1 产品定位

**indicator_test** 是一个三层宏观经济风险监控系统，旨在为权益市场提供早期危机预警信号。系统基于 Minsky 金融不稳定假说，通过结合结构脆弱性指标、变化率信号和实时市场压力指标，实现动态投资组合风险管理。

### 1.2 核心理念

> 危机源于系统内部动态（债务积累 → 过度杠杆 → 强制抛售），而非外部冲击。

### 1.3 目标用户

- 量化研究员
- 风险管理团队
- 资产配置决策者

---

## 2. 系统架构

### 2.1 三层框架

```
┌─────────────────────────────────────────────────────┐
│        SYSTEM ORCHESTRATOR (系统协调器)              │
│   输出: NORMAL/CAUTIOUS/DEFENSIVE/CRISIS 状态       │
│         Risk Budget (0.35-1.15)                     │
└─────────────────────────────────────────────────────┘
          ↑              ↑              ↑
    ┌─────┴──────┬──────┴──────┬──────┴──────┐
    │            │             │             │
┌───┴────┐   ┌───┴────┐   ┌────┴────┐
│ FUEL   │   │ CRACK  │   │ TREND   │
│ SCORE  │   │ SCORE  │   │ SCORE   │
│结构层   │   │裂缝层   │   │趋势层    │
├────────┤   ├────────┤   ├─────────┤
│频率:    │   │频率:    │   │频率:     │
│季度     │   │月度     │   │日度      │
│范围:    │   │范围:    │   │范围:     │
│0-100   │   │σ 单位   │   │0-1      │
│滞后:    │   │滞后:    │   │滞后:     │
│3-6月   │   │1-3月    │   │实时      │
└────────┘   └────────┘   └─────────┘
```

### 2.2 层级职责

| 层级 | 问题 | 数据频率 | 输出 |
|------|------|----------|------|
| **Structure (FuelScore)** | 经济结构是否足够脆弱以支撑重大危机？ | 季度 | 0-100 分数 |
| **Crack (CrackScore)** | 结构脆弱性是否在加速恶化？ | 月度 | σ 单位 |
| **Trend (TrendScore)** | 市场当前是否处于压力/紧张状态？ | 日度 | 0-1 热度 |

---

## 3. Structure 层 (FuelScore)

### 3.1 功能描述

衡量长期结构脆弱性积累（债务、估值过高、杠杆）。

### 3.2 核心因子

| 因子 | 名称 | 窗口 | 变换 | IC权重 | AUC权重 |
|------|------|------|------|--------|---------|
| V1 | 短期债务比率 | 10Y | Percentile | 12.2% | 6.4% |
| V4 | 利息覆盖率 | 5Y | Percentile(flip) | 4.6% | 0.0% |
| V5 | TDSP (家庭债务服务) | 5Y | Percentile | 31.3% | 52.0% |
| V7 | Shiller PE (CAPE) | 10Y | Percentile | 14.2% | 28.4% |
| V8 | 保证金债务/市值 | 10Y | Credit Gap | 37.7% | 13.2% |

### 3.3 信号状态

| FuelScore | 信号 | 行动 |
|-----------|------|------|
| 0-20 | EXTREME_LOW | 最大风险偏好 |
| 20-40 | LOW | 正常组合 |
| 40-60 | NEUTRAL | 基线监控 |
| 60-80 | HIGH | 开始降风险 |
| 80-100 | EXTREME_HIGH | 防御模式 |

### 3.4 Risk Budget 公式

```python
risk_budget = clip(1.1 - 0.007 × fuel_score, 0.35, 1.15)
```

---

## 4. Crack 层 (CrackScore)

### 4.1 功能描述

捕捉脆弱性的变化率（从稳定到脆弱的转变）。

### 4.2 计算方法

```python
# 1. 计算滚动 Z-score (10年窗口)
Z_t = zscore(X_t, window=120)

# 2. Z空间中的 Delta
delta_Z = Z_t - Z_{t-w}

# 3. 方向标准化
adjusted = delta_Z × direction  # ICR: -1, 其他: +1

# 4. 仅取恶化方向
crack_i = max(0, adjusted)
```

### 4.3 因子权重

| 因子 | 名称 | 窗口 | 权重 |
|------|------|------|------|
| V4 | 利息覆盖率 | 4Q | 33.3% |
| V8 | 保证金债务 | 8Q | 24.6% |
| V2 | 未保险存款 | 4Q | 17.5% |
| V5 | TDSP | 4Q | 16.6% |

### 4.4 状态机

| CrackScore | 状态 | 含义 |
|------------|------|------|
| < 0.3σ | STABLE | 正常恶化 |
| 0.3-0.5σ | EARLY_CRACK | 早期脆弱 |
| 0.5-1.0σ | WIDENING_CRACK | 裂缝扩大 |
| > 1.0σ | BREAKING | 系统临近崩溃 |

---

## 5. Trend 层 (TrendScore v4.1)

### 5.1 功能描述

基于高频市场数据（VIX、利差、资金流）的实时风险情绪。

### 5.2 四模块架构

```
因子层 (10个因子)
├── A: VTS, SKEW, MOVE (波动率)
├── B: Funding, GCF_IORB (流动性)
├── C: HY_Spread, IG_Spread (信用)
└── D: HYG_Flow, LQD_Flow, TLT_Flow (资金流)
        ↓
模块层 (4个模块 A-D)
├── module_heat = 0.4×max + 0.6×weighted_avg
        ↓
趋势层
└── trend_heat = (Σ W_m × module_heat_m)^1.3
        ↓
状态: CALM/WATCH/ALERT/CRITICAL
```

### 5.3 模块权重

| 模块 | 名称 | 权重 |
|------|------|------|
| A | 波动率 | 25% |
| B | 流动性 | 25% |
| C | 信用 | 30% |
| D | 资金流 | 20% |

### 5.4 数据质量等级

| 等级 | 可用模块 | 用途 |
|------|----------|------|
| STRONG | 4 (A+B+C+D) | 完全升级资格 |
| OK | 3 | Risk Budget 调整 |
| WEAK | 2 | 仅本地信号 |
| NONE | <2 | 使用 Fallback 规则 |

---

## 6. 规则引擎 v2.0

### 6.1 优先级规则

规则按顺序评估，首次匹配即返回：

| 规则 | 名称 | 状态 | 行动 | 条件 |
|------|------|------|------|------|
| R1 | Crisis: Trend CRITICAL + Crack裂缝 | CRISIS | EXIT | trend=CRITICAL, crack∈{WIDENING,BREAKING}, quality∈{OK,STRONG} |
| R2 | Crisis: Crack BREAKING + Trend ALERT+ | CRISIS | EXIT | crack=BREAKING, trend∈{ALERT,CRITICAL} |
| R3 | Defensive: Crack WIDENING + Trend升级 | DEFENSIVE | HEDGE | crack=WIDENING_CRACK, trend∈{WATCH,ALERT,CRITICAL} |
| R4 | Defensive: Fuel EXTREME + Trend ALERT+ | DEFENSIVE | HEDGE | fuel=EXTREME, trend∈{ALERT,CRITICAL} |
| R5 | Cautious: Fuel高位，未点火 | CAUTIOUS | DE-RISK | fuel∈{HIGH,EXTREME}, crack∈{STABLE,EARLY_CRACK} |
| R6 | Cautious: Crack早期裂纹 | CAUTIOUS | DE-RISK | crack=EARLY_CRACK |
| R7 | Normal: 无重大风险 | NORMAL | HOLD | fuel∈{LOW,NEUTRAL}, crack=STABLE, trend∈{CALM,WATCH} |

### 6.2 Fallback 规则

当 Trend 质量为 WEAK/NONE 时使用：

| 规则 | 条件 | 状态 |
|------|------|------|
| R8a | crack=BREAKING | CRISIS |
| R8b | crack=WIDENING_CRACK | DEFENSIVE |
| R8c | crack=EARLY_CRACK | CAUTIOUS |
| R8d | fuel=EXTREME | CAUTIOUS |
| R8e | fuel=HIGH | CAUTIOUS |

### 6.3 Risk Budget 惩罚系统

```python
# 基础公式
base = 1.1 - 0.007 × fuel_score

# 状态乘数
STATE_MULTIPLIERS = {
    'NORMAL': 1.00,
    'CAUTIOUS': 0.85,
    'DEFENSIVE': 0.60,
    'CRISIS': 0.30,
}

# Crack 惩罚
CRACK_PENALTIES = {
    'STABLE': 1.00,
    'EARLY_CRACK': 0.90,
    'WIDENING_CRACK': 0.75,
    'BREAKING': 0.60,
}

# Trend 惩罚 (仅 OK/STRONG 时启用)
TREND_PENALTIES = {
    'CALM': 1.00,
    'WATCH': 0.95,
    'ALERT': 0.85,
    'CRITICAL': 0.70,
}

# 最终
final = clip(base × state_mult × crack_penalty × trend_penalty, 0.35, 1.15)
```

---

## 7. 数据流

### 7.1 数据源

| 数据源 | 类型 | 频率 | 用途 |
|--------|------|------|------|
| FRED API | 宏观数据 | 季度/月度 | Structure/Crack 因子 |
| Yahoo Finance | 市场数据 | 日度 | Trend 因子, SPX |
| 本地 CSV | 历史数据 | - | 缓存和回测 |

### 7.2 Release Lag 配置

| 因子 | 滞后 | 来源 |
|------|------|------|
| V1 | 5月 | Z.1 Financial Accounts |
| V4 | 6月 | BEA NIPA |
| V5 | 3月 | Federal Reserve |
| V7 | 0月 | Shiller CAPE (实时) |
| V8 | 2月 | Fed Flow of Funds |
| V9 | 1月 | SLOOS |

### 7.3 变换类型

| 类型 | 描述 | 输出 |
|------|------|------|
| Percentile | 滚动窗口百分位 | 0-100 |
| Z-score | 滚动标准化 | σ 单位 |
| Credit Gap | 偏离长期趋势 | 0-100 |
| U-shape | \|Pctl-50\|×2 | 0-100 |

---

## 8. 系统输出

### 8.1 Portfolio Action Contract

```python
{
    'date': '2026-01-15',
    'system_state': 'CAUTIOUS',        # NORMAL/CAUTIOUS/DEFENSIVE/CRISIS
    'action': 'DE-RISK',               # HOLD/DE-RISK/HEDGE/EXIT
    'risk_budget': 0.62,               # 0.35-1.15
    'confidence': 'HIGH',              # LOW/MEDIUM/HIGH
    'reason': ['R5: Fuel高位，未点火'],
    'structure': {
        'fuel_score': 67.5,
        'fuel_signal': 'HIGH',
        'fuel_components': {...},
        'risk_budget': 0.62,
    },
    'crack': {
        'crack_score': 0.33,
        'crack_state': 'STABLE',
        'crack_components': {...},
    },
    'trend': {
        'trend_heat': 0.25,
        'trend_state': 'CALM',
        'data_quality': {'quality_level': 'STRONG'},
        'module_heat': {...},
    },
}
```

### 8.2 状态-行动映射

| 系统状态 | 行动 | 含义 |
|----------|------|------|
| NORMAL | HOLD | 正常运营 |
| CAUTIOUS | DE-RISK | 降低敞口 |
| DEFENSIVE | HEDGE | 激活对冲 |
| CRISIS | EXIT | 紧急退出 |

---

## 9. 用户界面

### 9.1 Streamlit Dashboard

**功能**:
- 系统状态概览卡片
- 三层分页展示 (Structure/Crack/Trend)
- 因子解释与经济含义
- 历史趋势图表 (叠加 SPX)
- IC vs AUC 权重对比

**启动**:
```bash
streamlit run dashboard_app.py --server.port 8501
```

### 9.2 CLI 接口

```bash
python system_orchestrator.py                    # 查看当前状态
python system_orchestrator.py --update           # 更新数据并显示
python system_orchestrator.py --json out.json    # 导出 JSON
python system_orchestrator.py --update-only      # 仅刷新数据
```

---

## 10. 项目结构

```
indicator_test/
├── config.py                    # 统一配置 (权重、阈值、规则)
├── system_orchestrator.py       # 系统协调器 (主入口)
├── dashboard_app.py             # Streamlit Dashboard
├── pyproject.toml              # 包配置
│
├── core/                        # 核心模块
│   ├── fuel_score.py           # FuelScore 计算
│   ├── crack_score.py          # CrackScore 计算
│   └── __init__.py
│
├── trend/                       # Trend 层
│   ├── trend_score/
│   │   ├── trend_score.py      # TrendScore v4.1
│   │   ├── intensity.py        # 强度映射
│   │   └── config.py           # 因子区间配置
│   └── data/                   # 日度因子数据
│
├── data/                        # 数据层
│   ├── loader.py               # 统一数据加载器
│   └── __init__.py
│
├── utils/                       # 工具函数
│   ├── transforms.py           # 数据变换
│   └── __init__.py
│
├── validation/                  # 验证模块
│   ├── ic_calculator.py        # IC 计算
│   ├── auc_calculator.py       # AUC 计算
│   └── __init__.py
│
├── lib/                         # 研究库 (已废弃部分)
│   ├── transform_layers.py     # [DEPRECATED]
│   └── ...
│
└── structure/                   # Structure 层数据
    └── data/
        ├── raw/                # 原始数据
        └── lagged/             # 滞后调整数据
```

---

## 11. 历史验证

### 11.1 危机回测

| 事件 | FuelScore | CrackScore | TrendScore | 预警时间 |
|------|-----------|------------|------------|----------|
| Dot-com (2000) | ~80 | ~2.0σ | ALERT | 数月 |
| GFC (2008) | 60-75 | ~2.5σ | CRITICAL | 数月 |
| COVID (2020) | ~65 | ~1.5σ | CRITICAL | 即时 |

### 11.2 数据可用性

- **Trend 因子**: 1986-至今 (完整日度)
- **Structure 因子**: 1990-至今 (季度)
- **完整系统**: 1998-至今 (4个 Trend 模块齐全)

---

## 12. 技术规格

### 12.1 环境要求

```
Python >= 3.9
```

### 12.2 核心依赖

```
pandas >= 1.5.0
numpy >= 1.21.0
scipy >= 1.9.0
matplotlib >= 3.5.0
fredapi >= 0.5.0
yfinance >= 0.2.0
streamlit >= 1.20.0
```

### 12.3 环境变量

```bash
export FRED_API_KEY='your_fred_api_key'  # 必需
```

---

## 13. 近期改进 (2026-01)

### 13.1 已完成

| 改进 | 文件 | 描述 |
|------|------|------|
| 移除硬编码 API key | config.py | 改为环境变量 + 警告 |
| 创建包结构 | pyproject.toml | 标准 Python 包配置 |
| 声明式规则引擎 | config.py | PRIORITY_RULES / FALLBACK_RULES |
| 提取加权分数逻辑 | fuel_score.py | `_weighted_score()` 静态方法 |
| 命名常量 | ic_calculator.py | MIN_SAMPLES_FULL 等 |
| 修复异常处理 | auc_calculator.py | 捕获具体异常类型 |
| 废弃旧模块 | transform_layers.py | 添加 DeprecationWarning |

### 13.2 待优化

- [ ] 滚动计算向量化 (性能优化)
- [ ] 完全移除 sys.path 操作 (使用相对导入)
- [ ] Dashboard 图表函数提取公共逻辑
- [ ] 添加单元测试覆盖

---

## 14. 快速开始

### 14.1 安装

```bash
cd indicator_test
pip install -e .
```

### 14.2 基本用法

```python
from system_orchestrator import SystemOrchestrator

# 创建实例
orch = SystemOrchestrator(use_lagged=True)

# 获取系统状态
result = orch.compute_portfolio_action()

print(f"状态: {result['system_state']}")
print(f"行动: {result['action']}")
print(f"Risk Budget: {result['risk_budget']:.2f}")
```

### 14.3 单层访问

```python
from core.fuel_score import FuelScore
from core.crack_score import CrackScore

# Fuel
fuel = FuelScore(weight_scheme='ic')
print(f"Fuel: {fuel.compute()['fuel_score']:.1f}")

# Crack
crack = CrackScore()
print(f"Crack: {crack.compute()['crack_score']:.2f}σ")
```

---

## 附录 A: 关键阈值汇总

| 参数 | 值 | 用途 |
|------|-----|------|
| Risk Budget Base | 1.1 | 基础上限 |
| Risk Budget Slope | -0.007 | 每单位 FuelScore 扣减 |
| Risk Budget Min | 0.35 | 下限 |
| Risk Budget Max | 1.15 | 上限 |
| Fuel LOW | 20 | 低风险阈值 |
| Fuel NEUTRAL | 40 | 中性阈值 |
| Fuel HIGH | 60 | 高风险阈值 |
| Fuel EXTREME | 80 | 极端阈值 |
| Crack STABLE | 0.3σ | 稳定上限 |
| Crack EARLY | 0.5σ | 早期裂纹 |
| Crack WIDENING | 1.0σ | 扩大裂缝 |
| Trend CALM | 0.30 | 平静上限 |
| Trend WATCH | 0.50 | 观察上限 |
| Trend ALERT | 0.70 | 预警上限 |
| MIN_SAMPLES_FULL | 30 | IC 计算最小样本 |
| MIN_SAMPLES_REGIME | 20 | 分区 IC 最小样本 |
| IC_SIGNIFICANCE | 0.01 | IC 显著性阈值 |

---

## 附录 B: 文档索引

| 文档 | 描述 |
|------|------|
| INDICATOR_SYSTEM_OVERVIEW.md | 完整技术规格 (中文) |
| ARCHITECTURE.md | 高层架构概览 |
| METHODOLOGY_REPORT.md | 详细理论方法论 |
| CRACK_LAYER_METHODOLOGY.md | Crack 层细节 |
| trend/trend_score/README.md | TrendScore 详细文档 |
| CLAUDE.md | 开发指南 |
