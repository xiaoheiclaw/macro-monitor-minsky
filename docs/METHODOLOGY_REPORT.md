# 宏观脆弱性风险监测系统：方法论与技术报告

## 摘要

本报告详细阐述了一套基于明斯基金融不稳定假说的三层风险监测系统。该系统整合了结构层（FuelScore）、边际层（CrackScore）和趋势层（TrendScore），旨在为股票市场提供系统性风险的早期预警。

---

# 第一章：理论基础

## 1.1 明斯基金融不稳定假说

**核心观点**：经济危机不是由外部突发事件（如战争、瘟疫）造成的，而是**金融体系内部运作的必然结果**。

**核心逻辑**：在经济繁荣和稳定的时期，投资者、企业和银行会因为自信心的膨胀，逐渐改变他们的风险偏好：

1. **长期稳定导致盲目自信**：如果经济长时间表现良好，人们会忘记过去的风险，认为未来也会一直好下去
2. **债务扩张**：既然未来是美好的，那么借更多的钱来投资（加杠杆）就是理性的
3. **从保守转向激进**：市场融资结构会从安全的"对冲融资"逐渐演变为危险的"庞氏融资"

## 1.2 债务融资的三种状态

| 融资类型 | 风险等级 | 定义 | 关键特征 | 典型比喻 |
|---------|---------|------|---------|---------|
| **对冲性融资** (Hedge Finance) | 最安全 | 经营现金流足以覆盖**本金和利息** | 债务结构健康，对利率上升和宏观波动具备韧性 | 住房按揭：收入可完全覆盖月供 |
| **投机性融资** (Speculative Finance) | 风险累积 | 现金流只能支付**利息**，无法偿还本金 | 依赖持续再融资；对利率上升和信贷收紧敏感 | 过桥贷款企业、只付息债券 |
| **庞氏融资** (Ponzi Finance) | 系统性风险 | 现金流连**利息都无法覆盖** | 必须依赖资产价格持续上涨；价格一停即崩 | 次贷危机中的零首付炒房客 |

## 1.3 危机公式：脆弱性 × 触发点 × 放大器

### 脆弱性（燃料堆积）
- **明斯基语境**：融资结构的退化 (Hedge→Speculative→Ponzi)
- **具体表现**：
  - 庞氏融资占比过高：市场上有太多借款人全靠"资产价格上涨"来还债
  - 期限错配 (Duration Mismatch)：大量借短期资金来投长期资产
  - 安全边际消失：投资者为了追求收益率，把杠杆加满，容错率降至零

### 触发点（火花）
- **常见形式**：
  - 央行加息：资金成本上升，投机性融资者发现利息还不上了
  - 资产升值停滞：房价或股价只要不涨，庞氏融资者就无法通过再融资续命
  - 外部冲击：战争、监管政策突变，导致流动性突然收紧
- **相对性**：在脆弱性低的时候，加息只是正常的宏观调控；在脆弱性高的时候（庞氏融资盛行），加息就是死刑判决

### 放大器（连锁反应）
- **明斯基语境**：资产抛售与债务通缩 (Fire Sales & Debt-Deflation)
- **机制**：
  1. **强制平仓**：当庞氏融资者违约，债权人为了收回资金，被迫拍卖抵押品
  2. **价格崩塌**：大量资产同时被抛售，导致资产价格暴跌
  3. **传染效应**：资产价格暴跌导致原本健康的融资者的抵押物价值不足，引发追加保证金通知 (Margin Call)
  4. **信贷枯竭**：银行看到资产贬值，立即停止放贷，导致流动性黑洞

---

# 第二章：系统架构

## 2.1 三层风险监测框架

本系统采用三层架构，分别捕捉不同时间尺度和风险维度的信号：

```
┌─────────────────────────────────────────────────────────────────┐
│                     系统整合层 (SystemOrchestrator)               │
│         输出：系统状态 (NORMAL/CAUTIOUS/DEFENSIVE/CRISIS)         │
│               风险预算 (Risk Budget: 0.35-1.15)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↑
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐     ┌───────┴───────┐     ┌───────┴───────┐
│   结构层       │     │   边际层       │     │   趋势层       │
│  (FuelScore)  │     │ (CrackScore)  │     │ (TrendScore)  │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ 频率：季度     │     │ 频率：月度     │     │ 频率：日度     │
│ 范围：0-100   │     │ 范围：σ单位   │     │ 范围：0-1     │
│ 滞后：3-6个月 │     │ 滞后：1-3个月 │     │ 滞后：实时     │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
   宏观脆弱性累积         脆弱性恶化速度         市场实时压力
```

## 2.2 核心问题

| 层级 | 回答的问题 | 类比 |
|-----|----------|-----|
| **Structure (FuelScore)** | "经济基础是否脆弱？" | 火药库有多大？ |
| **Crack (CrackScore)** | "脆弱性是否在加速恶化？" | 火药库在变大吗？ |
| **Trend (TrendScore)** | "市场当前是否承压？" | 有人在点火吗？ |

---

# 第三章：Structure/Crack 层因子

Structure层（FuelScore）和Crack层（CrackScore）共享同一组宏观因子，但计算方式不同：
- **FuelScore**：计算因子的**水平**（Level），评估脆弱性累积程度
- **CrackScore**：计算因子的**变化速度**（ΔZ），评估脆弱性恶化速率

## 3.1 因子总结表

| 因子 | 名称 | 计算公式 | 关键发现 | 系统角色 |
|-----|------|---------|---------|---------|
| **V1** | 企业短期债务占比 | 企业短期债务 / 总债务 | IC=0.116, AUC=0.622; 仅高利率环境有效 | **Fuel层**：结构背景指标 (IC权重12.2%) |
| **V2** | 银行活期存款占比 | 未保险存款 / 总存款 × 100% | IC=-0.008(无信号), AUC=0.477; 存在结构性断裂 | **已剔除**：因存在regime leakage |
| **V4** | 企业利息保障倍数 | EBIT / 利息支出 | IC(变化)=-0.408(强), AUC=0.882(优秀); **ICR下降是核心信号** | **Fuel+Crack层**：衡量企业偿债缓冲 (Fuel: 4.6%, Crack: 33.3%) |
| **V5** | 家庭偿债比例 | (房贷+消费贷利息) / 可支配收入 | IC=-0.297(强), AUC=0.737(强); **整体最强预测因子** | **Fuel+Crack层**：系统核心支柱 (Fuel: 31.3%/52.0%, Crack: 16.6%) |
| **V7** | Shiller PE (CAPE) | S&P 500价格 / 10年通胀调整后平均收益 | IC=-0.540(**最强IC**), AUC=0.681; **唯一实时数据因子** | **Fuel+Crack层**：燃料因子 (Fuel: 14.2%/28.4%, Crack: 2.9%) |
| **V8** | 保证金债务比率 | 券商保证金贷款 / 股市总市值 × 100% | IC=-0.427(强), AUC=0.741(优秀); **双信号系统** | **Fuel+Crack层**：杠杆度测量 (Fuel: 37.7%/13.2%, Crack: 24.6%) |
| **V9** | 商业地产贷款标准 | 3个CRE贷款标准指数平均 | IC=0.187(弱), AUC=0.750(强); **双向信号** | **Fuel层**：信贷环境指标 (AUC权重: 38.2%) |

---

## 3.2 因子详述

### 3.2.1 V1: 企业短期债务占比 (Short-Term Debt Ratio)

| 属性 | 值 |
|-----|---|
| **FRED序列** | BOGZ1FL104140006Q |
| **计算公式** | 企业短期债务 / 总债务 |
| **经济含义** | 短债占比越高，企业越依赖持续再融资 |
| **发布滞后** | 5个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M收益 | 0.116 | 弱正相关 (p=0.043) |
| IC (高利率/低利率) | 0.248 / 0.005 | 极不稳定 |
| AUC (MDD<-20%) | 0.622 | 中等 |
| **最终IC权重** | **12.2%** | |
| **最终AUC权重** | **6.4%** | |

**系统角色**：作为Trigger的条件升级器使用，而非独立风险警报。

---

### 3.2.2 V2: 银行活期存款占比 (Uninsured Deposits Ratio) - 已剔除

| 属性 | 值 |
|-----|---|
| **FRED序列** | BOGZ1FL763139105Q / BOGZ1FL763130005Q |
| **计算公式** | 未保险存款 / 总存款 × 100% |
| **经济含义** | 银行挤兑风险指标 |
| **发布滞后** | 6个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M收益 | -0.008 | **无信号** (p=0.902) |
| IC (高利率/低利率) | 0.451 / -0.156 | **方向相反！** |
| AUC (MDD<-20%) | 0.477 | 低于随机 (0.5) |
| **最终权重** | **0.0%** | **已剔除** |

**剔除原因**：存在结构性断裂（post-2008，post-2020），主要反映政策与制度变迁（regime leakage）。

---

### 3.2.3 V4: 企业利息保障倍数 (Interest Coverage Ratio)

| 属性 | 值 |
|-----|---|
| **FRED序列** | A464RC1Q027SBEA (利润) / B471RC1Q027SBEA (利息) |
| **计算公式** | EBIT / 利息支出 |
| **经济含义** | 企业偿债能力；低ICR = 高违约风险 |
| **发布滞后** | 6个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M MDD (水平) | -0.044 | 弱 |
| IC vs 12M MDD (变化) | **-0.408** | **强** |
| AUC (MDD<-20%) | 0.725-0.882 | **优秀** |
| **最终IC权重** | **4.6%** | |

**关键发现**：
- **ICR下降是核心信号**：负变化比正水平更重要
- 最擅长检测**信用驱动型危机**（GFC 2008 = -2.09 Z-score）
- 对**政策冲击型危机**（COVID、2022加息）预测能力差

---

### 3.2.4 V5: 家庭偿债比例 (Total Debt Service Payments Ratio)

| 属性 | 值 |
|-----|---|
| **FRED序列** | TDSP |
| **计算公式** | (房贷+消费贷利息支出) / 可支配收入 |
| **经济含义** | 家庭财务压力 |
| **发布滞后** | 3个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M MDD | -0.297 | **强负相关** (p<0.001) |
| AUC (MDD<-20%) | 0.737 | **强** |
| **最终IC权重** | **31.3%** | **最高IC权重** |
| **最终AUC权重** | **52.0%** | **最高AUC权重** |

**关键发现**：
- **整体最强预测因子**：IC和AUC表现均优异
- **全天候因子**：跨利率环境一致

---

### 3.2.5 V7: Shiller PE (CAPE)

| 属性 | 值 |
|-----|---|
| **数据源** | Robert Shiller官网 |
| **计算公式** | S&P 500价格 / 10年通胀调整后平均收益 |
| **经济含义** | 估值极端程度，均值回归风险 |
| **发布滞后** | 0个月（实时） |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M MDD | -0.540 | **非常强** (p<0.0001) |
| AUC (MDD<-20%) | 0.681 | 良好 |
| **最终IC权重** | **14.2%** | |
| **最终AUC权重** | **28.4%** | |

**关键发现**：
- **最强IC**：-0.540对于经济因子来说非常优秀
- **唯一实时数据因子**（无滞后）
- 不是说**高估值 = 危机**，而是**高估值 + 高杠杆**才危险

---

### 3.2.6 V8: 保证金债务比率 (Margin Debt Ratio)

| 属性 | 值 |
|-----|---|
| **FRED序列** | BOGZ1FL663067003Q / BOGZ1FL893064105Q |
| **计算公式** | 券商保证金贷款 / 股市总市值 × 100% |
| **经济含义** | 系统性杠杆，强制平仓风险 |
| **发布滞后** | 2个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M MDD (水平) | -0.427 | 强 |
| IC vs 12M MDD (速度) | -0.285 | 强 |
| AUC (MDD<-20%) | 0.741 (速度) | **优秀** |
| **最终IC权重** | **37.7%** | **最高IC权重** |

**关键发现**：
- **双信号系统**：水平（绝对高度）+ 速度（2年变化）
- 不对称：预测下行比上行更准

---

### 3.2.7 V9: 商业地产贷款标准 (CRE Lending Standards)

| 属性 | 值 |
|-----|---|
| **FRED序列** | DRTSCLCC, DRTSCILM, DRTSCIS (SLOOS) |
| **计算公式** | 3个CRE贷款标准指数的平均值 |
| **经济含义** | 信贷可得性，CRE估值支撑 |
| **发布滞后** | 1个月 |

**验证结果**：

| 指标 | 数值 | 评估 |
|-----|-----|-----|
| IC vs 12M MDD | 0.187 | 弱正相关 |
| AUC (MDD<-20%) | 0.750 | **强** |
| **最终AUC权重** | 38.2% | |

**关键发现**：
- **双向信号**：
  - Z > 1.5：信贷紧缩冲击（即时风险）
  - Z < -1.5：信贷宽松扭曲（延迟/泡沫风险）

---

## 3.3 因子转换方式

Structure层和Crack层共享同一组因子，但使用不同的转换方法：
- **Fuel层**：计算因子的**水平**（Level），使用Percentile或Credit Gap转换
- **Crack层**：计算因子的**变化速度**（ΔZ），使用Delta Z-score转换

---

### 3.3.1 Fuel层转换配置

#### 转换配置表 (2026-01-04 更新)

| 因子 | 转换方法 | 窗口 | 特殊处理 | 选择依据 |
|-----|---------|-----|---------|---------|
| V1 | Percentile | 120月(10Y) | - | 滚动分位数，直接映射0-100 |
| V2 | Percentile | 120月(10Y) | - | 辅助因子(0%权重) |
| V4 | Percentile | 60月(5Y) | **Flip** | 低ICR=高风险，翻转后高分位=高风险 |
| V5 | Percentile | 60月(5Y) | - | AUC优化(崩盘检测) |
| V7 | Percentile | 120月(10Y) | - | 滚动分位数，直接映射0-100 |
| V8 | **Credit Gap** | 120月(10Y) | 去趋势 | 过滤长期结构性上升趋势 |
| V9 | **U-shape** | 120月(10Y) | 双向 | 信贷紧缩/宽松都是风险 |

#### Percentile转换

```python
def compute_rolling_percentile(series, window=120):
    # 计算当前值在滚动窗口内的分位数
    pctl = (historical < current).sum() / len(historical) * 100
    return pctl  # 直接返回0-100
```

- 分位数 = 0 → Fuel = 0（历史最低）
- 分位数 = 50 → Fuel = 50（历史中位数）
- 分位数 = 100 → Fuel = 100（历史最高）

#### Credit Gap Percentile转换（V8专用）

V8（保证金债务比率）存在长期结构性上升趋势，直接使用Z-score或Percentile会导致永远处于高位。Credit Gap Percentile方法过滤趋势，同时保持良好的信号分布：

```python
def compute_credit_gap(series, window=120):
    # Step 1: 计算长期移动平均（趋势）
    ma = series.rolling(window=window).mean()

    # Step 2: 计算残差（周期性偏离）
    gap = series - ma

    # Step 3: 对残差计算滚动分位数（0-100）
    fuel = rolling_percentile(gap, window=window)
```

**方法选择验证**（vs Forward 12M Return/MDD）：

| 方法 | IC | AUC | Median | 分布问题 |
|-----|-----|-----|--------|---------|
| Z-score | -0.427 | 0.718 | N/A | 长期趋势导致永远高位 |
| clip(0,3) | -0.139 | 0.769 | 0 | **48%时间为0**，信号稀疏 |
| **Gap Percentile** | **-0.204** | **0.753** | **58** | 分布均匀，无极端聚集 |

**选择Gap Percentile的原因**：
- **IC权衡**：-0.204 vs Z-score的-0.427，预测力略低但无趋势污染
- **AUC稳健**：0.753 vs clip(0,3)的0.769，崩盘检测能力接近
- **分布健康**：Median=58，仅1.6%时间为0（vs clip方法的48%）
- **信号连续**：避免clip方法导致的"要么0要么高"的离散问题

#### U形转换（双向信号）

```python
def compute_ushape_transform(series, window=120):
    pctl = compute_rolling_percentile(series, window=window)
    fuel = abs(pctl - 50) * 2  # |分位数 - 50| × 2
```

| 信贷状况 | 分位数 | Fuel Score | 风险类型 |
|---------|-------|-----------|---------|
| 极度紧缩 | ~95 | ~90 | 即时风险 |
| 正常 | ~50 | ~0 | 安全 |
| 极度宽松 | ~5 | ~90 | 延迟风险 |

---

### 3.3.2 Crack层转换配置

Crack层计算因子的**变化速度**，核心公式为Delta Z-score：

#### 计算公式

```python
def compute_crack_signal(series, factor_name):
    # Step 1: 计算滚动Z-score（10年窗口）
    zscore = compute_rolling_zscore(series, window=120)

    # Step 2: 计算Delta Z-score（因子特定窗口）
    delta_window = DELTA_WINDOWS[factor_name] * 3  # 季度转月度
    delta_z = zscore - zscore.shift(delta_window)

    # Step 3: 应用方向调整
    direction = DIRECTIONS[factor_name]
    adjusted_signal = delta_z * direction

    return adjusted_signal
```

#### 方向配置表

不同因子的"恶化"方向不同：

| 因子 | 方向 | 含义 | 危险信号 |
|-----|------|------|---------|
| V1 | +1 | 短期债务占比上升是坏事 | ΔZ > 0 |
| V2 | +1 | 未保险存款上升是坏事 | ΔZ > 0 |
| V4 | **-1** | 利息保障倍数**下降**是坏事 | ΔZ < 0 |
| V5 | +1 | 偿债比例上升是坏事 | ΔZ > 0 |
| V7 | +1 | CAPE上升是坏事 | ΔZ > 0 |
| V8 | +1 | 保证金债务上升是坏事 | ΔZ > 0 |

> **注意**：V4的方向为-1，因为ICR（利息保障倍数）是"越高越好"的因子，所以ICR下降才是风险信号。

#### Delta窗口配置表

| 因子 | Delta窗口 | 月数 | 选择依据 |
|-----|----------|-----|---------|
| V1 | 4季度 | 12月 | 标准年度变化 |
| V2 | 4季度 | 12月 | 标准年度变化 |
| V4 | 4季度 | 12月 | 标准年度变化 |
| V5 | 4季度 | 12月 | 标准年度变化 |
| V7 | 4季度 | 12月 | 标准年度变化 |
| V8 | **8季度** | **24月** | 杠杆周期较长，需要更长窗口 |

#### 状态映射

Crack信号（调整后的ΔZ）映射到四档状态：

| 状态 | 阈值 | 含义 |
|-----|------|------|
| **STABLE** | ΔZ < 0.5σ | 结构稳定，无显著恶化 |
| **EARLY_CRACK** | 0.5σ ≤ ΔZ < 1.0σ | 早期裂纹，开始恶化 |
| **WIDENING_CRACK** | 1.0σ ≤ ΔZ < 1.5σ | 裂缝扩大，明显恶化 |
| **BREAKING** | ΔZ ≥ 1.5σ | 结构破裂，急剧恶化 |

#### 示例：V4 (ICR) 的Crack计算

```
假设 ICR 的 Z-score 序列：
- 12月前: Z = 0.5 (略高于均值)
- 当前:   Z = -1.0 (低于均值)

计算:
- delta_z = -1.0 - 0.5 = -1.5
- direction = -1 (ICR下降是坏事)
- adjusted_signal = -1.5 × (-1) = +1.5σ

结果: BREAKING 状态 (≥1.5σ)
解读: ICR在12个月内下降了1.5个标准差，信用风险急剧恶化
```

---

# 第四章：Trend 层因子

TrendScore 是实时市场压力指标，采用四模块架构监控日度级别的市场压力。

## 4.1 因子总结表

| 因子 | 名称 | 模块 | 计算公式 | 关键发现 | 状态 |
|-----|------|-----|---------|---------|-----|
| **A1_VTS** | VIX期限结构 | A-波动率 | VIX/VIX3M - 1 | AUC=0.583, IC=-0.104, Lead=1月; 高分位=倒挂=短期恐慌 | 启用 |
| **A2_SKEW** | CBOE SKEW指数 | A-波动率 | CBOE SKEW 1Y分位数 | AUC=0.451, IC=0.022; 极端高位反而不危险 | 启用(弱) |
| **A3_MOVE** | MOVE债券波动率 | A-波动率 | MOVE指数ΔZ-score | **AUC=0.846**, IC=-0.402, Lead=3月; **最强因子** | 启用 |
| **B1_Funding** | 资金利差 | B-流动性 | TED(pre-2018) + EFFR-SOFR(post-2018) | AUC=0.558, IC=0.051, Lead=1月 | 启用 |
| **B2_GCF_IORB** | GCF-IORB利差 | B-流动性 | GCF Repo Rate - EFFR | AUC=0.377, IC=0.082; 极端高位代表正常化 | 启用(弱) |
| **C1_HY_Spread** | 高收益债利差 | C-信用 | HY OAS 1Y分位数 | **AUC=0.773**, IC=-0.373, Lead=2月; 信用风险溢价 | 启用 |
| **C2_IG_Spread** | 投资级债利差 | C-信用 | IG OAS 1Y分位数 | **AUC=0.804**, IC=-0.386, Lead=2月; 避险情绪蔓延 | 启用 |
| **D1_HYG_Flow** | HYG资金流 | D-资金流 | HYG ETF资金流ΔZ | AUC=0.500, IC=0.000; 验证未通过 | **禁用** |
| **D2_LQD_Flow** | LQD资金流 | D-资金流 | LQD ETF资金流分位数 | AUC=0.386, IC=0.207; IG债被抛售 | 启用(弱) |
| **D3_TLT_Flow** | TLT资金流 | D-资金流 | TLT ETF资金流Z-score | AUC=0.552, IC=0.024, Lead=1月 | 启用(弱) |

---

## 4.2 因子详述

### 4.2.1 模块A: 波动率机制 (Volatility Regime)

#### A1_VTS: VIX期限结构

| 属性 | 值 |
|-----|---|
| **数据源** | CBOE VIX, VIX3M |
| **计算公式** | VIX / VIX3M - 1 |
| **经济含义** | 正值 = 短期恐慌 > 长期预期（期限结构倒挂） |
| **转换方式** | 5年滚动分位数 |
| **危险方向** | 高 → 危险 |

**验证结果**：AUC=0.583, IC=-0.104, Lift=1.55x, Lead=1月, 通过5/5 Gates

---

#### A2_SKEW: CBOE SKEW指数

| 属性 | 值 |
|-----|---|
| **数据源** | CBOE SKEW Index |
| **计算公式** | SKEW 1年滚动分位数 |
| **经济含义** | 尾部风险定价；低位 = 市场对下跌保护需求低（自满） |
| **转换方式** | 1年滚动分位数 |
| **危险方向** | 高 → 危险（但极端高位反而安全） |

**验证结果**：AUC=0.451, IC=0.022, 通过2/5 Gates（弱因子）

---

#### A3_MOVE: 债券波动率指数

| 属性 | 值 |
|-----|---|
| **数据源** | ICE BofA MOVE Index |
| **计算公式** | MOVE 1年ΔZ-score |
| **经济含义** | 债券波动率快速上升 = 利率不确定性飙升 |
| **转换方式** | 1年滚动ΔZ-score |
| **危险方向** | 高 → 危险 |

**验证结果**：**AUC=0.846**, IC=-0.402, Lift=2.49x, Lead=3月, 通过5/5 Gates（**最强因子**）

---

### 4.2.2 模块B: 资金/流动性 (Funding / Liquidity)

#### B1_Funding: 资金利差

| 属性 | 值 |
|-----|---|
| **数据源** | FRED: TED Spread (pre-2018), EFFR-SOFR (post-2018) |
| **计算公式** | TED或EFFR-SOFR拼接后1年分位数 |
| **经济含义** | 银行间资金成本 - 无风险利率；正值 = 流动性紧张 |
| **转换方式** | 1年滚动分位数（拼接序列） |
| **危险方向** | 高 → 危险 |

**验证结果**：AUC=0.558, IC=0.051, Lift=1.28x, Lead=1月, 通过4/5 Gates

---

#### B2_GCF_IORB: Repo市场利差

| 属性 | 值 |
|-----|---|
| **数据源** | DTCC GCF Repo Rate, Fed IORB |
| **计算公式** | GCF Repo Rate - EFFR |
| **经济含义** | Repo市场压力指标；偏离 = 货币市场摩擦 |
| **转换方式** | 1年滚动分位数 |
| **危险方向** | 高 → 危险（但极端高位代表正常化） |

**验证结果**：AUC=0.377, IC=0.082, 通过2/5 Gates（弱因子）

---

### 4.2.3 模块C: 信用补偿 (Credit Compensation)

#### C1_HY_Spread: 高收益债利差

| 属性 | 值 |
|-----|---|
| **数据源** | ICE BofA US High Yield OAS |
| **计算公式** | HY OAS 1年滚动分位数 |
| **经济含义** | 高收益债利差上升 = 信用风险偏好恶化 |
| **转换方式** | 1年滚动分位数 |
| **危险方向** | 高 → 危险 |

**验证结果**：**AUC=0.773**, IC=-0.373, Lift=1.89x, Lead=2月, 通过5/5 Gates

---

#### C2_IG_Spread: 投资级债利差

| 属性 | 值 |
|-----|---|
| **数据源** | ICE BofA US Corporate OAS |
| **计算公式** | IG OAS 1年滚动分位数 |
| **经济含义** | 投资级债利差上升 = 连优质信用都被抛售 |
| **转换方式** | 1年滚动分位数 |
| **危险方向** | 高 → 危险 |

**验证结果**：**AUC=0.804**, IC=-0.386, Lift=1.81x, Lead=2月, 通过5/5 Gates

---

### 4.2.4 模块D: 资金流确认 (Flow Confirmation)

#### D1_HYG_Flow: 高收益债ETF资金流 - **已禁用**

| 属性 | 值 |
|-----|---|
| **数据源** | iShares HYG ETF Fund Flow |
| **计算公式** | 资金流(取负) 1年ΔZ-score |
| **经济含义** | 正值 = 资金流出 = 高收益债被抛售 |
| **状态** | **禁用** - 验证未通过 (2/5 Gates) |

**禁用原因**：AUC=0.500（等于随机），IC=0.000，无预测能力

---

#### D2_LQD_Flow: 投资级债ETF资金流

| 属性 | 值 |
|-----|---|
| **数据源** | iShares LQD ETF Fund Flow |
| **计算公式** | 资金流(取负) 1年分位数 |
| **经济含义** | 正值 = 资金流出 = IG债被抛售 |
| **转换方式** | 1年滚动分位数 |
| **危险方向** | 高 → 危险 |

**验证结果**：AUC=0.386, IC=0.207, 通过2/5 Gates（弱因子）

---

#### D3_TLT_Flow: 长期国债ETF资金流

| 属性 | 值 |
|-----|---|
| **数据源** | iShares TLT ETF Fund Flow |
| **计算公式** | 资金流(取负) 3年Z-score |
| **经济含义** | 正值 = 资金流出 = 避险逆转 |
| **转换方式** | 3年滚动Z-score |
| **危险方向** | 高 → 危险 |

**验证结果**：AUC=0.552, IC=0.024, Lift=1.21x, Lead=1月, 通过3/5 Gates

---

## 4.3 因子转换方式

### 转换配置表

| 因子 | 转换方法 | 窗口 | 特殊处理 |
|-----|---------|-----|---------|
| A1_VTS | 分位数 | 5年 | - |
| A2_SKEW | 分位数 | 1年 | 极端高位不危险 |
| A3_MOVE | ΔZ-score | 1年 | **Z-score映射** |
| B1_Funding | 分位数 | 1年 | TED/EFFR-SOFR拼接 |
| B2_GCF_IORB | 分位数 | 1年 | 极端高位代表正常化 |
| C1_HY_Spread | 分位数 | 1年 | - |
| C2_IG_Spread | 分位数 | 1年 | - |
| D2_LQD_Flow | 分位数 | 1年 | 取负（流出=正） |
| D3_TLT_Flow | Z-score | 3年 | 取负（流出=正），**Z-score映射** |

### Z-score 到分位数的映射

对于使用 Z-score 作为转换方法的因子（A3_MOVE, D3_TLT_Flow），需要将 Z-score 映射到 0-100 分位数刻度，以便与三档 Zone 配置兼容。

**映射公式**：
```python
def zscore_to_pctl(zscore, z_min=-3, z_max=3):
    pctl = (zscore - z_min) / (z_max - z_min) * 100
    return clip(pctl, 0, 100)
```

**映射对照表**：
| Z-score | 映射分位数 | 说明 |
|---------|-----------|------|
| -3 | 0 | 低于均值3个标准差 |
| -2 | 16.7 | 低于均值2个标准差 |
| -1 | 33.3 | 低于均值1个标准差 |
| **0** | **50** | **均值（中性）** |
| +1 | 66.7 | 高于均值1个标准差 |
| +2 | 83.3 | 高于均值2个标准差 |
| +3 | 100 | 高于均值3个标准差 |

**映射后分布**（基于历史数据）：

| 因子 | 原始Z范围 | 截断到0 | 截断到100 | 中位数 |
|-----|----------|---------|-----------|-------|
| A3_MOVE | -10.4 ~ +11.4 | 3.0% | 4.1% | 48.3 |
| D3_TLT_Flow | -5.6 ~ +2.7 | 1.5% | 0.0% | 52.8 |

**选择 [-3, +3] 区间的原因**：
- 正态分布假设下，99.7% 的数据落在 ±3σ 内
- 超出范围的极端值截断到 0 或 100，约占 3-7%
- 映射后中位数约 50，与分位数因子的刻度统一

### 三档Zone映射

每个因子根据转换后的分位数映射到三档Zone（Z-score因子先经过上述映射）：

| Zone | 覆盖率目标 | 权重 | 含义 |
|-----|-----------|-----|-----|
| WATCH | 20-30% | 0.4 | 背景监控 |
| ALERT | 10-15% | 0.7 | 风险预警 |
| CRITICAL | 3-7% | 1.0 | 强制行动 |

---

# 第五章：三层系统实现

## 5.1 三层聚合逻辑对比

### 设计理念

三层系统针对不同频率和特性的数据，采用不同复杂度的聚合方式：

| 层级 | 数据频率 | 聚合复杂度 | 原因 |
|-----|---------|-----------|------|
| FuelScore | 季度 | 最简单 | 慢变量，无噪音 |
| CrackScore | 季度 | 中等 | 变化率信号，需截断 |
| TrendScore | 日度 | 最复杂 | 高频噪音，需去噪 + 尖峰捕捉 |

### 聚合公式对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FuelScore (最简单)                                                          │
│                                                                             │
│   FuelScore = Σ(weight × factor_pctl) / Σ(weight)                          │
│                                                                             │
│   - 简单加权平均                                                            │
│   - 输出: 0-100                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ CrackScore (中等)                                                           │
│                                                                             │
│   CrackScore = Σ(weight × max(0, ΔZ)) / Σ(weight)                          │
│                                                                             │
│   - max(0, ΔZ): 只计入恶化方向，改善不贡献                                  │
│   - 输出: σ 单位 (通常 0-3)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TrendScore (最复杂)                                                         │
│                                                                             │
│   Step 1: pctl → Zone → intensity (离散化去噪)                              │
│   Step 2: module_heat = 0.4×max + 0.6×weighted_avg (尖峰+广谱)              │
│   Step 3: trend_heat = raw_heat^1.3 (非线性压缩)                            │
│                                                                             │
│   - 三层聚合 + 非线性压缩                                                   │
│   - 输出: 0-1                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 为什么 TrendScore 最复杂？

| 问题 | TrendScore 解决方案 | Fuel/Crack 为何不需要 |
|-----|--------------------|--------------------|
| 日内噪音 | Zone 离散化 (SAFE/WATCH/ALERT/CRITICAL) | 季度数据天然平滑 |
| 单因子假警报 | max/avg 混合 (40%/60%) | 因子数少，无需分组 |
| 中等热度误报 | γ=1.3 非线性压缩 | 季度信号稀疏，无需压缩 |
| 模块间协调 | 模块层聚合 | 无模块概念 |

### 状态覆盖率对比

| 状态 | FuelScore | CrackScore | TrendScore |
|-----|-----------|------------|------------|
| 正常 (60%+) | LOW/NEUTRAL <60 | STABLE <0.5σ | CALM <0.30 |
| 关注 (20-25%) | HIGH 60-80 | EARLY_CRACK 0.5-1.0σ | WATCH 0.30-0.50 |
| 警告 (10-15%) | - | WIDENING_CRACK 1.0-1.5σ | ALERT 0.50-0.70 |
| 危机 (1-5%) | EXTREME HIGH >80 | BREAKING ≥1.5σ | CRITICAL ≥0.70 |

---

## 5.2 结构层：FuelScore

**目的**：测量长期宏观脆弱性累积（0-100量表）

**计算公式**：
$$FuelScore = \frac{\sum_i w_i \times fuel_i}{\sum_j w_j}, \quad \text{其中 } w_j > 0$$

**信号阈值**：
| 范围 | 信号 | 含义 |
|-----|-----|-----|
| 80-100 | EXTREME HIGH | 极端高风险 |
| 60-80 | HIGH | 高风险 |
| 40-60 | NEUTRAL | 中性 |
| 20-40 | LOW | 低风险 |
| 0-20 | EXTREME LOW | 极端低风险 |

**权重方案**：

| 因子 | IC权重 | AUC权重 |
|-----|-------|--------|
| V1 | 12.2% | 6.4% |
| V4 | 4.6% | 0.0% |
| V5 | **31.3%** | **52.0%** |
| V7 | 14.2% | 28.4% |
| V8 | **37.7%** | 13.2% |

---

## 5.3 边际层：CrackScore

**目的**：追踪脆弱性因子的变化速率（ΔZ）

**Delta Z-Score计算**：
```python
1. 计算滚动Z-score: z_t = (x_t - mean[t-120:t]) / std[t-120:t]
2. 计算回看窗口内的变化: ΔZ_t = z_t - z_{t-delta_window}
3. 应用因子特定方向: V4乘以-1（低ICR=坏），其余乘以+1
```

**Crack状态**：
| 状态 | 阈值 | 含义 |
|-----|-----|-----|
| STABLE | ΔZ < 0.5σ | 正常恶化速度 |
| EARLY_CRACK | 0.5 ≤ ΔZ < 1.0σ | 令人担忧 |
| WIDENING_CRACK | 1.0 ≤ ΔZ < 1.5σ | 严重恶化 |
| BREAKING | ΔZ ≥ 1.5σ | 危机加速 |

**权重方案**：
| 因子 | 权重 | 回看窗口 |
|-----|-----|---------|
| V4 | **33.3%** | 4Q |
| V8 | **24.6%** | 8Q |
| V2 | 17.5% | 4Q |
| V5 | 16.6% | 4Q |
| V1 | 5.1% | 4Q |
| V7 | 2.9% | 4Q |

---

## 5.4 趋势层：TrendScore

**目的**：实时市场压力指标（0-1量表）

**四模块架构**：
| 模块 | 名称 | 因子 | 经济含义 |
|-----|-----|-----|---------|
| A | 波动率机制 | VIX期限、SKEW、MOVE | 股票/债券期权定价 |
| B | 资金/流动性 | EFFR-SOFR利差、GCF-IORB利差 | 短期资金压力 |
| C | 信用补偿 | HY利差、IG利差 | 风险溢价扩大 |
| D | 资金流确认 | LQD、TLT资金流 | Risk-on/off资金流 |

---

### 5.4.1 TrendScore 聚合流程概览

```
因子层 ──────────► 模块层 ──────────► TrendScore
pctl → intensity   intensity聚合     module_heat聚合
```

**三层聚合**：
1. **因子层**：pctl (0-100) → intensity (0-1)
2. **模块层**：多因子 intensity → module_heat (0-1)
3. **TrendScore层**：多模块 module_heat → trend_heat (0-1)

---

### 5.4.2 因子层：pctl → intensity

#### Z-score 到分位数的映射

对于使用 Z-score 作为转换方法的因子（A3_MOVE, D3_TLT_Flow），需要先映射到 0-100：

```python
def zscore_to_pctl(zscore, z_min=-3, z_max=3):
    pctl = (zscore - z_min) / (z_max - z_min) * 100
    return clip(pctl, 0, 100)
```

| Z-score | 映射分位数 |
|---------|-----------|
| -3 | 0 |
| -1 | 33.3 |
| 0 | 50 |
| +1 | 66.7 |
| +3 | 100 |

#### 三档 Zone 配置 (v2.1)

每个因子根据**历史分布**设置不重叠的 Zone：

| 档位 | 分位数范围 | 目标覆盖率 | 权重 | 含义 |
|-----|-----------|-----------|-----|-----|
| SAFE | < P60 | ~60% | 0.0 | 无风险信号 |
| WATCH | P60-P85 | ~25% | 0.4 | 背景监控 |
| ALERT | P85-P95 | ~10% | 0.7 | 风险预警 |
| CRITICAL | P95+ | ~5% | 1.0 | 强制行动 |

#### Intensity 计算

```python
def compute_intensity(pctl, zones):
    """
    根据 pctl 落在哪个 Zone，返回对应的 intensity 权重
    """
    if pctl in CRITICAL zone:
        return 1.0
    elif pctl in ALERT zone:
        return 0.7
    elif pctl in WATCH zone:
        return 0.4
    else:  # SAFE
        return 0.0
```

**示例 (A1_VTS)**：
- Zone配置: WATCH(52,82), ALERT(82,94), CRITICAL(94,100)
- pctl=60 → 在 WATCH → intensity=0.4
- pctl=88 → 在 ALERT → intensity=0.7
- pctl=96 → 在 CRITICAL → intensity=1.0
- pctl=40 → SAFE → intensity=0.0

#### 各因子 Zone 配置

| 因子 | WATCH | ALERT | CRITICAL | 说明 |
|-----|-------|-------|----------|------|
| A1_VTS | (52, 82) | (82, 94) | (94, 100) | 标准配置 |
| A2_SKEW | (63, 90) | (90, 98) | - | 极端高位不危险 |
| A3_MOVE* | (54, 79) | (79, 100) | - | P95=100，无CRITICAL |
| B1_Funding | (45, 81) | (81, 94) | (94, 100) | 标准配置 |
| B2_GCF_IORB | (51, 88) | (88, 95) | (95, 100) | 标准配置 |
| C1_HY_Spread | (52, 91) | (91, 98) | (98, 100) | 标准配置 |
| C2_IG_Spread | (56, 92) | (92, 98) | (98, 100) | 标准配置 |
| D2_LQD_Flow | (60, 96) | (96, 100) | - | P95=100，无CRITICAL |
| D3_TLT_Flow* | (57, 69) | (69, 77) | (77, 100) | Z-score转换后分布窄 |

> *表示该因子使用 Z-score transform，Zone 基于转换后的 pctl 分布设置

---

### 5.4.3 模块层：因子 → module_heat

#### 模块内聚合公式

```python
module_heat = α × max(intensities) + (1-α) × weighted_avg(intensities)
```

**参数**：
- α = 0.4 (module_max_weight)
- 1-α = 0.6 (module_avg_weight)

**两个部分的含义**：

| 部分 | 权重 | 捕捉信号 |
|------|------|----------|
| `max(intensities)` | 40% | **尖峰信号**：单个因子极端报警 |
| `weighted_avg(intensities)` | 60% | **广谱升温**：多因子普遍升高 |

#### 因子 Reliability 权重

加权平均使用因子的 reliability 权重（基于验证指标）：

```python
rel_i = 0.4 × clip((AUC-0.5)/0.5, 0, 1)    # AUC 贡献 40%
      + 0.2 × clip(|IC|/0.5, 0, 1)          # IC 贡献 20%
      + 0.4 × clip(Lead/6, 0, 1)            # Lead 贡献 40%
```

#### 计算示例：Module A (Volatility)

假设某天 Module A 的三个因子状态：

| 因子 | pctl | tier | intensity | reliability权重 |
|------|------|------|-----------|----------------|
| A1_VTS | 96 | CRITICAL | 1.0 | 0.5 |
| A2_SKEW | 70 | WATCH | 0.4 | 0.3 |
| A3_MOVE | 60 | SAFE | 0.0 | 0.2 |

**计算过程**：
```python
# max 部分
max_intensity = max(1.0, 0.4, 0.0) = 1.0

# weighted_avg 部分 (按 reliability 加权)
weights = [0.5, 0.3, 0.2]  # 归一化
weighted_avg = 1.0×0.5 + 0.4×0.3 + 0.0×0.2 = 0.62

# 模块热度
module_heat = 0.4 × 1.0 + 0.6 × 0.62 = 0.772
```

#### 设计意图

**场景对比**：

| 场景 | 因子状态 | max | avg | module_heat |
|------|----------|-----|-----|-------------|
| 单因子尖峰 | A1=1.0, A2=0, A3=0 | 1.0 | 0.33 | 0.60 |
| 多因子普涨 | A1=0.4, A2=0.4, A3=0.4 | 0.4 | 0.40 | 0.40 |
| 尖峰+普涨 | A1=1.0, A2=0.7, A3=0.4 | 1.0 | 0.70 | 0.82 |

- 对**单因子极端信号**有响应（通过 max）
- 但不会被单因子完全主导（max 权重只有 40%）
- 更重视**多因子共振**（avg 权重 60%）

---

### 5.4.4 TrendScore层：模块 → trend_heat

#### 跨模块聚合公式

```python
# Step 1: 加权平均
raw_heat = Σ(module_weight × module_heat) / Σ(module_weight)

# Step 2: 非线性压缩
trend_heat = raw_heat ^ γ    # γ = 1.3
```

**模块权重**：由模块内因子的 reliability 权重汇总得到

#### 非线性压缩的作用

γ = 1.3 的效果：

| raw_heat | trend_heat | 压缩幅度 |
|----------|-----------|----------|
| 0.2 | 0.13 | -35% |
| 0.4 | 0.31 | -23% |
| 0.5 | 0.41 | -18% |
| 0.7 | 0.62 | -11% |
| 0.9 | 0.87 | -3% |
| 1.0 | 1.00 | 0% |

**设计意图**：
- **低/中热度**：压缩明显，减少误报
- **高热度**：几乎不压缩，保持对真正危机的敏感度

```
trend_heat
    1.0 ─────────────────────────●
        │                      ╱
    0.8 │                    ╱
        │                  ╱   ← 高热度基本不压缩
    0.6 │                ╱
        │              ╱
    0.4 │           ╱
        │        ╱       ← 中等热度压缩
    0.2 │     ╱
        │  ╱    ← 低热度压缩明显
    0.0 ●─────────────────────────
        0   0.2  0.4  0.6  0.8  1.0  raw_heat
```

---

### 5.4.5 状态判定 (v3.0)

#### 基本阈值

| 状态 | 阈值 | 历史覆盖率 |
|-----|-----|-----------|
| CALM | < 0.30 | ~60% |
| WATCH | 0.30-0.50 | ~25% |
| ALERT | 0.50-0.70 | ~10% |
| CRITICAL | ≥ 0.70 | ~5% |

#### CRITICAL 收紧逻辑

v3.0 对 CRITICAL 判定设置了更严格的门槛：

```python
def determine_trend_state(module_states, trend_heat, alert_modules):
    # 条件1: Credit 模块(C) 达到 CRITICAL（最硬的风险信号）
    credit_critical = module_states['C'].state == 'CRITICAL'

    # 条件2: 多模块联动 + 高热度
    multi_module_stress = (len(alert_modules) >= 2 and
                          trend_heat > CRITICAL_threshold)

    # CRITICAL 判定：必须满足条件1 或 条件2
    if credit_critical or multi_module_stress:
        return 'CRITICAL'
    elif trend_heat >= ALERT_threshold:
        return 'ALERT'
    elif trend_heat >= WATCH_threshold:
        return 'WATCH'
    else:
        return 'CALM'
```

**设计意图**：避免单一模块误触发系统级 CRITICAL

---

## 5.5 SystemOrchestrator

```python
SystemOrchestrator()
├── FuelScore (use_lagged=True, weight_scheme='ic')
│   └── 返回: fuel_score, signal, factor_breakdown
│
├── CrackScore (use_lagged=True)
│   └── 返回: crack_score (σ), state, factor_breakdown
│
├── TrendScore ()
│   └── 返回: trend_heat (0-1), state, module_breakdown
│
└── compute_portfolio_action()
    └── 整合三层 → NORMAL/CAUTIOUS/DEFENSIVE/CRISIS
```

**系统状态矩阵**：
| FuelScore | CrackScore | TrendScore | 系统状态 | 建议操作 |
|-----------|------------|------------|---------|---------|
| LOW | STABLE | CALM | NORMAL | HOLD |
| HIGH | STABLE | CALM | CAUTIOUS | MONITOR |
| HIGH | EARLY_CRACK | WATCH | DEFENSIVE | DE-RISK |
| EXTREME | BREAKING | CRITICAL | CRISIS | EXIT |

**风险预算公式**：
$$RiskBudget = \text{clip}(1.1 - 0.007 \times FuelScore, 0.35, 1.15)$$

---

# 第六章：附录

## 6.1 数据处理与因子验证

### 6.1.1 数据来源与发布滞后

| 因子 | 数据源 | 发布滞后 | 数据频率 | 历史覆盖 |
|-----|--------|---------|---------|---------|
| V1 | FRED: Z.1 Financial Accounts | 5个月 | 季度 | 1945-至今 |
| V4 | FRED: BEA NIPA | 6个月 | 季度 | 1947-至今 |
| V5 | FRED: TDSP | 3个月 | 季度 | 1980-至今 |
| V7 | Robert Shiller | 0个月 | 月度 | 1880-至今 |
| V8 | FRED: Flow of Funds | 2个月 | 季度 | 1945-至今 |
| V9 | FRED: SLOOS | 1个月 | 季度 | 1990-至今 |

### 6.1.2 因子验证框架

**IC (Information Coefficient)**：因子值与未来12个月股市收益的Spearman秩相关系数

**AUC (ROC曲线面积)**：预测未来12个月最大回撤是否超过-20%的分类能力

**稳定性惩罚**：
$$s_i = \min\left(1, \frac{|IC_{高利率}| + |IC_{低利率}|}{2 \times |IC_{全样本}|}\right)$$

### 6.1.3 5-Gate 因子验证框架 (TrendScore)

| Gate | 指标 | 阈值 | 说明 |
|------|-----|-----|-----|
| 1 | AUC | > 0.55 | 二分类预测能力 |
| 2 | IC | \|IC\| > 0.05 | 与前向收益的相关性 |
| 3 | Lift | > 1.2x | 高分位数时危机发生率提升 |
| 4 | Lead | ≥ 1月 | 信号领先于危机的时间 |
| 5 | Precision | > 15% | CRITICAL档位的精确率 |

---

## 6.2 项目结构

```
indicator_test/
├── config.py              # 统一配置（权重、阈值、路径）
├── dashboard_app.py       # Streamlit Web仪表板
├── system_orchestrator.py # 三层整合
│
├── core/                  # 核心计算模块
│   ├── fuel_score.py      # FuelScore（IC/AUC双权重）
│   ├── crack_score.py     # CrackScore（ΔZ信号）
│   └── trend_score.py     # TrendScore包装器
│
├── data/                  # 数据加载层
│   └── loader.py          # 统一DataLoader，支持滞后
│
├── validation/            # 权重验证与优化
│   ├── ic_calculator.py   # IC（收益相关性）计算
│   ├── auc_calculator.py  # AUC（MDD预测）计算
│   ├── weight_optimizer.py # 权重优化与报告
│   └── transform_comparator.py # Transform对比测试
│
├── utils/                 # 工具函数
│   └── transforms.py      # 分位数、Z-score转换
│
├── trend/                 # 趋势层实现
│   └── trend_score/       # TrendScore模块
│
└── structure/             # 结构层数据
    └── data/              # 因子CSV文件
        ├── raw/           # 原始数据
        └── lagged/        # 发布滞后调整后的数据
```

---

## 6.3 快速使用示例

```python
# 1. 当前系统状态
from system_orchestrator import SystemOrchestrator
orch = SystemOrchestrator()
print(orch.compute_portfolio_action())

# 2. 单层分析
from core import FuelScore, CrackScore, TrendScore

fuel = FuelScore(weight_scheme='ic')
print(f"FuelScore: {fuel.compute()['fuel_score']:.1f}")

crack = CrackScore()
print(f"CrackScore: {crack.compute()['crack_score']:.2f}σ")

trend = TrendScore()
print(f"TrendScore: {trend.compute()['trend_score']:.2f}")
```

---

## 参考文献

1. Minsky, H.P. (1986). *Stabilizing an Unstable Economy*. Yale University Press.
2. Adrian, T., & Shin, H.S. (2010). *Liquidity and Leverage*. Journal of Financial Intermediation.
3. Schularick, M., & Taylor, A.M. (2012). *Credit Booms Gone Bust*. American Economic Review.
4. Shiller, R.J. (2015). *Irrational Exuberance* (3rd ed.). Princeton University Press.

---

*报告生成日期：2026年1月4日*
*系统版本：v3.4*
*更新：Fuel层转换方式统一为Percentile，V8改用Credit Gap去趋势方法*
