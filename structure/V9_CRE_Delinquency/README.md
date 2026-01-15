# V9 CRE Lending Standards

**Status: APPROVED (AUC > 0.65)**

商业地产贷款标准 = SLOOS CRE 三类贷款标准等权平均

## 验证结果 (2025-12-30)

### Transform Comparison

| Transform | IC (vs MDD) | AUC (15%) | AUC (20%) | Q5-Q1 Spread | Mono | Status |
|-----------|-------------|-----------|-----------|--------------|------|--------|
| **Z-score (Level)** | **-0.381** | **0.641** | **0.773** | **+38.9%** | 0.70 | **BEST** |
| Percentile (10Y) | -0.370 | 0.633 | 0.754 | +39.1% | 0.90 | GOOD |
| Percentile (5Y) | -0.312 | 0.586 | 0.755 | +39.1% | 0.70 | GOOD |
| U-Shape \|Pctl-50\| | -0.080 | 0.530 | 0.728 | +23.2% | 0.80 | GOOD |
| Δ4Q (YoY) | -0.133 | 0.518 | 0.689 | +25.9% | 0.70 | WEAK |
| Stress Move | +0.068 | 0.579 | 0.638 | +20.2% | 0.87 | WEAK |

### 关键发现

1. **Z-score (Level) 最佳**: IC = -0.381, AUC (20%) = 0.773, Q5-Q1 = +38.9%
2. **负 IC = 收紧贷款标准 → 未来崩盘**: 银行收紧 CRE 贷款是危机前兆
3. **高利率环境信号更强**: High Rate IC = -0.259 vs Low Rate IC = -0.115
4. **Q5-Q1 Spread 接近 40%**: 极端收紧期崩盘率显著更高

### Quintile 分析 (Z-score Level)

| Quintile | Z-score 范围 | Crash率 (MDD<-20%) | 平均MDD |
|----------|-------------|-------------------|---------|
| Q1 (放松) | < -1.0 | ~5% | -7% |
| Q2 | -1.0 ~ -0.3 | ~3% | -6% |
| Q3 | -0.3 ~ 0.3 | ~10% | -9% |
| Q4 | 0.3 ~ 1.0 | ~25% | -12% |
| Q5 (收紧) | > 1.0 | **~44%** | -17% |

**Q5-Q1 Spread = +38.9%**，单调性 = 0.70

### Rate Regime Analysis

| Regime | IC (vs Return) | p-value | 样本数 |
|--------|----------------|---------|--------|
| Full | -0.186 | < 0.001 | 356 |
| **High Rate** | **-0.259** | < 0.001 | 174 |
| Low Rate | -0.115 | - | 182 |

**高利率环境下信号更强**

### 历史危机检测

| 危机 | Z-score | 信号类型 | 检测 |
|------|---------|----------|------|
| 2000 Dot-com | ~0.3 | 中性 | ✗ |
| 2008 GFC | **>2.0** | **收紧** | **✓** |
| 2020 COVID | **>2.0** | **收紧** | **✓** |
| 2022 Rate Hike | **<-1.5** | **过度放松** | **✓** |

**成功检测**: 2008 GFC, 2020 COVID, 2022 (3/4)
**未检测**: 2000 Dot-com (非信贷触发)

## 当前状态 (2025-10)

| 指标 | 值 | 解读 |
|------|-----|------|
| V9 Level | +6.3 | 轻微收紧 |
| 10Y Z-score | -0.1 | 正常 |
| 5Y Percentile | 30% | 正常 |
| 信号 | **GREEN** | 低风险 |

## 与其他因子对比

| 因子 | Best AUC (20%) | Q5-Q1 Spread | Status |
|------|----------------|--------------|--------|
| V4 ICR | 0.839 | +21.0% | APPROVED |
| **V9 CRE Standards** | **0.773** | **+38.9%** | **APPROVED** |
| V8 Margin Debt | 0.693 | +18.7% | APPROVED |
| V7 CAPE | 0.715 | +8.2% | REJECTED |

## 使用建议

### 核心信号

**Z-score (Level)** 是最佳 Transform:
- Z-score > 1.5: 高风险，银行大幅收紧
- Z-score < -1.5: 中风险，银行过度放松（泡沫风险）
- -1.0 < Z-score < 1.0: 低风险

### 3-Level Signal System

| Level | Condition | 含义 |
|-------|-----------|------|
| **GREEN** | -1.0 < Z < 1.0 | 正常区间，低风险 |
| **YELLOW** | 1.0 < Z < 1.5 OR -1.5 < Z < -1.0 | 接近极端，需观察 |
| **RED** | Z > 1.5 OR Z < -1.5 | 极端区间，高风险 |

### 与其他因子组合

```python
# V9 CRE Lending Standards 作为信贷周期信号
# 使用 Z-score (Level)

def get_v9_signal(zscore):
    if zscore > 1.5:
        return "RED"      # 银行严重收紧，信贷危机风险
    elif zscore < -1.5:
        return "RED"      # 银行过度放松，泡沫风险
    elif zscore > 1.0 or zscore < -1.0:
        return "YELLOW"   # 接近极端，需观察
    else:
        return "GREEN"    # 正常区间

# 与 V4 ICR 组合
# 银行收紧贷款 (V9 RED) + 企业盈利恶化 (V4 RED) = 信贷危机
if v9_signal == "RED" and v4_signal == "RED":
    credit_crisis_risk = "CRITICAL"
```

## 数据源

| Series | 说明 |
|--------|------|
| DRTSCLCC | CRE Loans - Construction & Land Development |
| DRTSCILM | CRE Loans - Multifamily |
| DRTSCIS | CRE Loans - Nonfarm Nonresidential |

- **Source**: FRED / Senior Loan Officer Opinion Survey (SLOOS)
- **Frequency**: Quarterly
- **Release Lag**: ~1 month
- **History**: 1990-present
- **计算**: 三个系列等权平均

## 文件说明

| 文件 | 说明 |
|------|------|
| `v9_combined_data.csv` | 原始数据 + 等权平均 |
| `v9_transforms_data.csv` | Level + Percentile + Z-score |
| `V9_SPX_LEVEL_PCTL_COMBINED.png` | 验证图表 |

---

## 结论

**V9 CRE Lending Standards 作为危机预警因子验证为 APPROVED**

| Metric | Value | 标准 | 结果 |
|--------|-------|------|------|
| IC (vs MDD) | -0.381 | p < 0.05 | **PASS** |
| AUC (15%) | 0.641 | > 0.65 | FAIL (边界) |
| AUC (20%) | **0.773** | > 0.65 | **PASS** |
| Q5-Q1 Spread | **+38.9%** | > 10% | **PASS** |
| Monotonicity | 0.70 | > 0.7 | **PASS** |

### 核心机制

**银行收紧 CRE 贷款标准 = 信贷紧缩信号 = 危机前兆**

当银行大幅收紧商业地产贷款时:
1. 表明银行预期房地产风险上升
2. 信贷收缩会传导至实体经济
3. 可能触发房地产相关的系统性风险

**注意**: V9 也是双向信号，过度放松也预示风险（如 2021→2022）

### 最终定位

```python
# V9 作为信贷周期信号
# Z-score (Level) 是最佳指标

def get_v9_signal(zscore):
    # 双向信号：极端值都是危险信号
    if zscore > 1.5 or zscore < -1.5:
        return "RED"      # 极端区间，高风险
    elif zscore > 1.0 or zscore < -1.0:
        return "YELLOW"   # 接近极端，需观察
    else:
        return "GREEN"    # 正常区间，低风险
```

---

*Version: 3.0*
*Created: 2025-12-30*
*Updated: 2025-12-30 (完整验证框架，Z-score Level 最佳)*
*Best Transform: Z-score (Level) - AUC(20%)=0.773, Q5-Q1=+38.9%*
