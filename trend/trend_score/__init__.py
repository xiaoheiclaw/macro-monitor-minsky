"""
TrendScore 聚合系统
==================

将多个 Trend 层因子聚合成统一的风险评分，作为 Structure 层的风险放大器。

核心组件:
- config.py: 因子配置（best transform, danger zone, weight）
- intensity.py: RiskIntensity 映射函数
- trend_score.py: TrendScore 聚合类
"""

from .config import FACTOR_CONFIG
from .intensity import compute_intensity
from .trend_score import TrendScore

__all__ = ['FACTOR_CONFIG', 'compute_intensity', 'TrendScore']
