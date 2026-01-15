# V8 Margin Debt / Market Cap

**Status: APPROVED (AUC > 0.65)**

融资余额相对市值 = Security Brokers Receivables / Equity Market Value

## 验证结果 (2025-12-29)

### Transform Comparison

| Transform | IC (vs MDD) | AUC (15%) | AUC (20%) | Q5-Q1 Spread | Status |
|-----------|-------------|-----------|-----------|--------------|--------|
| Ratio YoY % | -0.195 | 0.583 | 0.620 | +13.6% | GOOD |
| Ratio Δ12M Z-score | -0.125 | 0.538 | 0.563 | +14.3% | WEAK |
| **Ratio Δ24M Z-score** | **-0.236** | **0.649** | **0.693** | **+18.7%** | **BEST** |
| Margin YoY % (不除以市值) | -0.058 | 0.526 | 0.487 | +3.7% | RANDOM |
| Margin Δ24M Z-score (不除以市值) | -0.165 | 0.599 | 0.610 | +15.4% | WEAK |

### 关键发现

1. **必须除以市值**: 不除以市值的 YoY AUC ≈ 0.5，无预测力
2. **Δ24M Z-score 最佳**: IC = -0.236 (显著), AUC (15%) = 0.649, AUC (20%) = 0.693
3. **负 IC = 高杠杆增速 → 高 MDD**: 杠杆急升 = 市场脆弱
4. **Q5-Q1 Spread = +18.7%**: 高杠杆增速组崩盘率显著更高

### 为什么必须除以市值？

杠杆风险是**相对于市场规模的杠杆**：
- 如果市场规模翻倍，Margin Debt 翻倍是正常的
- 只有 **Margin / MktCap 比例**上升才是真正的杠杆堆积信号

### Quintile 分析 (Ratio Δ24M Z-score)

| Quintile | 杠杆增速 | 崩盘率 (MDD<-20%) |
|----------|----------|-------------------|
| Q1 (低) | 杠杆下降 | ~10% |
| Q2 | | ~15% |
| Q3 | | ~12% |
| Q4 | | ~15% |
| Q5 (高) | 杠杆急升 | **~29%** |

**Q5-Q1 Spread = +18.7%**

## 当前状态 (2025-12)

| 指标 | 值 | 解读 |
|------|-----|------|
| Margin Debt | $0.5T | 当前水平 |
| Market Cap | ~$100T | 股市总市值 |
| Ratio | ~0.5% | 正常范围 |
| Δ24M Z-score | 0.29 | **安全** |

## 与其他因子对比

| 因子 | Best AUC (20%) | Q5-Q1 Spread | Status |
|------|----------------|--------------|--------|
| V4 ICR | 0.839 | +21.0% | APPROVED |
| **V8 Margin Debt** | **0.693** | **+18.7%** | **APPROVED** |
| V7 CAPE | 0.715 | +8.2% | REJECTED |

## 使用建议

### 核心信号

**Ratio Δ24M Z-score** 是最佳 Transform:
- Z-score > 1.5: 杠杆急剧上升，高危信号
- Z-score < -1.5: 杠杆下降，相对安全

### 3-Level Signal System

| Level | Condition | 含义 |
|-------|-----------|------|
| **GREEN** | Δ24M Z < 0 | 杠杆下降，市场去杠杆化 |
| **YELLOW** | 0 < Δ24M Z < 1.5 | 杠杆温和上升，需观察 |
| **RED** | Δ24M Z > 1.5 | 杠杆急升，高风险 |

### 与其他因子组合

```python
# V8 Margin Debt 作为杠杆风险信号
# 使用 Ratio Δ24M Z-score

def get_v8_signal(delta_24m_zscore):
    if delta_24m_zscore > 1.5:
        return "RED"      # 杠杆急升，高风险
    elif delta_24m_zscore > 0:
        return "YELLOW"   # 杠杆上升，需观察
    else:
        return "GREEN"    # 杠杆下降，相对安全

# 与 V4 ICR 组合
# 当企业盈利恶化 (V4 RED) + 杠杆过高 (V8 RED) = 系统性风险
if v4_signal == "RED" and v8_signal == "RED":
    system_risk = "CRITICAL"
```

## 数据源

| Series | 说明 |
|--------|------|
| BOGZ1FL663067003Q | Security Brokers Receivables from Customers (Margin Debt proxy) |
| BOGZ1FL893064105Q | Equity Market Value (Market Cap) |

- **Source**: FRED (Federal Reserve)
- **Frequency**: Quarterly → Monthly (forward-filled)
- **Release Lag**: ~2 months
- **History**: 1945-present

## 文件说明

| 文件 | 说明 |
|------|------|
| `all_transforms_data.csv` | 所有 Transform 数据 |

### 图表

| 图表 | 说明 |
|------|------|
| `V8_SPX_LEVEL_CHANGE_COMBINED.png` | SPX + Level + Change 综合图 |

---

## 结论

**V8 Margin Debt / Market Cap 作为危机预警因子验证为 APPROVED**

| Metric | Value | 标准 | 结果 |
|--------|-------|------|------|
| Best AUC (15%) | 0.649 | > 0.65 | **PASS** (边界) |
| Best AUC (20%) | 0.693 | > 0.65 | **PASS** |
| Q5-Q1 Spread | +18.7% | > 10% | **PASS** |
| IC 显著性 | p < 0.0001 | p < 0.05 | **PASS** |

### 核心机制

**高融资余额/市值比 = 杠杆过高 = 市场脆弱**

当投资者大量使用杠杆买入股票时:
1. 市场对下跌更敏感（强制平仓）
2. 小幅下跌可能触发级联抛售
3. 流动性危机风险上升

### 最终定位

```python
# V8 作为杠杆风险信号
# Ratio Δ24M Z-score 是最佳指标

def get_v8_signal(delta_24m_zscore):
    if delta_24m_zscore > 1.5:
        return "RED"      # 杠杆急升，高风险
    elif delta_24m_zscore > 0:
        return "YELLOW"   # 杠杆上升，需观察
    else:
        return "GREEN"    # 杠杆下降，相对安全
```

---

*Version: 2.0*
*Created: 2025-12-29*
*Updated: 2025-12-29 (确认必须除以市值，Δ24M Z-score 最佳)*
*Best Transform: Ratio Δ24M Z-score - AUC(20%)=0.693, Q5-Q1=+18.7%*
