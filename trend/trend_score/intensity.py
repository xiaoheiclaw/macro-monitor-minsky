"""
RiskIntensity 映射函数
=====================

将因子的百分位值映射到统一的 RiskIntensity (0~1) 刻度。

三种映射类型:
1. upper: 越高越危险 (T1 VTS, T5 TLT, T6 Funding)
2. lower: 越低越危险 (T8 Dealer)
3. band: 区间内危险，极端值不危险 (T3 SKEW, T10 GCF-IORB)

Z-score 映射:
- zscore_to_pctl: Z-score [-3, +3] → Percentile [0, 100]
"""

import numpy as np
from typing import Tuple, Union


def zscore_to_pctl(zscore: float, z_min: float = -3.0, z_max: float = 3.0) -> float:
    """
    将 Z-score 映射到 0-100 分位数刻度

    映射公式:
        pctl = (zscore - z_min) / (z_max - z_min) * 100, clip(0, 100)

    默认映射 [-3, +3] → [0, 100]:
        Z = -3 → pctl = 0
        Z = -2 → pctl = 16.7
        Z = -1 → pctl = 33.3
        Z =  0 → pctl = 50
        Z = +1 → pctl = 66.7
        Z = +2 → pctl = 83.3
        Z = +3 → pctl = 100

    Parameters:
    -----------
    zscore : float
        Z-score 值
    z_min : float
        Z-score 下界 (映射到 0)，默认 -3
    z_max : float
        Z-score 上界 (映射到 100)，默认 +3

    Returns:
    --------
    float : 映射后的百分位值 (0-100)

    Examples:
        >>> zscore_to_pctl(0)
        50.0
        >>> zscore_to_pctl(1.5)
        75.0
        >>> zscore_to_pctl(-3)
        0.0
        >>> zscore_to_pctl(5)  # 超出范围，截断到 100
        100.0
    """
    if np.isnan(zscore):
        return np.nan
    pctl = (zscore - z_min) / (z_max - z_min) * 100
    return float(np.clip(pctl, 0, 100))


def intensity_upper(pctl: float, lower: float) -> float:
    """
    单边危险：越高越危险

    适用于：
    - T1 VTS: danger_zone (50, 100)
    - T5 TLT: danger_zone (50, 100)
    - T6 Funding: danger_zone (50, 100)

    映射逻辑：
    - pctl < lower → 0 (安全区)
    - pctl = lower → 0 (边界)
    - pctl = 100 → 1 (最危险)

    Examples:
        >>> intensity_upper(50, 50)   # 边界
        0.0
        >>> intensity_upper(75, 50)   # 中间
        0.5
        >>> intensity_upper(100, 50)  # 最高
        1.0
        >>> intensity_upper(30, 50)   # 安全区
        0.0
    """
    if np.isnan(pctl):
        return np.nan
    return float(np.clip((pctl - lower) / (100 - lower), 0, 1))


def intensity_lower(pctl: float, upper: float) -> float:
    """
    单边危险：越低越危险

    适用于：
    - T8 Dealer: danger_zone (0, 50)

    映射逻辑：
    - pctl > upper → 0 (安全区)
    - pctl = upper → 0 (边界)
    - pctl = 0 → 1 (最危险)

    Examples:
        >>> intensity_lower(50, 50)   # 边界
        0.0
        >>> intensity_lower(25, 50)   # 中间
        0.5
        >>> intensity_lower(0, 50)    # 最低
        1.0
        >>> intensity_lower(80, 50)   # 安全区
        0.0
    """
    if np.isnan(pctl):
        return np.nan
    return float(np.clip((upper - pctl) / upper, 0, 1))


def intensity_band(pctl: float, low: float, high: float,
                   decay_rate: float = 10.0) -> float:
    """
    区间内危险：中间值危险，极端值不危险

    适用于：
    - T3 SKEW: danger_zone (0, 90) - 极端高位反而不危险
    - T10 GCF-IORB: danger_zone (0, 90)

    映射逻辑：
    - pctl < low → 0 (低于下界)
    - pctl 在 [low, high] 内 → 线性增加 (0 → 1)
    - pctl > high → 衰减 (避免极端值过度报警)

    衰减公式: max(0, 1 - (pctl - high) / decay_rate)

    Examples:
        >>> intensity_band(0, 0, 90)    # 下界
        0.0
        >>> intensity_band(45, 0, 90)   # 中间
        0.5
        >>> intensity_band(90, 0, 90)   # 上界
        1.0
        >>> intensity_band(95, 0, 90)   # 超出，衰减
        0.5
        >>> intensity_band(100, 0, 90)  # 极端高，衰减更多
        0.0
    """
    if np.isnan(pctl):
        return np.nan

    if pctl < low:
        return 0.0
    if pctl > high:
        # 超出上界，衰减（可调整 decay_rate）
        decayed = 1 - (pctl - high) / decay_rate
        return float(max(0, decayed))
    # 区间内：线性映射
    return float((pctl - low) / (high - low))


def compute_intensity(pctl: float,
                      zone: Tuple[float, float],
                      zone_type: str) -> float:
    """
    统一的 intensity 计算入口

    Parameters:
    -----------
    pctl : float
        因子的百分位值 (0-100)
    zone : tuple
        (lower, upper) 危险区间
    zone_type : str
        'upper', 'lower', 或 'band'

    Returns:
    --------
    float : RiskIntensity (0~1)

    Examples:
        >>> compute_intensity(75, (50, 100), 'upper')
        0.5
        >>> compute_intensity(25, (0, 50), 'lower')
        0.5
        >>> compute_intensity(45, (0, 90), 'band')
        0.5
    """
    low, high = zone

    if zone_type == 'upper':
        return intensity_upper(pctl, low)
    elif zone_type == 'lower':
        return intensity_lower(pctl, high)
    elif zone_type == 'band':
        return intensity_band(pctl, low, high)
    else:
        raise ValueError(f"Unknown zone_type: {zone_type}. "
                        f"Expected 'upper', 'lower', or 'band'.")


def compute_three_tier_intensity(pctl: float, zones: dict,
                                  direction: str = 'high_is_danger') -> dict:
    """
    计算三档 Zone 的强度

    根据当前百分位值判断处于哪个档位 (CRITICAL > ALERT > WATCH > SAFE)，
    并返回对应的 intensity 权重。

    Parameters:
    -----------
    pctl : float
        因子的百分位值 (0-100)
    zones : dict
        三档 Zone 配置，格式:
        {
            'WATCH': {'zone': (50, 80), 'weight': 0.4},
            'ALERT': {'zone': (65, 85), 'weight': 0.7},
            'CRITICAL': {'zone': (80, 100), 'weight': 1.0},
        }
    direction : str
        'high_is_danger' 或 'low_is_danger'

    Returns:
    --------
    dict: {
        'tier': 'CRITICAL' | 'ALERT' | 'WATCH' | 'SAFE',
        'intensity': 0.0 ~ 1.0,
        'in_zones': {'WATCH': True, 'ALERT': True, 'CRITICAL': False},
    }

    Examples:
        >>> zones = {
        ...     'WATCH': {'zone': (50, 80), 'weight': 0.4},
        ...     'ALERT': {'zone': (65, 85), 'weight': 0.7},
        ...     'CRITICAL': {'zone': (80, 100), 'weight': 1.0},
        ... }
        >>> compute_three_tier_intensity(85, zones)
        {'tier': 'CRITICAL', 'intensity': 1.0, 'in_zones': {'WATCH': True, 'ALERT': True, 'CRITICAL': True}}
        >>> compute_three_tier_intensity(70, zones)
        {'tier': 'ALERT', 'intensity': 0.7, 'in_zones': {'WATCH': True, 'ALERT': True, 'CRITICAL': False}}
        >>> compute_three_tier_intensity(55, zones)
        {'tier': 'WATCH', 'intensity': 0.4, 'in_zones': {'WATCH': True, 'ALERT': False, 'CRITICAL': False}}
        >>> compute_three_tier_intensity(30, zones)
        {'tier': 'SAFE', 'intensity': 0.0, 'in_zones': {'WATCH': False, 'ALERT': False, 'CRITICAL': False}}
    """
    if np.isnan(pctl):
        return {
            'tier': 'UNKNOWN',
            'intensity': np.nan,
            'in_zones': {},
        }

    # 对于 low_is_danger，翻转百分位
    if direction == 'low_is_danger':
        effective_pctl = 100 - pctl
    else:
        effective_pctl = pctl

    # 判断每个档位
    in_zones = {}
    for tier_name, tier_cfg in zones.items():
        if 'zone' not in tier_cfg:
            in_zones[tier_name] = False
            continue
        low, high = tier_cfg['zone']
        in_zones[tier_name] = low <= effective_pctl <= high

    # 优先级: CRITICAL > ALERT > WATCH
    if in_zones.get('CRITICAL', False):
        active_tier = 'CRITICAL'
        weight = zones['CRITICAL'].get('weight', 1.0)
    elif in_zones.get('ALERT', False):
        active_tier = 'ALERT'
        weight = zones['ALERT'].get('weight', 0.7)
    elif in_zones.get('WATCH', False):
        active_tier = 'WATCH'
        weight = zones['WATCH'].get('weight', 0.4)
    else:
        active_tier = 'SAFE'
        weight = 0.0

    return {
        'tier': active_tier,
        'intensity': weight,
        'in_zones': in_zones,
    }


def compute_continuous_intensity(pctl: float, zones: dict,
                                  direction: str = 'high_is_danger') -> dict:
    """
    计算连续的三档强度（在档位内进一步细分）

    与 compute_three_tier_intensity 不同，这个函数在每个档位内
    提供连续的强度值，而不是固定权重。

    Parameters:
    -----------
    pctl : float
        因子的百分位值 (0-100)
    zones : dict
        三档 Zone 配置
    direction : str
        'high_is_danger' 或 'low_is_danger'

    Returns:
    --------
    dict: {
        'tier': str,
        'intensity': float (0.0 ~ 1.0, 连续值),
        'tier_intensity': float (档位内的相对强度, 0~1),
        'in_zones': dict,
    }
    """
    if np.isnan(pctl):
        return {
            'tier': 'UNKNOWN',
            'intensity': np.nan,
            'tier_intensity': np.nan,
            'in_zones': {},
        }

    # 对于 low_is_danger，翻转百分位
    if direction == 'low_is_danger':
        effective_pctl = 100 - pctl
    else:
        effective_pctl = pctl

    # 判断每个档位
    in_zones = {}
    for tier_name, tier_cfg in zones.items():
        if 'zone' not in tier_cfg:
            in_zones[tier_name] = False
            continue
        low, high = tier_cfg['zone']
        in_zones[tier_name] = low <= effective_pctl <= high

    # 计算连续强度
    if in_zones.get('CRITICAL', False):
        active_tier = 'CRITICAL'
        low, high = zones['CRITICAL']['zone']
        base_weight = zones.get('ALERT', {}).get('weight', 0.7)
        max_weight = zones['CRITICAL'].get('weight', 1.0)
        # 在 CRITICAL 区间内线性插值
        tier_intensity = (effective_pctl - low) / (high - low) if high > low else 1.0
        intensity = base_weight + tier_intensity * (max_weight - base_weight)

    elif in_zones.get('ALERT', False):
        active_tier = 'ALERT'
        low, high = zones['ALERT']['zone']
        base_weight = zones.get('WATCH', {}).get('weight', 0.4)
        max_weight = zones['ALERT'].get('weight', 0.7)
        tier_intensity = (effective_pctl - low) / (high - low) if high > low else 1.0
        intensity = base_weight + tier_intensity * (max_weight - base_weight)

    elif in_zones.get('WATCH', False):
        active_tier = 'WATCH'
        low, high = zones['WATCH']['zone']
        base_weight = 0.0
        max_weight = zones['WATCH'].get('weight', 0.4)
        tier_intensity = (effective_pctl - low) / (high - low) if high > low else 1.0
        intensity = base_weight + tier_intensity * (max_weight - base_weight)

    else:
        active_tier = 'SAFE'
        tier_intensity = 0.0
        intensity = 0.0

    return {
        'tier': active_tier,
        'intensity': float(np.clip(intensity, 0, 1)),
        'tier_intensity': float(np.clip(tier_intensity, 0, 1)),
        'in_zones': in_zones,
    }


def compute_rolling_percentile(series, window: int = 60,
                                min_periods: int = 24) -> 'pd.Series':
    """
    计算滚动历史分位数

    用于将非百分位的 transform (如 yoy, zscore, ratio) 转换成百分位。

    Parameters:
    -----------
    series : pd.Series
        原始数据序列
    window : int
        滚动窗口大小（月数），默认 60 (5年)
    min_periods : int
        最小有效期数，默认 24 (2年)

    Returns:
    --------
    pd.Series : 滚动百分位 (0-100)
    """
    import pandas as pd

    def pctl_func(x):
        if len(x) <= 1:
            return 50
        # 当前值在历史中的排名
        current = x.iloc[-1]
        historical = x.iloc[:-1]
        return (historical < current).sum() / len(historical) * 100

    return series.rolling(window, min_periods=min_periods).apply(pctl_func)


# ==================== 测试用例 ====================

if __name__ == '__main__':
    print("Testing intensity functions...")

    # Test upper
    assert abs(intensity_upper(50, 50) - 0.0) < 0.001
    assert abs(intensity_upper(75, 50) - 0.5) < 0.001
    assert abs(intensity_upper(100, 50) - 1.0) < 0.001
    assert abs(intensity_upper(30, 50) - 0.0) < 0.001
    print("  intensity_upper: PASS")

    # Test lower
    assert abs(intensity_lower(50, 50) - 0.0) < 0.001
    assert abs(intensity_lower(25, 50) - 0.5) < 0.001
    assert abs(intensity_lower(0, 50) - 1.0) < 0.001
    assert abs(intensity_lower(80, 50) - 0.0) < 0.001
    print("  intensity_lower: PASS")

    # Test band
    assert abs(intensity_band(0, 0, 90) - 0.0) < 0.001
    assert abs(intensity_band(45, 0, 90) - 0.5) < 0.001
    assert abs(intensity_band(90, 0, 90) - 1.0) < 0.001
    assert intensity_band(100, 0, 90) < 1.0  # 衰减
    print("  intensity_band: PASS")

    # Test compute_intensity
    assert abs(compute_intensity(75, (50, 100), 'upper') - 0.5) < 0.001
    assert abs(compute_intensity(25, (0, 50), 'lower') - 0.5) < 0.001
    assert abs(compute_intensity(45, (0, 90), 'band') - 0.5) < 0.001
    print("  compute_intensity: PASS")

    print("\nAll tests passed!")
