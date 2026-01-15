"""
Trend Factor Configuration (v2.0 - 三档 Zone)
==============================================

基于三档 Zone 优化模板的因子配置。

Zone 定义:
- WATCH: 20-30% coverage, Lift > 1.0x, 背景监控
- ALERT: 10-15% coverage, Lift > 1.2x, 风险预警
- CRITICAL: 3-7% coverage, Lift > 1.5x, Precision > 25%, 最高警报

Module 定义:
- A: Volatility Regime (A1_VTS, A2_SKEW, A3_MOVE)
- B: Funding / Liquidity (B1_Funding, B2_GCF_IORB)
- C: Credit Compensation (C1_HY_Spread, C2_IG_Spread)
- D: Flow Confirmation (D1_HYG_Flow, D2_LQD_Flow, D3_TLT_Flow)
"""

# ==============================================================================
# Module Definitions
# ==============================================================================

MODULES = {
    'A': {
        'name': 'Volatility Regime',
        'factors': ['A1_VTS', 'A2_SKEW', 'A3_MOVE'],
        'description': '波动率体系状态',
    },
    'B': {
        'name': 'Funding / Liquidity',
        'factors': ['B1_Funding', 'B2_GCF_IORB'],
        'description': '资金/流动性压力',
    },
    'C': {
        'name': 'Credit Compensation',
        'factors': ['C1_HY_Spread', 'C2_IG_Spread'],
        'description': '信用风险溢价',
    },
    'D': {
        'name': 'Flow Confirmation',
        'factors': ['D1_HYG_Flow', 'D2_LQD_Flow', 'D3_TLT_Flow'],
        'description': '资金流确认信号',
    },
}


# ==============================================================================
# Factor Configuration (三档 Zone 版本)
# ==============================================================================

FACTOR_CONFIG = {
    # ==================== Module A: Volatility Regime ====================
    # Zone设计原则：不重叠，基于历史分位数
    # WATCH: P60-P85 (~25% coverage)
    # ALERT: P85-P95 (~10% coverage)
    # CRITICAL: P95+ (~5% coverage)

    'A1_VTS': {
        'name': 'VIX Term Structure',
        'transform': 'vts_pctl_5y',
        'file': 'a1_vts.csv',
        'direction': 'high_is_danger',
        'module': 'A',
        'zones': {
            'WATCH': {'zone': (52, 82), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (82, 94), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (94, 100), 'weight': 1.0},  # P95+, ~5%
        },
        'enabled': True,
        'description': 'VTS = VIX/VIX3M - 1, 高分位=倒挂=短期恐慌',
    },

    'A2_SKEW': {
        'name': 'CBOE SKEW Index',
        'transform': 'skew_pctl_1y',
        'file': 'a2_skew.csv',
        'direction': 'high_is_danger',
        'module': 'A',
        'zones': {
            'WATCH': {'zone': (63, 90), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (90, 98), 'weight': 0.7},      # P85-P95, ~10%
            # CRITICAL: 极端高位(>98)反而不危险，不设置
        },
        'enabled': True,
        'description': '尾部风险定价, 极端高位(>98)反而不危险',
    },

    'A3_MOVE': {
        'name': 'MOVE Index (Delta Z-score)',
        'transform': 'move_delta_zscore_1y',  # zscore 会自动转为 pctl [0,100]
        'file': 'a3_move.csv',
        'direction': 'high_is_danger',
        'module': 'A',
        'zones': {
            'WATCH': {'zone': (54, 79), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (79, 100), 'weight': 0.7},     # P85-P95, ~10% (P95=100)
            # CRITICAL: 转换后 P95=100，无法单独区分
        },
        'enabled': True,
        'description': '债券波动率上升速度',
    },

    # ==================== Module B: Funding / Liquidity ====================

    'B1_Funding': {
        'name': 'Funding Spread',
        'transform': 'funding_pctl_1y_combined',
        'file': 'b1_funding.csv',
        'direction': 'high_is_danger',
        'module': 'B',
        'zones': {
            'WATCH': {'zone': (45, 81), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (81, 94), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (94, 100), 'weight': 1.0},  # P95+, ~5%
        },
        'enabled': True,
        'description': 'TED(pre-2018) + EFFR-SOFR(post-2018) 拼接',
    },

    'B2_GCF_IORB': {
        'name': 'GCF-IORB Spread',
        'transform': 'gcf_iorb_pctl_1y',
        'file': 'b2_gcf_iorb.csv',
        'direction': 'high_is_danger',
        'module': 'B',
        'zones': {
            'WATCH': {'zone': (51, 88), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (88, 95), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (95, 100), 'weight': 1.0},  # P95+, ~6%
        },
        'enabled': True,
        'description': 'GCF Repo Rate - EFFR, 高=Repo市场压力',
    },

    # ==================== Module C: Credit Compensation ====================

    'C1_HY_Spread': {
        'name': 'HY Credit Spread',
        'transform': 'hy_spread_pctl_1y',
        'file': 'c1_hy_spread.csv',
        'direction': 'high_is_danger',
        'module': 'C',
        'zones': {
            'WATCH': {'zone': (52, 91), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (91, 98), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (98, 100), 'weight': 1.0},  # P95+, ~5%
        },
        'enabled': True,
        'description': '高收益债OAS, 高=信用风险溢价上升',
    },

    'C2_IG_Spread': {
        'name': 'IG Credit Spread',
        'transform': 'ig_spread_pctl_1y',
        'file': 'c2_ig_spread.csv',
        'direction': 'high_is_danger',
        'module': 'C',
        'zones': {
            'WATCH': {'zone': (56, 92), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (92, 98), 'weight': 0.7},      # P85-P95, ~9%
            'CRITICAL': {'zone': (98, 100), 'weight': 1.0},  # P95+, ~6%
        },
        'enabled': True,
        'description': '投资级债OAS, 高=避险情绪蔓延',
    },

    # ==================== Module D: Flow Confirmation ====================

    'D1_HYG_Flow': {
        'name': 'HYG Flow',
        'transform': 'hyg_flow_delta_zscore_1y',  # zscore 会自动转为 pctl [0,100]
        'file': 'd1_hyg_flow.csv',
        'direction': 'high_is_danger',
        'module': 'D',
        'zones': {
            'WATCH': {'zone': (49, 80), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (80, 94), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (94, 100), 'weight': 1.0},  # P95+, ~5%
        },
        'enabled': False,  # REJECTED in 5-Gate validation
        'reason': 'REJECTED (2/5 gates)',
        'description': 'HYG资金流出=高收益债被抛售',
    },

    'D2_LQD_Flow': {
        'name': 'LQD Flow',
        'transform': 'lqd_flow_pctl_1y',
        'file': 'd2_lqd_flow.csv',
        'direction': 'high_is_danger',
        'module': 'D',
        'zones': {
            'WATCH': {'zone': (60, 96), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (96, 100), 'weight': 0.7},     # P85-P95, ~9%
            # CRITICAL: 数据集中在高位，P95=100
        },
        'enabled': True,
        'description': 'LQD资金流出=IG债被抛售',
    },

    'D3_TLT_Flow': {
        'name': 'TLT Flow',
        'transform': 'tlt_flow_zscore_3y',  # zscore 会自动转为 pctl [0,100]
        'file': 'd3_tlt_flow.csv',
        'direction': 'high_is_danger',
        'module': 'D',
        'zones': {
            'WATCH': {'zone': (57, 69), 'weight': 0.4},      # P60-P85, ~25%
            'ALERT': {'zone': (69, 77), 'weight': 0.7},      # P85-P95, ~10%
            'CRITICAL': {'zone': (77, 100), 'weight': 1.0},  # P95+, ~5%
        },
        'enabled': True,
        'description': 'TLT资金流入=Flight to Safety=高危',
    },
}


# ==============================================================================
# Zone Tier Specifications
# ==============================================================================

ZONE_TIER_SPECS = {
    # v2.1: 不重叠 Zone 设计，基于历史分位数
    # WATCH: P60-P85, ALERT: P85-P95, CRITICAL: P95+
    'WATCH': {
        'percentile_range': (60, 85),   # P60-P85
        'coverage_target': 0.25,        # 目标 ~25%
        'coverage_min': 0.20,
        'coverage_max': 0.30,
        'lift_min': 1.0,
        'weight': 0.4,
        'description': '背景监控，提醒关注',
    },
    'ALERT': {
        'percentile_range': (85, 95),   # P85-P95
        'coverage_target': 0.10,        # 目标 ~10%
        'coverage_min': 0.08,
        'coverage_max': 0.12,
        'lift_min': 1.2,
        'weight': 0.7,
        'description': '主动调整仓位，风险预警',
    },
    'CRITICAL': {
        'percentile_range': (95, 100),  # P95+
        'coverage_target': 0.05,        # 目标 ~5%
        'coverage_min': 0.03,
        'coverage_max': 0.07,
        'lift_min': 1.5,
        'precision_min': 0.25,
        'weight': 1.0,
        'description': '强制行动，最高警报',
    },
}


# ==============================================================================
# Quantile-based Thresholds (v3.0 温度校准)
# ==============================================================================

# 分位数阈值配置 - 用历史分位数定义状态，确保状态分布符合预期
QUANTILE_THRESHOLDS = {
    'CRITICAL': 0.95,  # heat_score > 95th percentile → ~5%
    'ALERT': 0.80,     # heat_score > 80th percentile → ~10-15% (从0.85调整)
    'WATCH': 0.60,     # heat_score > 60th percentile → ~25%
}

# 目标状态分布
TARGET_STATE_DISTRIBUTION = {
    'CALM': (0.45, 0.60),      # 45-60%
    'WATCH': (0.20, 0.30),     # 20-30%
    'ALERT': (0.10, 0.15),     # 10-15%
    'CRITICAL': (0.03, 0.07),  # 3-7%
}

# ==============================================================================
# State Thresholds (模块级和整体级) - 默认值，会被校准覆盖
# ==============================================================================

MODULE_STATE_THRESHOLDS = {
    'CRITICAL': 0.7,    # heat_score >= 0.7
    'ALERT': 0.5,       # heat_score >= 0.5
    'WATCH': 0.3,       # heat_score >= 0.3
    'CALM': 0.0,        # heat_score < 0.3
}

TREND_STATE_THRESHOLDS = {
    'CRITICAL': 0.7,    # >= 0.70 (aligned with METHODOLOGY_REPORT)
    'ALERT': 0.5,
    'WATCH': 0.3,
    'CALM': 0.0,
}


# ==============================================================================
# Aggregation Parameters (v3.0 修正)
# ==============================================================================

AGGREGATION_PARAMS = {
    # 模块内聚合: heat_score = max_weight * max + avg_weight * avg
    # v3.0: 降低 max 权重，提高 avg 权重，减少单因子对模块的影响
    'module_max_weight': 0.4,  # 从 0.6 降到 0.4
    'module_avg_weight': 0.6,  # 从 0.4 升到 0.6

    # 跨模块聚合
    # v3.0: 改为加权平均，不再用 max
    'use_max_module': False,   # 改为 False，使用加权平均
    'use_weighted_avg': True,  # 新增：使用加权平均

    # 非线性压缩指数 - 压缩中等热度，放大极端热度
    'nonlinear_exponent': 1.3,

    # Structure 层集成参数
    'amplifier_strength': 0.6,
}


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_enabled_factors() -> dict:
    """返回所有启用的因子配置"""
    return {k: v for k, v in FACTOR_CONFIG.items() if v.get('enabled', False)}


def get_module_factors(module_name: str) -> dict:
    """返回指定模块的因子配置"""
    if module_name not in MODULES:
        return {}
    factor_names = MODULES[module_name]['factors']
    return {k: v for k, v in FACTOR_CONFIG.items() if k in factor_names and v.get('enabled', False)}


def get_factor_zones(factor_name: str) -> dict:
    """返回因子的三档 Zone 配置"""
    if factor_name not in FACTOR_CONFIG:
        return {}
    return FACTOR_CONFIG[factor_name].get('zones', {})


def get_zone_weight(tier_name: str) -> float:
    """返回 Zone 档位对应的权重"""
    return ZONE_TIER_SPECS.get(tier_name, {}).get('weight', 0.0)


def determine_state_from_heat(heat_score: float, thresholds: dict = None) -> str:
    """根据 heat_score 确定状态"""
    if thresholds is None:
        thresholds = MODULE_STATE_THRESHOLDS

    if heat_score >= thresholds['CRITICAL']:
        return 'CRITICAL'
    elif heat_score >= thresholds['ALERT']:
        return 'ALERT'
    elif heat_score >= thresholds['WATCH']:
        return 'WATCH'
    else:
        return 'CALM'


# ==============================================================================
# Data File Mapping (新命名)
# ==============================================================================

DATA_FILE_MAPPING = {
    'A1_VTS': 'a1_vts.csv',
    'A2_SKEW': 'a2_skew.csv',
    'A3_MOVE': 'a3_move.csv',
    'B1_Funding': 'b1_funding.csv',
    'B2_GCF_IORB': 'b2_gcf_iorb.csv',
    'C1_HY_Spread': 'c1_hy_spread.csv',
    'C2_IG_Spread': 'c2_ig_spread.csv',
    'D1_HYG_Flow': 'd1_hyg_flow.csv',
    'D2_LQD_Flow': 'd2_lqd_flow.csv',
    'D3_TLT_Flow': 'd3_tlt_flow.csv',
}


# ==============================================================================
# v4.0 数据驱动权重 (Data-Driven Weights)
# ==============================================================================

# 因子验证指标 (从 TRANSFORM_VALIDATION_REPORT.md 2026-01-05 提取)
# AUC: 越高越好 (0.5=随机, 1.0=完美)
# IC: 绝对值越大越好 (负数=反向预测)
# Lead: 提前月数 (从 validation gates 提取)
# 数据源更新: VIX/VIX3M改用FRED, MOVE改用Yahoo ^MOVE, B2修复GCF series ID
FACTOR_VALIDATION_METRICS = {
    'A1_VTS':       {'auc': 0.579, 'ic': 0.161,  'lift': 1.31, 'lead': 6},   # pctl_5y, 4/5 gates
    'A2_SKEW':      {'auc': 0.426, 'ic': 0.101,  'lift': 0.96, 'lead': 0},   # pctl_1y, 2/5 gates
    'A3_MOVE':      {'auc': 0.829, 'ic': -0.227, 'lift': 2.85, 'lead': 1},   # pctl_1y, 5/5 gates (真实MOVE)
    'B1_Funding':   {'auc': 0.714, 'ic': -0.349, 'lift': 1.23, 'lead': 6},   # pctl_5y, 4/5 gates (FRED数据)
    'B2_GCF_IORB':  {'auc': 0.734, 'ic': -0.222, 'lift': 2.39, 'lead': 1},   # pctl_1y, 5/5 gates (修复series ID)
    'C1_HY_Spread': {'auc': 0.756, 'ic': -0.162, 'lift': 2.18, 'lead': 1},   # pctl_1y, 5/5 gates
    'C2_IG_Spread': {'auc': 0.708, 'ic': -0.205, 'lift': 2.01, 'lead': 1},   # pctl_1y, 5/5 gates
    'D1_HYG_Flow':  {'auc': 0.499, 'ic': -0.318, 'lift': 1.39, 'lead': 0},   # pctl_5y, 4/5 gates (6m AUC仅0.53，无效lead)
    'D2_LQD_Flow':  {'auc': 0.502, 'ic': -0.065, 'lift': 1.58, 'lead': 0},   # pctl_5y, 4/5 gates (all leads AUC~0.5，无效)
    'D3_TLT_Flow':  {'auc': 0.437, 'ic': 0.066,  'lift': 0.85, 'lead': 0},   # zscore_1y, 3/5 gates (6m AUC仅0.555，无效lead)
}

# Reliability 权重配置
# rel_i = auc_weight * clip((AUC-0.5)/0.5, 0, 1)
#       + ic_weight * clip(|IC|/0.5, 0, 1)
#       + lead_weight * clip(Lead/lead_max, 0, 1)
RELIABILITY_CONFIG = {
    'auc_weight': 0.4,          # AUC 占 40%
    'ic_weight': 0.2,           # IC 占 20%
    'lead_weight': 0.4,         # Lead 占 40% (领先性很重要)
    'lead_max': 6,              # 最大提前月数 (用于归一化)
    'min_reliability': 0.1,     # 因子最低权重下限 (避免完全忽略弱因子)
    'min_module_weight': 0.1,   # 模块最低权重下限 (避免完全忽略弱模块)
    'max_module_weight': 0.55,  # 模块最高权重上限 (避免单模块主导)
    'credit_module_boost': 1.2, # Credit 模块额外权重 (最硬的风险信号)
    'min_modules_required': 2,  # TrendScore 计算需要的最少模块数 (避免早期数据单模块饱和)
}


# ==============================================================================
# v4.1 数据质量分层配置 (Data Quality Tiering)
# ==============================================================================

DATA_QUALITY_CONFIG = {
    # 质量级别定义：根据有效模块数确定数据质量
    'quality_levels': {
        0: 'NONE',      # 无模块数据
        1: 'WEAK',      # 单模块，只输出局部信号
        2: 'OK',        # 2个模块，可输出标准 TrendScore
        3: 'STRONG',    # 3个模块，高置信度
        4: 'STRONG',    # 4个模块，完整版
    },

    # 各级别的信任度 (confidence)
    'level_confidence': {
        'NONE': 0.0,
        'WEAK': 0.25,
        'OK': 0.6,
        'STRONG': 1.0,
    },

    # TrendScore 计算的最小模块数
    'min_modules_for_trend': 2,

    # 局部信号模式 (coverage=1) 的配置
    'weak_mode': {
        'output_local_signal': True,    # 输出单模块的局部热度
        'suppress_trend_state': True,   # 不输出趋势级 WATCH/ALERT/CRITICAL
    },

    # 回测窗口定义 (产品化)
    # Trend 层天然是 1997+（最好 2004+）才可靠的体系
    'intended_backtest_windows': {
        'primary': '1998-01-01',     # 主回测窗口 (A+B+C，信用模块上线)
        'recommended': '2004-01-01', # 推荐回测窗口 (全模块完整版)
        'earliest': '1991-01-01',    # 最早可用 (A+B only，波动+资金面)
    },
}

# Confidence 惩罚系数 (预留接口，默认关闭)
# 启用后: trend_score_adjusted = trend_score_raw * confidence
COVERAGE_PENALTY = {
    'enabled': False,           # 是否启用 coverage penalty
    'formula': 'linear',        # 'linear': coverage/4, 'sqrt': sqrt(coverage/4)
}


# ==============================================================================
# Legacy Support (旧配置兼容)
# ==============================================================================

# 旧因子名到新因子名的映射
LEGACY_FACTOR_MAPPING = {
    'T1_VTS': 'A1_VTS',
    'T3_SKEW': 'A2_SKEW',
    'T5_TLT': 'D3_TLT_Flow',
    'T6_Funding': 'B1_Funding',
    'T8_Dealer': None,  # 已移除
    'T10_GCF_IORB': 'B2_GCF_IORB',
}
