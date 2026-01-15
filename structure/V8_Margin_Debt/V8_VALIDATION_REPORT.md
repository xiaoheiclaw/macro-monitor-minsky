# V8 Margin Debt / Market Cap - Validation Report

Generated: 2025-12-30 21:34:20

## Factor Definition

**Series**: Margin Debt / Market Cap Ratio
- BOGZ1FL663067003Q: Security Brokers Receivables (Margin Debt proxy)
- BOGZ1FL893064105Q: Equity Market Value (Market Cap)

| 属性 | 值 |
|------|-----|
| Units | Ratio (%) |
| Frequency | Quarterly |
| Data Start | 1945 |
| Release Lag | 2 months |

**机制**:
- **Fuel Level** (Z_level): 杠杆绝对高度 → 市场脆弱度
- **Fuel Speed** (Δ8Q_Z): 杠杆堆积速度 → 泡沫形成速度

---

## Current Status

| 指标 | 值 | Signal |
|------|-----|--------|
| **V8 Ratio** | **0.5075%** | - |
| **Z-score (Level)** | **-1.29** | LOW |
| **Δ8Q Z-score (Speed)** | **0.27** | NEUTRAL |
| **Combined** | - | **NEUTRAL** |

---

## Transform Comparison

### IC (Information Coefficient) vs 12M Forward MDD

| Transform | Full IC | p-value | High Rate IC | Low Rate IC |
|-----------|---------|---------|--------------|-------------|
| Δ8Q Z-score (2Y Change) | -0.285 | 0.0000 | -0.372 | -0.185 |
| Δ4Q Z-score (YoY Change) | -0.236 | 0.0000 | -0.381 | -0.158 |
| YoY % Change | -0.325 | 0.0000 | -0.444 | -0.139 |
| Z-score (Level) | -0.427 | 0.0000 | -0.535 | -0.173 |
| Percentile (10Y) | -0.397 | 0.0000 | -0.486 | -0.187 |

### Drawdown Prediction (AUC)

| Transform | MDD<-10% | MDD<-15% | MDD<-20% |
|-----------|----------|----------|----------|
| Δ8Q Z-score (2Y Change) | 0.614 | 0.623 | 0.741 |
| Δ4Q Z-score (YoY Change) | 0.566 | 0.605 | 0.543 |
| YoY % Change | 0.596 | 0.661 | 0.605 |
| Z-score (Level) | 0.561 | 0.613 | 0.716 |
| Percentile (10Y) | 0.564 | 0.623 | 0.697 |

### Quintile Monotonicity

| Transform | Spearman | Q5-Q1 Spread | Monotonicity |
|-----------|----------|--------------|---------------|
| Δ8Q Z-score (2Y Change) | -0.900 | -14.36% | 0.90 |
| Δ4Q Z-score (YoY Change) | -0.400 | -14.13% | 0.40 |
| YoY % Change | -0.800 | -14.66% | 0.80 |
| Z-score (Level) | -1.000 | -18.65% | 1.00 |
| Percentile (10Y) | -0.900 | -15.41% | 0.90 |

---

## Best Transform: Δ8Q Z-score (2Y Change)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC (15%) | 0.623 | > 0.65 | FAIL |
| AUC (20%) | 0.741 | > 0.65 | **PASS** |
| IC (Full) | -0.285 | p < 0.05 | **PASS** |
| Q5-Q1 Spread | -14.36% | > 10% | **PASS** |
| Monotonicity | 0.90 | > 0.7 | **PASS** |

---

## Signal Logic (双维度系统)

### 维度1: Fuel Speed (Δ8Q Z-score) - 杠杆堆积速度

```python
def get_v8_speed_signal(delta_8q_zscore):
    """
    V8 Speed Signal - 杠杆变化速度
    4档信号，避免长期YELLOW失去分辨率
    """
    if delta_8q_zscore > 1.5:
        return "LEVERAGE_SURGE"   # 杠杆急升（危险）
    elif delta_8q_zscore > 0.5:
        return "BUILDUP"          # 杠杆堆积中
    elif delta_8q_zscore > -0.5:
        return "NEUTRAL"          # 中性
    else:
        return "DELEVERAGING"     # 去杠杆 / 风险释放
```

| Δ8Q Z-score | Speed Signal | 含义 |
|-------------|--------------|------|
| Z > 1.5 | **LEVERAGE_SURGE** | 杠杆急升（危险）|
| 0.5 < Z ≤ 1.5 | BUILDUP | 杠杆堆积中 |
| -0.5 ≤ Z ≤ 0.5 | NEUTRAL | 中性 |
| Z < -0.5 | DELEVERAGING | 去杠杆 / 风险释放 |

### 维度2: Fuel Level (Z-score Level) - 杠杆绝对高度

```python
def get_v8_level_signal(zscore_level):
    """
    V8 Level Signal - 杠杆绝对水平
    高位本身就危险，即使不再上升
    """
    if zscore_level > 1.0:
        return "HIGH_LEVERAGE"    # 高杠杆（脆弱）
    elif zscore_level > 0:
        return "ELEVATED"         # 偏高
    elif zscore_level > -1.0:
        return "NORMAL"           # 正常
    else:
        return "LOW"              # 低杠杆（安全）
```

| Level Z-score | Level Signal | 含义 |
|---------------|--------------|------|
| Z > 1.0 | **HIGH_LEVERAGE** | 高杠杆（市场脆弱）|
| 0 < Z ≤ 1.0 | ELEVATED | 偏高 |
| -1.0 ≤ Z ≤ 0 | NORMAL | 正常 |
| Z < -1.0 | LOW | 低杠杆（安全）|

### 双维度组合信号

```python
def get_v8_combined_signal(zscore_level, delta_8q_zscore):
    """
    V8 Combined Signal - Level × Speed 组合

    关键洞察：高位去杠杆 ≠ 安全
    高位去杠杆意味着强平链条可能已启动（Amplifier on）
    """
    level_signal = get_v8_level_signal(zscore_level)
    speed_signal = get_v8_speed_signal(delta_8q_zscore)

    # 最高风险：高位 + 急升
    if level_signal == "HIGH_LEVERAGE" and speed_signal == "LEVERAGE_SURGE":
        return "CRITICAL"  # 立即行动

    # 高风险：高位 + 剧烈去杠杆（强平链条启动）
    if level_signal == "HIGH_LEVERAGE" and speed_signal == "DELEVERAGING":
        if delta_8q_zscore < -1.5:
            return "RED"    # 剧烈去杠杆 = 强平潮
        else:
            return "ORANGE" # 温和去杠杆 = 风险释放中但仍脆弱

    # 高风险：高位 + 任何非去杠杆
    if level_signal == "HIGH_LEVERAGE":
        return "RED"  # 高位脆弱，随时可能崩

    # 中高风险：急升（无论level）
    if speed_signal == "LEVERAGE_SURGE":
        return "ORANGE"  # 杠杆急升中

    # 中风险：偏高 + 堆积
    if level_signal == "ELEVATED" and speed_signal == "BUILDUP":
        return "YELLOW"  # 需密切观察

    # 安全：低位去杠杆
    if speed_signal == "DELEVERAGING" and level_signal in ["LOW", "NORMAL"]:
        return "GREEN"  # 风险释放中

    return "NEUTRAL"
```

### 组合信号矩阵

|  | DELEVERAGING (剧烈<-1.5) | DELEVERAGING (温和) | NEUTRAL | BUILDUP | LEVERAGE_SURGE |
|--|--------------------------|---------------------|---------|---------|----------------|
| **HIGH_LEVERAGE** | **RED** (强平潮) | ORANGE (仍脆弱) | RED | RED | **CRITICAL** |
| **ELEVATED** | YELLOW | GREEN | NEUTRAL | YELLOW | ORANGE |
| **NORMAL** | GREEN | GREEN | NEUTRAL | NEUTRAL | ORANGE |
| **LOW** | GREEN | GREEN | GREEN | NEUTRAL | YELLOW |

### 高位去杠杆的危险性

**为什么 HIGH_LEVERAGE + DELEVERAGING ≠ GREEN？**

1. **强平链条已启动**: 去杠杆意味着有人在被迫卖出
2. **Amplifier on**: 高位去杠杆会放大下跌
3. **历史案例**:
   - 2008年9-10月：高杠杆 + 剧烈去杠杆 → 最惨烈崩盘
   - 2000年3-4月：高杠杆 + 温和去杠杆 → 开始崩盘

**判断逻辑**:
- 剧烈去杠杆 (Δ8Q Z < -1.5): RED - 强平潮正在发生
- 温和去杠杆 (-1.5 < Δ8Q Z < -0.5): ORANGE - 风险在释放但市场仍脆弱

### 核心机制

**为什么需要两个维度？**

1. **Speed (Δ8Q)**: 捕捉"泡沫正在形成"
   - 杠杆急升 = 投机情绪高涨
   - AUC(20%) = 0.741

2. **Level (Z)**: 捕捉"高位脆弱"
   - 高位即使不再上升也危险
   - IC = -0.427（更强！）
   - 高位横盘 + 任何Trigger = 崩盘

**关键洞察**：
- 2000年：Level高位 + 略微去杠杆 → 仍然崩盘
- 2008年：Level高位 + Speed急升 → 最惨烈崩盘
- 2020年：Speed急升 from 低位 → 快速调整但不致命

---

## Combination with Other Factors

```python
# ==========================================
# CRITICAL: 多因子共振（立即行动）
# ==========================================

# V8 CRITICAL + V4 RED: 系统性危机
if v8_combined == "CRITICAL" and v4_signal == "RED":
    # 杠杆急升 + 盈利恶化 = 2008式危机
    action = "立即清仓或重度对冲"

# V8 RED + V9 TIGHTENING_SHOCK: 强制平仓潮
if v8_combined == "RED" and v9_signal == "CREDIT_TIGHTENING_SHOCK":
    # 高杠杆 + 银行收紧 = Margin Call级联
    action = "立即减仓"

# ==========================================
# HIGH ALERT: 需密切观察
# ==========================================

# V8 HIGH_LEVERAGE 单独（无论速度）
if v8_level == "HIGH_LEVERAGE":
    # 高位脆弱，等待触发因素
    alert = "市场脆弱，关注任何负面触发"
    prepare = "建立对冲仓位"

# V8 LEVERAGE_SURGE 单独
if v8_speed == "LEVERAGE_SURGE":
    # 杠杆快速堆积
    alert = "投机情绪过热"
    action = "减少杠杆敞口"
```

---

## Data Sources

| Series | Description | Source |
|--------|-------------|--------|
| BOGZ1FL663067003Q | Security Brokers Receivables | FRED/Flow of Funds |
| BOGZ1FL893064105Q | Equity Market Value | FRED/Flow of Funds |

---

*Version: 1.0*
*Validated: 2025-12-30*
*Framework: V1 Complete Validation*
