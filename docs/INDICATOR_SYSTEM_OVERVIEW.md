# Indicator System 技术文档

## 概述

本系统包含三个层次的风险指标框架，分别从不同维度评估市场风险：

| 层次 | 名称 | 视角 | 数据频率 | 输出范围 |
|------|------|------|----------|----------|
| **Structure** | FuelScore | 宏观结构性脆弱度 | 季度 | 0-100 |
| **Crack** | CrackScore | 边际恶化信号 | 月度 | 状态机 |
| **Trend** | TrendScore | 实时市场动量 | 日度 | 0-1 |

---

## 零、System Contract（输出契约）

### 0.1 输出目标

系统对外只输出三类东西：
1. **风险预算（Risk Budget）**：长期上限
2. **升级/降级状态机（Escalation State）**：中期结构恶化
3. **实时压力（Trend Heat）**：短期风险情绪

**升级动作必要条件**：
```
Trend 质量 OK/STRONG + Crack 至少 EARLY_CRACK + Structure Fuel 高位/恶化
```
具体规则见 4.3 决策框架。

---

### 0.2 三层输出字段（固定 schema）

#### A) Structure Layer Output（季度 / 月度滞后）

| Field | Type | Range | Meaning |
|-------|------|-------|---------|
| date | date | - | 数据时间点 |
| fuel_score | float | 0~100 | 结构燃料存量 |
| fuel_signal | enum | EXTREME_LOW/LOW/NEUTRAL/HIGH/EXTREME_HIGH | FuelScore 分档 |
| fuel_components | dict | - | 各因子 fuel 值、权重、贡献 |
| risk_budget | float | 0.0~1.0 | 推荐风险敞口上限（长期） |
| notes | str | - | 当前燃料主导来源（例如估值主导/杠杆主导）|

**目的**：给资产配置一个长期风险预算上限（不依赖价格信号）。

#### B) Crack Layer Output（月度 / 滞后）

| Field | Type | Range | Meaning |
|-------|------|-------|---------|
| date | date | - | 数据时间点 |
| crack_score | float | σ | 边际恶化强度（只计恶化）|
| crack_state | enum | STABLE/EARLY_CRACK/WIDENING_CRACK/BREAKING | 裂缝状态机 |
| crack_components | dict | - | 各因子 crack 值、权重、贡献 |
| dominant_crack | str | - | 当前最主要裂缝来源（V4/V8/V2/V5…）|

**目的**：检测"燃料是否在加速恶化"，作为升级的必要条件之一。

#### C) Trend Layer Output（日度 / 实时）

| Field | Type | Range | Meaning |
|-------|------|-------|---------|
| date | date | - | 数据日期 |
| trend_heat | float | 0~1 | 实时压力热度 |
| trend_state | enum | CALM/WATCH/ALERT/CRITICAL/INSUFFICIENT_DATA | 状态机输出 |
| data_quality | dict | - | coverage_modules / quality_level / reason |
| module_heat | dict | 0~1 | A/B/C/D 模块 heat |
| factor_intensity | dict | 0~1 | 各因子 intensity |
| dominant_module | str | - | 当前主要压力来源（Credit / Vol / Funding / Flow）|

**目的**：短期风险情绪（但必须经过质量门槛才能触发升级动作）。

---

### 0.3 最终系统输出（Portfolio Action Output）

| Field | Type | Meaning |
|-------|------|---------|
| system_state | enum | NORMAL/CAUTIOUS/DEFENSIVE/CRISIS |
| action | enum | HOLD/DE-RISK/HEDGE/EXIT |
| risk_budget | float | 风险预算（来自 Structure + 状态机调整）|
| confidence | enum | LOW/MEDIUM/HIGH |
| reason | list[str] | 触发原因解释（可读句子）|

**Risk Budget 公式**：
```python
# FuelScore in [0,100]
risk_budget = clip(1.1 - 0.007 * fuel_score, 0.35, 1.15)
```

---

## 一、Structure 层 (FuelScore)

### 1.1 设计理念

Structure 层测量经济系统的"燃料积累"程度 —— 危机发生需要的结构性前提条件。

**核心问题**：当前经济结构是否脆弱到足以支持一次重大危机？

### 1.2 因子清单

系统包含 7 个候选因子，分为三类角色：
- **Fuel 因子**：参与 FuelScore 聚合（权重 > 0）
- **Auxiliary 因子**：作为结构背景监控（暂不进入 FuelScore）
- **Trigger 因子**：结构内生触发器（不进入 FuelScore，用于升级规则）

| 因子 | 名称 | Transform | 权重 | Role | 说明 |
|------|------|-----------|------|------|------|
| **V1** | ST Debt Ratio | Percentile(10Y) | 12.2% | Amplifier | 短债占比水位（结构背景+传导确认）|
| V2_old | Unstable Deposits | - | - | Archived | 已 Reject：H.8 汇总机制不成立 |
| V2 | Uninsured Deposits Ratio | Percentile(10Y) | 0% | Auxiliary | 未保险存款比例（样本短，稳定性不足）|
| **V4** | Interest Coverage (ICR) | Percentile(10Y) Flipped | 4.6% | Fuel | 企业偿债缓冲水位（低=危险）|
| **V5** | TDSP | Percentile(5Y) | 31.3% | Fuel | 家庭偿债负担（GFC-like 场景放大器）|
| **V7** | Shiller PE (CAPE) | Z-score(10Y) | 14.2% | Fuel | 估值燃料存量（风险预算+放大器）|
| **V8** | Margin Debt / MktCap | Z-score(10Y) | 37.7% | Fuel | 杠杆脆弱度（稳定器/放大器）|
| V9 | CRE Lending Standards (SLOOS) | - | - | Trigger | 银行 CRE 贷款标准（双向触发）|

> FuelScore 权重基于 |IC| × Stability。V2（新）因样本短/稳定性不足暂不进入 FuelScore，但保留为银行体系脆弱度监控。

### 1.3 数据特性

- **数据频率**：季度（部分月度）
- **发布滞后**：约 2 个月 (Lagged 数据)
- **主要来源**：FRED API
- **历史覆盖**：1990 年至今

### 1.4 聚合方法

```python
# Step 1: Base weight
w_i* = |IC_i|

# Step 2: Stability penalty (高低利率环境一致性)
s_i = min(1, (|IC_high| + |IC_low|) / (2 * |IC_full|))

# Step 3: Normalize
w_i = (w_i* × s_i) / Σ(w_j* × s_j)

# Step 4: Weighted sum
FuelScore = Σ(w_i × fuel_i)  # 0-100 range
```

### 1.5 状态解读

| FuelScore | Signal | 含义 |
|-----------|--------|------|
| 80-100 | EXTREME HIGH | 极端高风险 |
| 60-80 | HIGH | 高风险 |
| 40-60 | NEUTRAL | 中性 |
| 20-40 | LOW | 低风险 |
| 0-20 | EXTREME LOW | 安全期 |

### 1.6 目录结构

```
structure/
├── V1_ST_Debt_Ratio/
├── V2_Unstable_Deposits/
├── V4_Interest_Coverage/
├── V5_TDSP/
├── V7_Shiller_PE_CAPE/
├── V8_Margin_Debt/
├── V9_CRE_Delinquency/
├── aggregation/
│   ├── ic_return/
│   │   ├── fuel_score_unified.py  # FuelScore 主类
│   │   └── FUEL_SCORE_REPORT.md   # 详细报告
│   └── auc_mdd/                   # AUC 验证
└── data/                          # 数据缓存
```

---

## 二、Crack 层 (CrackScore)

### 2.1 设计理念

Crack 层捕捉结构性脆弱度的"边际恶化"—— 从积累到破裂的过渡信号。

**核心问题**：结构性风险是否正在加速恶化？

### 2.2 方法论

采用 **ΔZ = Z(t) - Z(t-w)** 方法，捕捉标准化空间下的边际恶化速度：

```python
# Step 1: rolling Z-score (统一窗口，例如 10Y)
Z_t = zscore(X_t, window=120)

# Step 2: delta in Z-space
delta_Z = Z_t - Z_{t-w}

# Step 3: direction normalize (正值 = 危险)
adjusted = delta_Z * direction   # ICR: direction=-1, 杠杆/利差: direction=+1

# Step 4: only deterioration (恢复期不抵消风险)
crack_i = max(0, adjusted)
```

其中 `w` 为因子特定的回看窗口（4Q / 8Q / 12M 等）。

**核心特点**：
- 所有因子以 σ 为单位，可跨因子比较
- 只计入"恶化"，恢复期不抵消（避免误判）

### 2.3 聚合逻辑

**线性聚合**：
```python
CrackScore = Σ(w_i × crack_i)  # 单位: σ (标准差)
```

### 2.4 状态机

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| **STABLE** | 稳定 | CrackScore < threshold_1 |
| **EARLY_CRACK** | 早期裂痕 | threshold_1 ≤ CrackScore < threshold_2 |
| **WIDENING_CRACK** | 裂痕扩大 | threshold_2 ≤ CrackScore < threshold_3 |
| **BREAKING** | 破裂 | CrackScore ≥ threshold_3 |

### 2.5 目录结构

```
crack/
├── crack_score.py           # CrackScore 主类
└── data/                    # 数据目录
    ├── raw/                 # 原始数据
    └── lagged/              # 滞后数据
```

---

## 三、Trend 层 (TrendScore v4.1)

### 3.1 设计理念

Trend 层测量实时市场动量和短期风险情绪。

**核心问题**：当前市场是否处于风险偏好恶化的趋势中？

### 3.2 三层聚合架构

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
│  └─────────────────────────────────────────────┘            │
│                         │                                    │
│                         ▼                                    │
│  趋势层 (TrendScore)                                         │
│  ┌─────────────────────────────────────────────┐            │
│  │ trend_heat = (Σ W_m × module_heat_m)^1.3    │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 四大模块

| 模块 | 名称 | 说明 | 因子数 |
|------|------|------|--------|
| **A** | Volatility | 波动率相关指标 | 3 |
| **B** | Funding | 资金面/流动性指标 | 2 |
| **C** | Credit | 信用利差指标 | 2 |
| **D** | Flow | 资金流向指标 | 3 |

### 3.4 十个因子

| 因子 | 名称 | 含义 | 风险映射 |
|------|------|------|----------|
| **A1_VTS** | VIX Term Structure | VIX期限结构倒挂程度 | intensity ↑ = danger |
| **A2_SKEW** | CBOE SKEW Index | 尾部风险定价 | intensity ↑ = danger |
| **A3_MOVE** | MOVE Index | 债券波动率变化率 | intensity ↑ = danger |
| **B1_Funding** | Funding Spread | 银行间资金成本利差 | intensity ↑ = danger |
| **B2_GCF_IORB** | GCF-IORB Spread | Repo市场压力指标 | intensity ↑ = danger |
| **C1_HY_Spread** | HY Credit Spread | 高收益债利差 | intensity ↑ = danger |
| **C2_IG_Spread** | IG Credit Spread | 投资级债利差 | intensity ↑ = danger |
| **D1_HYG_Flow** | HYG Flow | 高收益债ETF资金流 | **禁用** |
| **D2_LQD_Flow** | LQD Flow | 投资级债ETF资金流 | intensity ↑ = danger |
| **D3_TLT_Flow** | TLT Flow | 长期国债ETF资金流 | intensity ↑ = danger |

> Trend 层所有指标最终都通过 transform + danger-zone mapping 映射为 intensity ∈ [0,1]，统一为：**intensity 越高越危险**。原始指标的方向性由验证结果决定，不在技术文档中写死。

### 3.5 三档 Zone

| Zone | 覆盖率目标 | 权重 | 含义 |
|------|-----------|------|------|
| WATCH | 20-30% | 0.4 | 背景监控 |
| ALERT | 10-15% | 0.7 | 风险预警 |
| CRITICAL | 3-7% | 1.0 | 强制行动 |

### 3.6 数据质量分层 (v4.1)

| coverage_modules | quality_level | 输出内容 | 用途 |
|------------------|---------------|----------|------|
| 0 | **NONE** | INSUFFICIENT_DATA | 无法判断 |
| 1 | **WEAK** | 局部信号 | 局部压力提示 |
| 2 | **OK** | TrendScore + State | 可用于 risk budget |
| 3-4 | **STRONG** | TrendScore + State | 可用于 escalation |

### 3.7 历史覆盖率

| 时期 | 可用模块 | quality_level |
|------|----------|---------------|
| 1986-1990 | B only | WEAK |
| 1991-1997 | A+B | OK |
| 1998-2003 | A+B+C | STRONG |
| 2004+ | A+B+C+D | STRONG |

### 3.8 输出状态

| 状态 | 目标占比 | 含义 |
|------|----------|------|
| CALM | 45-60% | 市场平静 |
| WATCH | 20-30% | 需关注 |
| ALERT | 10-15% | 风险预警 |
| CRITICAL | 3-7% | 高风险 |

### 3.9 目录结构

```
trend/
├── trend_score/
│   ├── __init__.py           # 模块入口
│   ├── config.py             # v4.1 配置
│   ├── intensity.py          # 强度映射函数
│   ├── trend_score.py        # TrendScore 主类
│   ├── test_trend_score.py   # 单元测试
│   ├── plot_trend_history.py # 历史可视化
│   └── README.md             # 详细文档
└── data/                     # 因子数据
```

---

## 四、三层协同

### 4.1 时间维度互补

```
Structure (季度)  ──────────────────────────►  长期结构
     │
     ▼
Crack (月度)      ─────────────►  中期恶化
     │
     ▼
Trend (日度)      ──►  短期动量
```

### 4.2 典型使用场景

| 场景 | Structure | Crack | Trend | 解读 |
|------|-----------|-------|-------|------|
| 牛市中期 | 中 | 稳定 | 低 | 风险积累中，但未触发 |
| 牛市末期 | 高 | 早期裂痕 | 低 | 结构脆弱，裂痕出现 |
| 危机前夕 | 高 | 扩大 | 升高 | 全面预警 |
| 危机中 | 高 | 破裂 | 极高 | 危机确认 |
| 危机后 | 下降 | 稳定 | 下降 | 风险释放 |

### 4.3 决策框架

```python
# 0) Trend quality gate (v4.1 核心)
if TrendScore.quality_level == 'NONE':
    action = 'INSUFFICIENT_DATA: 仅输出 Structure/Crack，不执行升级'
elif TrendScore.quality_level == 'WEAK':
    action = 'WEAK_TREND: 仅作为局部压力提示，不触发全局升级'

# 1) Full escalation only when Trend quality OK/STRONG
else:
    if TrendScore.state == 'CRITICAL' and CrackScore.state in ['WIDENING_CRACK', 'BREAKING']:
        action = 'CRISIS MODE: 大幅减仓 / 强对冲'
    elif TrendScore.state in ['ALERT', 'CRITICAL'] and FuelScore > 70:
        action = 'DEFENSIVE: 降低风险敞口 + 增加对冲'
    elif FuelScore > 80 and CrackScore.state == 'EARLY_CRACK':
        action = 'CAUTIOUS: 降低新增风险 + 强化监控'
    else:
        action = 'NORMAL: 维持仓位，常规监控'
```

**解释**：
- **Structure** 决定长期风险预算上限
- **Crack** 决定是否出现结构性恶化趋势
- **Trend** 决定是否发生实时压力（需 quality OK/STRONG 才能升级）

---

## 五、数据依赖

### 5.1 外部数据源

| 数据源 | 用途 | 频率 |
|--------|------|------|
| FRED | 宏观经济数据 | 季度/月度 |
| FINRA | 保证金债务 | 月度 |
| CBOE | VIX, SKEW | 日度 |
| Yahoo Finance | ETF 价格和流量 | 日度 |

### 5.2 核心数据文件

- `SPX 1D Data (1).csv` - SPX 日度数据 (被 20+ 文件引用)
- `Shiller PE Data Dec 23 2025.csv` - Shiller PE 数据

---

## 六、使用示例

### 6.1 TrendScore

```python
from trend.trend_score import TrendScore

ts = TrendScore()
result = ts.compute_latest()

print(f"TrendScore: {result['trend_heat_score']:.3f}")
print(f"State: {result['trend_state']}")
print(f"Quality: {result['data_quality']['quality_level']}")
```

### 6.2 FuelScore

```python
from structure.aggregation.ic_return.fuel_score_unified import UnifiedFuelScore

fs = UnifiedFuelScore()
result = fs.compute_latest()

print(f"FuelScore: {result['fuel_score']:.1f}")
print(f"Signal: {result['signal']}")
```

详细报告见 [FUEL_SCORE_REPORT.md](structure/aggregation/ic_return/FUEL_SCORE_REPORT.md)

---

*Generated: 2026-01-03*
