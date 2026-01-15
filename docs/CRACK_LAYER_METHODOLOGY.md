# Crack Layer Methodology

## Overview

Crack 层捕捉各因子的**边际恶化**（Marginal Deterioration），用于检测系统性风险的早期裂缝。

**核心指标**: ΔZ (Delta Z-score) - 衡量因子在标准化空间中的变化速度

**聚合方式**: 线性聚合 (Linear Aggregation)

---

## 1. ΔZ 计算

### 公式

```
ΔZ = Z(t) - Z(t - window)
```

其中：
- `Z(t)` = 滚动 Z-score（10Y window = 120 months）
- `window` = 回看窗口（因子特定）

### 与传统 YoY 的区别

| 指标 | 公式 | 单位 | 特点 |
|------|------|------|------|
| **ΔZ** | Z(t) - Z(t-w) | 标准差 (σ) | 可跨因子比较，统一阈值 |
| YoY | (X(t) - X(t-12)) / X(t-12) | 百分比 | 因子间不可比 |

**ΔZ 的优势**: 所有因子使用相同的单位（σ），可以直接加权聚合。

---

## 2. 因子配置

| Factor | 名称 | Window | Direction |
|--------|------|--------|-----------|
| V4 | ICR (盈利覆盖) | 4Q (12M) | -1 (下降=坏) |
| V8 | Margin Debt (杠杆) | 8Q (24M) | +1 (上升=坏) |
| V2 | Uninsured Deposits | 4Q (12M) | +1 |
| V5 | TDSP (家庭负担) | 4Q (12M) | +1 |
| V1 | ST Debt (短债) | 4Q (12M) | +1 |
| V7 | CAPE (估值) | 12M | +1 |

### Direction 说明

- `direction = +1`: 原始值上升 = 危险（如杠杆上升）
- `direction = -1`: 原始值下降 = 危险（如 ICR 下降）

**Adjusted Signal**: `adjusted_signal = ΔZ × direction`

调整后，所有因子统一为 **正值 = 危险**。

---

## 3. 线性聚合公式

### CrackScore 计算

```
CrackScore = Σ(w_i × max(0, adjusted_signal_i))
```

**特点**:
- 直接用 ΔZ 原始值，不使用阈值
- 负值截断为 0（只看恶化，不看恢复）
- 输出单位: **σ (标准差)**

### 与阈值聚合的对比

| 方式 | 公式 | 输出单位 | 特点 |
|------|------|----------|------|
| **线性聚合** | `Σ(w × max(0, ΔZ))` | σ | 连续、灵敏 |
| 阈值聚合 | `Σ(w × intensity) × 100` | 0~100 | 离散、有门槛 |

---

## 4. 权重计算

### IC/AUC 验证结果

| Factor | IC (vs 12M Return) | AUC (MDD<-20%) | 权重 |
|--------|-------------------|----------------|------|
| V4 | -0.263 | 0.822 | **33.3%** |
| V8 | -0.323 | 0.683 | **24.6%** |
| V2 | -0.156 | 0.662 | **17.5%** |
| V5 | -0.185 | 0.638 | **16.6%** |
| V1 | +0.052 | 0.544 | 5.1% |
| V7 | +0.087 | 0.292 | 2.9% |

### 权重公式

```
Score_i = 0.7 × max(0, AUC_i - 0.5) + 0.3 × |IC_i|
Weight_i = Score_i / Σ(Score_j)
```

**设计思路**:
- AUC 权重 70%: 强调对极端回撤的预测能力
- IC 权重 30%: 考虑整体相关性
- AUC 减去 0.5: 只有超过随机猜测的部分才有价值

---

## 5. 状态机

| CrackScore | 状态 | 含义 | 行动建议 |
|------------|------|------|----------|
| < 0.3σ | STABLE | 无裂缝 | 正常监控 |
| 0.3~0.5σ | EARLY_CRACK | 轻微恶化 | 降低新增风险 |
| 0.5~1.0σ | WIDENING_CRACK | 裂缝扩大 | 降低风险敞口 |
| > 1.0σ | BREAKING | 即将崩塌 | 立即进入防御模式 |

---

## 6. 历史验证

### 危机前信号

| 事件 | CrackScore 峰值 | 主要贡献因子 |
|------|-----------------|--------------|
| Dot-com (2000) | ~2.0σ | V4 (ICR), V8 (Margin) |
| GFC (2008) | ~2.5σ | V4 (ICR), V5 (TDSP) |
| COVID (2020) | ~1.5σ | V4 (ICR) |

### 2019Q4 COVID 预警案例

- **V4 ICR ΔZ**: -1.37 ~ -1.47（方向调整后 +1.37 ~ +1.47）
- **CrackScore**: 从 ~0.1σ 升至 ~0.5σ
- **数据时效性**: 2019Q4 数据在 lagged 系统中显示为 2020-01-01（2 季度延迟）
- **结论**: 基于实际可获得的 lagged 数据，系统在 COVID 前成功发出预警

---

## 7. 与 Fuel 层的区别

| 层 | 指标 | 含义 | Transform |
|----|------|------|-----------|
| **Fuel** | Level (水位) | 风险存量高低 | Z-score / Percentile |
| **Crack** | Speed (速度) | 边际恶化程度 | ΔZ (变化率) |

**类比**:
- Fuel = 汽油存量（高存量 + 火星 = 大爆炸）
- Crack = 裂缝扩张速度（快速恶化 = 即将崩塌）

---

## 8. 代码位置

```
indicator_test/crack/
├── crack_score.py              # 主计算脚本 (线性聚合)
├── ic_auc_analysis.py          # IC/AUC 验证分析
├── crack_score_data.csv        # 输出数据
├── crack_score_timeseries.png  # 时序图
└── crack_factor_transforms.png # 各因子 ΔZ 图
```

---

## 9. 使用示例

```python
from crack_score import main

# 使用 lagged 数据（避免前视偏差）
crack_score, crack_results = main(use_lagged=True)

# 获取当前状态
current = crack_score.iloc[-1]
print(f"CrackScore: {current:.2f}σ")
```

---

*Version: 2.0 (Linear Aggregation)*
*Last Updated: 2025-01-03*
