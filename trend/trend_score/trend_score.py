"""
TrendScore 聚合类 (v4.0 - 数据驱动权重版)
==========================================

v4.0 升级 (基于 v3.0):
- 数据驱动权重：用 AUC/IC/Lead 计算因子 reliability 权重
- 模块层加权 mean：α 固定，但 mean 部分用 reliability 加权
- 趋势层模块权重：根据模块平均 AUC 分配模块权重

v3.0 保留功能：
- 分位数校准：用历史分位数定义状态阈值
- 聚合公式：0.4×max + 0.6×weighted_avg + 非线性压缩
- CRITICAL门槛收紧：需要Credit模块CRITICAL或多模块联动

目标状态分布：
- CALM: 45-60%
- WATCH: 20-30%
- ALERT: 10-15%
- CRITICAL: 3-7%

结构:
    Factor → Module → TrendScore

输出格式:
    {
        'module_states': {
            'A': {'heat_score': 0.72, 'state': 'ALERT', ...},
            ...
        },
        'trend_heat_score': 0.55,
        'trend_state': 'ALERT',
        'trigger_flags': {...},
        'calibrated': True,
    }
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .config import (
    FACTOR_CONFIG,
    MODULES,
    DATA_FILE_MAPPING,
    MODULE_STATE_THRESHOLDS,
    TREND_STATE_THRESHOLDS,
    AGGREGATION_PARAMS,
    QUANTILE_THRESHOLDS,
    FACTOR_VALIDATION_METRICS,
    RELIABILITY_CONFIG,
    DATA_QUALITY_CONFIG,
    COVERAGE_PENALTY,
    get_enabled_factors,
    get_module_factors,
    get_factor_zones,
    determine_state_from_heat,
)
from .intensity import (
    compute_three_tier_intensity,
    compute_continuous_intensity,
    compute_rolling_percentile,
    zscore_to_pctl,
)


class TrendScore:
    """
    TrendScore v4.0 - 数据驱动权重版

    v4.0 新增：数据驱动权重 (AUC/IC/Lead → reliability)
    v3.0 保留：分位数校准、改进的聚合公式、收紧的CRITICAL门槛
    """

    def __init__(self, data_dir: str = None, config: dict = None,
                 use_continuous_intensity: bool = False,
                 calibrated_thresholds: dict = None):
        """
        初始化 TrendScore

        Parameters:
        -----------
        data_dir : str
            数据目录路径，默认为 trend/data/
        config : dict
            因子配置，默认使用 FACTOR_CONFIG
        use_continuous_intensity : bool
            是否使用连续强度计算（默认使用阶梯式）
        calibrated_thresholds : dict
            校准后的阈值，如果为None则使用默认值
        """
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(current_dir), 'data')

        self.data_dir = data_dir
        self.config = config or FACTOR_CONFIG
        self.modules = MODULES
        self.use_continuous_intensity = use_continuous_intensity

        # 校准阈值 (v3.0)
        self.calibrated_thresholds = calibrated_thresholds
        self._is_calibrated = calibrated_thresholds is not None

        # 缓存
        self._data_cache = {}

        # v4.0: 数据驱动权重
        self.factor_reliability_weights = self._compute_factor_reliability_weights()
        self.module_reliability_weights = self._compute_module_reliability_weights()

    def _compute_factor_reliability_weights(self) -> Dict[str, float]:
        """
        基于验证指标计算因子可靠度权重 (v4.0)

        公式:
            rel_i = auc_weight * clip((AUC-0.5)/0.5, 0, 1)
                  + ic_weight * clip(|IC|/0.5, 0, 1)
                  + lead_weight * clip(Lead/lead_max, 0, 1)

        权重在模块内归一化，确保 Σ w_i = 1 (每个模块内)

        Returns:
        --------
        dict : {factor_name: normalized_weight}
        """
        cfg = RELIABILITY_CONFIG
        metrics = FACTOR_VALIDATION_METRICS

        # 第一步：计算每个因子的原始 reliability
        raw_reliabilities = {}
        for factor, m in metrics.items():
            # 只处理启用的因子
            if not self.config.get(factor, {}).get('enabled', False):
                continue

            # AUC 得分: (AUC - 0.5) / 0.5, clipped to [0, 1]
            auc_score = max(0, min(1, (m['auc'] - 0.5) / 0.5))

            # IC 得分: |IC| / 0.5, clipped to [0, 1]
            ic_score = min(1, abs(m['ic']) / 0.5)

            # Lead 得分: Lead / lead_max, clipped to [0, 1]
            lead_score = min(1, m['lead'] / cfg['lead_max'])

            # 加权求和
            rel = (cfg['auc_weight'] * auc_score +
                   cfg['ic_weight'] * ic_score +
                   cfg['lead_weight'] * lead_score)

            # 应用最低权重下限
            raw_reliabilities[factor] = max(cfg['min_reliability'], rel)

        # 第二步：在每个模块内归一化
        normalized_weights = {}
        for mod_name, mod_info in self.modules.items():
            mod_factors = [f for f in mod_info['factors'] if f in raw_reliabilities]
            if mod_factors:
                total = sum(raw_reliabilities[f] for f in mod_factors)
                for f in mod_factors:
                    normalized_weights[f] = raw_reliabilities[f] / total

        return normalized_weights

    def _compute_module_reliability_weights(self) -> Dict[str, float]:
        """
        基于模块平均 AUC 计算模块权重 (v4.0)

        公式:
            auc_score_m = clip((AUC_m - 0.5) / 0.5, 0, 1)
            W_m = max(auc_score_m, min_module_weight)  # 应用下限
            W_m = min(W_m, max_module_weight)  # 应用上限
            W_m = W_m / Σ W_m  # 归一化

        Credit 模块(C) 额外加权 (最硬的风险信号)

        Returns:
        --------
        dict : {module_name: normalized_weight}
        """
        metrics = FACTOR_VALIDATION_METRICS
        cfg = RELIABILITY_CONFIG
        min_weight = cfg.get('min_module_weight', 0.1)
        max_weight = cfg.get('max_module_weight', 0.55)

        # 计算每个模块的平均 AUC
        module_aucs = {}
        for mod_name, mod_info in self.modules.items():
            # 只考虑启用的因子
            enabled_factors = [
                f for f in mod_info['factors']
                if f in metrics and self.config.get(f, {}).get('enabled', False)
            ]
            if enabled_factors:
                module_aucs[mod_name] = np.mean([metrics[f]['auc'] for f in enabled_factors])
            else:
                module_aucs[mod_name] = 0.5  # 默认值 (随机)

        # 计算 AUC 得分
        auc_scores = {}
        for mod, auc in module_aucs.items():
            score = max(0, (auc - 0.5) / 0.5)
            # Credit 模块额外加权
            if mod == 'C':
                score *= cfg.get('credit_module_boost', 1.2)
            # 应用最低权重下限 (避免完全忽略弱模块)
            auc_scores[mod] = max(min_weight, score)

        # 归一化
        total = sum(auc_scores.values())
        if total > 0:
            normalized = {mod: score / total for mod, score in auc_scores.items()}
        else:
            # 如果所有模块 AUC 都 <= 0.5，使用均等权重
            normalized = {mod: 1.0 / len(self.modules) for mod in self.modules}

        # 应用上限并重新分配超出部分
        excess = 0
        below_cap = []
        for mod, weight in normalized.items():
            if weight > max_weight:
                excess += weight - max_weight
                normalized[mod] = max_weight
            else:
                below_cap.append(mod)

        # 将超出部分按比例分配给未达上限的模块
        if excess > 0 and below_cap:
            below_cap_total = sum(normalized[m] for m in below_cap)
            for mod in below_cap:
                normalized[mod] += excess * (normalized[mod] / below_cap_total)

        return normalized

    def _compute_data_quality(self, module_states: Dict[str, dict]) -> dict:
        """
        计算数据质量层信息 (v4.1)

        根据有效模块数量确定数据质量级别：
        - NONE (0): 无模块数据
        - WEAK (1): 单模块，只输出局部信号
        - OK (2): 2个模块，可输出标准 TrendScore
        - STRONG (3-4): 高置信度

        Returns:
        --------
        dict : {
            'coverage_modules': int,
            'quality_level': str,
            'modules_available': list,
            'modules_missing': list,
            'confidence': float,
            'is_trustworthy': bool,
        }
        """
        cfg = DATA_QUALITY_CONFIG

        # 统计有效模块（有数据且非 NO_DATA 状态）
        modules_available = [
            mod_name for mod_name, m in module_states.items()
            if m.get('state') != 'NO_DATA' and m.get('heat_score', -1) >= 0
        ]
        modules_missing = [
            mod_name for mod_name in self.modules.keys()
            if mod_name not in modules_available
        ]

        coverage = len(modules_available)
        quality_level = cfg['quality_levels'].get(coverage, 'NONE')
        confidence = cfg['level_confidence'].get(quality_level, 0.0)

        return {
            'coverage_modules': coverage,
            'quality_level': quality_level,
            'modules_available': modules_available,
            'modules_missing': modules_missing,
            'confidence': confidence,
            'is_trustworthy': coverage >= cfg['min_modules_for_trend'],
        }

    def _build_none_response(self, date: pd.Timestamp,
                              module_states: Dict[str, dict],
                              data_quality: dict) -> dict:
        """
        NONE 模式响应：完全无数据

        Returns:
        --------
        dict : TrendScore 输出（无有效数据）
        """
        return {
            'date': date,
            'module_states': module_states,
            'trend_heat_score': np.nan,
            'trend_state': 'INSUFFICIENT_DATA',
            'data_quality': data_quality,
            'local_signals': None,
            'trigger_flags': {
                'any_critical': False,
                'multi_module_alert': False,
                'dominant_module': None,
                'alert_modules': [],
                'valid_modules_count': 0,
            },
            'calibrated': self._is_calibrated,
        }

    def _build_weak_response(self, date: pd.Timestamp,
                              module_states: Dict[str, dict],
                              data_quality: dict) -> dict:
        """
        WEAK 模式响应：单模块输出局部信号

        只输出该模块的局部热度，不输出趋势级 TrendScore。
        局部信号在 local_signals 中，trend_heat_score 为 NaN。

        Returns:
        --------
        dict : TrendScore 输出（包含局部信号）
        """
        # 找到唯一有效模块
        active_mod = data_quality['modules_available'][0]
        active_state = module_states[active_mod]

        local_signals = {
            'active_module': active_mod,
            'local_heat': active_state['heat_score'],
            'local_state': active_state['state'],
        }

        return {
            'date': date,
            'module_states': module_states,
            'trend_heat_score': np.nan,  # WEAK 模式不输出趋势级热度
            'trend_state': 'INSUFFICIENT_DATA',  # 趋势状态仍为不足
            'data_quality': data_quality,
            'local_signals': local_signals,
            'trigger_flags': {
                'any_critical': False,
                'multi_module_alert': False,
                'dominant_module': active_mod,
                'alert_modules': [],
                'valid_modules_count': 1,
            },
            'calibrated': self._is_calibrated,
        }

    def _build_standard_response(self, date: pd.Timestamp,
                                   module_states: Dict[str, dict],
                                   data_quality: dict,
                                   valid_modules: List[Tuple[str, float]]) -> dict:
        """
        OK/STRONG 模式响应：正常计算 TrendScore

        Parameters:
        -----------
        valid_modules : list
            有效模块列表 [(mod_name, heat_score), ...]

        Returns:
        --------
        dict : 完整的 TrendScore 输出
        """
        use_weighted_avg = AGGREGATION_PARAMS.get('use_weighted_avg', True)
        nonlinear_exp = AGGREGATION_PARAMS.get('nonlinear_exponent', 1.3)

        if use_weighted_avg:
            # v4.0: 使用模块级 reliability 权重
            weighted_sum = 0
            weight_total = 0
            for mod_name, heat in valid_modules:
                w = self.module_reliability_weights.get(mod_name, 0.25)
                weighted_sum += heat * w
                weight_total += w

            raw_heat = weighted_sum / weight_total if weight_total > 0 else 0

            # 非线性压缩：压缩中等热度，放大极端热度
            trend_heat = raw_heat ** nonlinear_exp
        else:
            # 旧逻辑：使用最高模块分数
            trend_heat = max(heat for _, heat in valid_modules)

        # 可选：Coverage Penalty (预留接口，默认关闭)
        if COVERAGE_PENALTY.get('enabled', False):
            if COVERAGE_PENALTY.get('formula') == 'sqrt':
                trend_heat = trend_heat * np.sqrt(data_quality['confidence'])
            else:
                trend_heat = trend_heat * data_quality['confidence']

        # 找主导模块
        dominant_module = max(valid_modules, key=lambda x: x[1])

        # Trigger flags
        alert_modules = [
            k for k, m in module_states.items()
            if m['state'] in ('ALERT', 'CRITICAL')
        ]
        multi_module_alert = len(alert_modules) >= 2

        # v3.0: 收紧的 CRITICAL 门槛
        trend_state = self._determine_trend_state_v3(
            module_states, trend_heat, alert_modules
        )

        return {
            'date': date,
            'module_states': module_states,
            'trend_heat_score': trend_heat,
            'trend_state': trend_state,
            'data_quality': data_quality,
            'local_signals': None,  # 非 WEAK 模式无此字段
            'trigger_flags': {
                'any_critical': any(m['state'] == 'CRITICAL' for m in module_states.values()),
                'multi_module_alert': multi_module_alert,
                'dominant_module': dominant_module[0],
                'alert_modules': alert_modules,
                'valid_modules_count': len(valid_modules),
            },
            'calibrated': self._is_calibrated,
        }

    def calibrate(self, history: pd.DataFrame = None) -> dict:
        """
        基于历史数据校准阈值 (v3.0 核心功能)

        使用历史分位数定义状态阈值，确保状态分布符合预期。

        Parameters:
        -----------
        history : pd.DataFrame
            历史数据，如果为None则自动计算

        Returns:
        --------
        dict : 校准后的阈值 {'CRITICAL': 0.xx, 'ALERT': 0.xx, 'WATCH': 0.xx}
        """
        if history is None:
            history = self.compute_history(freq='D')

        if 'trend_heat_score' not in history.columns or len(history) == 0:
            print("Warning: No valid history data for calibration")
            return TREND_STATE_THRESHOLDS.copy()

        heat_scores = history['trend_heat_score'].dropna()

        if len(heat_scores) < 100:
            print(f"Warning: Only {len(heat_scores)} data points, calibration may be unreliable")

        self.calibrated_thresholds = {
            'CRITICAL': heat_scores.quantile(QUANTILE_THRESHOLDS['CRITICAL']),
            'ALERT': heat_scores.quantile(QUANTILE_THRESHOLDS['ALERT']),
            'WATCH': heat_scores.quantile(QUANTILE_THRESHOLDS['WATCH']),
        }
        self._is_calibrated = True

        return self.calibrated_thresholds

    def get_thresholds(self) -> dict:
        """获取当前使用的阈值"""
        if self._is_calibrated and self.calibrated_thresholds:
            return self.calibrated_thresholds
        return TREND_STATE_THRESHOLDS.copy()

    def load_factor_data(self, factor_name: str) -> pd.DataFrame:
        """加载单个因子的数据"""
        if factor_name in self._data_cache:
            return self._data_cache[factor_name]

        cfg = self.config.get(factor_name)
        if cfg is None:
            raise ValueError(f"Unknown factor: {factor_name}")

        filename = cfg.get('file') or DATA_FILE_MAPPING.get(factor_name)
        if filename is None:
            raise ValueError(f"No data file mapping for factor: {factor_name}")

        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Data file not found: {filepath}")

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        self._data_cache[factor_name] = df
        return df

    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """加载所有启用因子的数据"""
        data = {}
        for factor_name, cfg in self.config.items():
            if not cfg.get('enabled', False):
                continue
            try:
                data[factor_name] = self.load_factor_data(factor_name)
            except (FileNotFoundError, ValueError) as e:
                print(f"Warning: {e}")
        return data

    def get_factor_value(self, factor_name: str, df: pd.DataFrame,
                         date: pd.Timestamp) -> float:
        """
        获取因子在指定日期的值

        对于 zscore 列，自动应用 Z → Pctl 映射:
            pctl = (zscore + 3) / 6 * 100, clip(0, 100)

        这样所有因子值都统一到 0-100 范围，与 zones 配置兼容。
        """
        cfg = self.config[factor_name]
        col = cfg.get('transform')

        if col is None:
            return np.nan

        # 找到最接近的日期
        valid_dates = df.index[df.index <= date]
        if len(valid_dates) == 0:
            return np.nan

        closest_date = valid_dates[-1]

        if col not in df.columns:
            # 尝试找匹配的列
            possible_cols = [c for c in df.columns if col in c or col.replace('_', '') in c.replace('_', '')]
            if possible_cols:
                col = possible_cols[0]
            else:
                return np.nan

        value = df.loc[closest_date, col]

        # 如果是 zscore 列，自动映射到 0-100
        # 检测列名中包含 'zscore' (但不包含 'pctl')
        if 'zscore' in col.lower() and 'pctl' not in col.lower():
            value = zscore_to_pctl(value)

        return value

    def compute_factor_state(self, factor_name: str, pctl: float) -> dict:
        """
        计算单个因子的状态

        Returns:
        --------
        dict: {
            'tier': str,
            'intensity': float,
            'in_zones': dict,
            'pctl': float,
        }
        """
        cfg = self.config.get(factor_name)
        if cfg is None or not cfg.get('enabled', False):
            return {
                'tier': 'DISABLED',
                'intensity': 0.0,
                'in_zones': {},
                'pctl': pctl,
            }

        zones = cfg.get('zones', {})
        direction = cfg.get('direction', 'high_is_danger')

        if not zones:
            return {
                'tier': 'NO_ZONES',
                'intensity': 0.0,
                'in_zones': {},
                'pctl': pctl,
            }

        if self.use_continuous_intensity:
            result = compute_continuous_intensity(pctl, zones, direction)
        else:
            result = compute_three_tier_intensity(pctl, zones, direction)

        result['pctl'] = pctl
        return result

    def compute_module_state(self, module_name: str,
                              factor_states: Dict[str, dict]) -> dict:
        """
        计算单个模块的聚合状态 (v4.0 数据驱动权重版)

        v4.0 改进：
        - α (max/avg系数) 固定不变 (结构偏好)
        - mean 部分用 reliability 加权：Σ(w_i * intensity_i)
        - 公式: module_heat = α * max(intensity_i) + (1-α) * weighted_mean

        Parameters:
        -----------
        module_name : str
            模块名称 ('A', 'B', 'C', 'D')
        factor_states : dict
            {factor_name: {'tier': 'ALERT', 'intensity': 0.7, ...}}

        Returns:
        --------
        dict: {
            'heat_score': float (0~1),
            'state': str,
            'dominant_factor': str,
            'factors_in_alert': list,
            'factor_details': dict,
        }
        """
        if not factor_states:
            return {
                'heat_score': 0.0,
                'state': 'NO_DATA',
                'dominant_factor': None,
                'factors_in_alert': [],
                'factor_details': {},
            }

        # 提取有效的 intensity 和对应的 reliability 权重
        intensities = []
        weights = []
        for name, state in factor_states.items():
            if state.get('tier') not in ('DISABLED', 'NO_ZONES', 'UNKNOWN'):
                intensity = state.get('intensity', 0.0)
                # v4.0: 获取因子 reliability 权重，默认为 1.0
                w = self.factor_reliability_weights.get(name, 1.0)
                intensities.append((name, intensity))
                weights.append(w)

        if not intensities:
            return {
                'heat_score': 0.0,
                'state': 'NO_DATA',
                'dominant_factor': None,
                'factors_in_alert': [],
                'factor_details': factor_states,
            }

        # 模块聚合 (v4.0): α * max + (1-α) * weighted_mean
        # α 固定 (结构偏好：shock vs breadth)
        alpha = AGGREGATION_PARAMS.get('module_max_weight', 0.4)

        values = [v for _, v in intensities]
        max_intensity = max(values)

        # v4.0: weighted mean (让可靠因子在"广谱升温"中占更大比重)
        weights_arr = np.array(weights)
        if weights_arr.sum() > 0:
            weights_norm = weights_arr / weights_arr.sum()
            weighted_mean = np.dot(values, weights_norm)
        else:
            weighted_mean = np.mean(values)

        heat_score = alpha * max_intensity + (1 - alpha) * weighted_mean

        # 找主导因子
        dominant = max(intensities, key=lambda x: x[1])

        # 找处于 ALERT 或 CRITICAL 的因子
        factors_in_alert = [
            name for name, state in factor_states.items()
            if state.get('tier') in ('ALERT', 'CRITICAL')
        ]

        # 状态映射
        state = determine_state_from_heat(heat_score, MODULE_STATE_THRESHOLDS)

        return {
            'heat_score': heat_score,
            'state': state,
            'dominant_factor': dominant[0],
            'dominant_intensity': dominant[1],
            'factors_in_alert': factors_in_alert,
            'factor_details': factor_states,
        }

    def compute_trend_output(self, all_factor_states: Dict[str, dict],
                              date: pd.Timestamp = None) -> dict:
        """
        计算最终 TrendScore 输出 (v4.1 数据质量分层输出版)

        v4.1 新增：
        - 数据质量分层输出：NONE/WEAK/OK/STRONG
        - WEAK 模式：单模块时输出 local_signals，不输出 TrendScore
        - 新增 data_quality 字段

        v4.0 保留：
        - 跨模块聚合使用模块级 reliability 权重
        - 公式: raw_heat = Σ(W_m * module_heat_m), trend_heat = raw_heat^γ

        v3.0 保留：
        - 非线性压缩
        - CRITICAL 门槛收紧：需要 Credit模块CRITICAL 或 多模块联动

        Parameters:
        -----------
        all_factor_states : dict
            所有因子的状态 {factor_name: state_dict}
        date : pd.Timestamp
            日期（可选）

        Returns:
        --------
        dict: {
            'date': Timestamp,
            'module_states': {...},
            'trend_heat_score': float,
            'trend_state': str,
            'data_quality': {...},    # v4.1 新增
            'local_signals': {...},   # v4.1 新增 (WEAK 模式)
            'trigger_flags': {...},
            'calibrated': bool,
        }
        """
        # Step 1: 计算各模块状态
        module_states = {}
        for mod_name, mod_info in self.modules.items():
            factor_names = mod_info['factors']
            mod_factor_states = {
                k: v for k, v in all_factor_states.items()
                if k in factor_names
            }
            module_states[mod_name] = self.compute_module_state(mod_name, mod_factor_states)

        # Step 2: 计算数据质量 (v4.1 新增)
        data_quality = self._compute_data_quality(module_states)

        # Step 3: 根据质量级别决定输出
        if data_quality['quality_level'] == 'NONE':
            # 完全无数据
            return self._build_none_response(date, module_states, data_quality)

        elif data_quality['quality_level'] == 'WEAK':
            # 单模块模式 - 输出局部信号
            return self._build_weak_response(date, module_states, data_quality)

        else:
            # OK/STRONG - 正常计算 TrendScore
            # 先获取所有有效模块（state != NO_DATA），即使 heat_score = 0
            valid_modules = [
                (mod_name, m['heat_score'])
                for mod_name, m in module_states.items()
                if m['state'] != 'NO_DATA' and not np.isnan(m.get('heat_score', np.nan))
            ]
            # 如果所有模块 heat_score 都是 0，仍然是有效输出（CALM 状态）
            if not valid_modules:
                # 退回到所有可用模块，包括 heat_score=0 的情况
                valid_modules = [
                    (mod_name, max(0, m.get('heat_score', 0)))
                    for mod_name in data_quality['modules_available']
                    for m in [module_states.get(mod_name, {})]
                ]
            # 最后兜底
            if not valid_modules:
                return self._build_none_response(date, module_states, data_quality)
            return self._build_standard_response(date, module_states, data_quality, valid_modules)

    def _determine_trend_state_v3(self, module_states: dict,
                                   trend_heat: float,
                                   alert_modules: list) -> str:
        """
        v3.0 收紧的状态判定逻辑

        CRITICAL 门槛：
        1. Credit 模块(C) 达到 CRITICAL（最硬的风险信号）
        或
        2. 至少2个模块 >= ALERT 且 trend_heat > CRITICAL阈值

        其他状态使用分位数校准阈值。
        """
        thresholds = self.get_thresholds()

        # 条件1: Credit 模块 CRITICAL
        credit_critical = module_states.get('C', {}).get('state') == 'CRITICAL'

        # 条件2: 多模块联动 + 高热度
        n_alert_plus = len(alert_modules)
        multi_module_stress = (n_alert_plus >= 2 and
                               trend_heat > thresholds.get('CRITICAL', 0.8))

        # CRITICAL 判定
        if credit_critical or multi_module_stress:
            return 'CRITICAL'
        elif trend_heat >= thresholds.get('ALERT', 0.5):
            return 'ALERT'
        elif trend_heat >= thresholds.get('WATCH', 0.3):
            return 'WATCH'
        else:
            return 'CALM'

    def compute_for_date(self, date: pd.Timestamp,
                          data: Dict[str, pd.DataFrame] = None) -> dict:
        """
        计算指定日期的 TrendScore

        Parameters:
        -----------
        date : pd.Timestamp
            目标日期
        data : dict
            预加载的数据，如果为 None 则自动加载

        Returns:
        --------
        dict : TrendScore 结果
        """
        if data is None:
            data = self.load_all_data()

        # 计算每个因子的状态
        all_factor_states = {}

        for factor_name, cfg in self.config.items():
            if not cfg.get('enabled', False):
                continue
            if factor_name not in data:
                continue

            df = data[factor_name]
            pctl = self.get_factor_value(factor_name, df, date)
            all_factor_states[factor_name] = self.compute_factor_state(factor_name, pctl)

        return self.compute_trend_output(all_factor_states, date)

    def compute_latest(self) -> dict:
        """计算最新的 TrendScore

        v4.2: 改进策略 - 对每个因子使用其最新可用数据，而非共同最早日期
        """
        data = self.load_all_data()

        # 计算每个因子的状态（使用各自的最新日期）
        all_factor_states = {}
        latest_dates = []

        for factor_name, cfg in self.config.items():
            if not cfg.get('enabled', False):
                continue
            if factor_name not in data:
                continue

            df = data[factor_name]
            if len(df) == 0:
                continue

            # 使用该因子的最新日期
            factor_latest_date = df.index.max()
            latest_dates.append(factor_latest_date)

            pctl = self.get_factor_value(factor_name, df, factor_latest_date)
            all_factor_states[factor_name] = self.compute_factor_state(factor_name, pctl)

        if not latest_dates:
            return {
                'trend_heat_score': np.nan,
                'trend_state': 'NO_DATA',
                'module_states': {},
                'trigger_flags': {},
                'data_quality': {
                    'coverage_modules': 0,
                    'quality_level': 'NONE',
                },
            }

        # 使用所有因子中最新的日期作为报告日期
        report_date = max(latest_dates)
        return self.compute_trend_output(all_factor_states, report_date)

    def compute_history(self, start_date: str = None,
                         end_date: str = None,
                         freq: str = 'D') -> pd.DataFrame:
        """
        计算历史 TrendScore 时间序列

        Parameters:
        -----------
        start_date : str
            开始日期
        end_date : str
            结束日期
        freq : str
            采样频率 ('D' 日, 'W' 周, 'ME' 月末)

        Returns:
        --------
        pd.DataFrame : 包含历史 TrendScore
        """
        data = self.load_all_data()

        # 确定日期范围
        all_dates = set()
        for df in data.values():
            all_dates.update(df.index.tolist())

        all_dates = sorted(all_dates)

        if start_date:
            all_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]
        if end_date:
            all_dates = [d for d in all_dates if d <= pd.Timestamp(end_date)]

        # 采样
        if freq != 'D':
            date_series = pd.Series(all_dates)
            sampled = date_series.resample(freq).last().dropna()
            all_dates = sampled.values.tolist()

        # 计算
        results = []
        for date in all_dates:
            result = self.compute_for_date(date, data)
            row = {
                'date': date,
                'trend_heat_score': result['trend_heat_score'],
                'trend_state': result['trend_state'],
                'any_critical': result['trigger_flags']['any_critical'],
                'multi_module_alert': result['trigger_flags']['multi_module_alert'],
                'dominant_module': result['trigger_flags']['dominant_module'],
            }

            # v4.1: 添加数据质量字段
            if 'data_quality' in result and result['data_quality']:
                dq = result['data_quality']
                row['coverage_modules'] = dq.get('coverage_modules', 0)
                row['quality_level'] = dq.get('quality_level', 'NONE')
                row['confidence'] = dq.get('confidence', 0.0)
                row['is_trustworthy'] = dq.get('is_trustworthy', False)

            # v4.1: 添加局部信号字段 (WEAK 模式)
            if 'local_signals' in result and result['local_signals']:
                ls = result['local_signals']
                row['local_module'] = ls.get('active_module')
                row['local_heat'] = ls.get('local_heat')
                row['local_state'] = ls.get('local_state')

            # 添加各模块分数
            for mod_name, mod_state in result['module_states'].items():
                row[f'module_{mod_name}_heat'] = mod_state['heat_score']
                row[f'module_{mod_name}_state'] = mod_state['state']

            results.append(row)

        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.set_index('date')
        return df

    def apply_trend_amplifier(self, base_ewi: float,
                               trend_heat: float) -> float:
        """
        使用 TrendHeatScore 放大 Structure 层的风险评估

        公式:
            amplified_ewi = base_ewi + (100 - base_ewi) × amplifier × trend_heat

        Parameters:
        -----------
        base_ewi : float
            Structure 层的基础 EWI 值 (0-100)
        trend_heat : float
            TrendHeatScore (0-1)

        Returns:
        --------
        float : 放大后的 EWI 值 (0-100)
        """
        if np.isnan(trend_heat):
            return base_ewi

        amplifier = AGGREGATION_PARAMS.get('amplifier_strength', 0.6)
        amplified = base_ewi + (100 - base_ewi) * amplifier * trend_heat
        return min(100, amplified)

    def get_summary(self) -> dict:
        """返回当前配置摘要"""
        summary = {
            'modules': {},
            'enabled_factors': 0,
            'total_factors': len(self.config),
        }

        for mod_name, mod_info in self.modules.items():
            enabled = [f for f in mod_info['factors']
                      if self.config.get(f, {}).get('enabled', False)]
            summary['modules'][mod_name] = {
                'name': mod_info['name'],
                'enabled_factors': enabled,
                'count': len(enabled),
            }
            summary['enabled_factors'] += len(enabled)

        return summary


# ==============================================================================
# 便捷函数
# ==============================================================================

def get_current_trend_score(data_dir: str = None) -> dict:
    """快速获取当前 TrendScore"""
    ts = TrendScore(data_dir=data_dir)
    return ts.compute_latest()


def get_trend_history(start_date: str = None, end_date: str = None,
                       data_dir: str = None) -> pd.DataFrame:
    """快速获取历史 TrendScore"""
    ts = TrendScore(data_dir=data_dir)
    return ts.compute_history(start_date, end_date)


def print_trend_status(result: dict = None):
    """打印 TrendScore 状态"""
    if result is None:
        result = get_current_trend_score()

    print("=" * 60)
    print("TREND SCORE STATUS")
    print("=" * 60)

    print(f"\nDate: {result.get('date', 'N/A')}")
    print(f"Trend Heat Score: {result.get('trend_heat_score', 0):.2f}")
    print(f"Trend State: {result.get('trend_state', 'N/A')}")

    flags = result.get('trigger_flags', {})
    print(f"\nTrigger Flags:")
    print(f"  Any Critical: {flags.get('any_critical', False)}")
    print(f"  Multi-Module Alert: {flags.get('multi_module_alert', False)}")
    print(f"  Dominant Module: {flags.get('dominant_module', 'N/A')}")

    print(f"\nModule States:")
    for mod_name, mod_state in result.get('module_states', {}).items():
        print(f"  Module {mod_name}:")
        print(f"    Heat Score: {mod_state.get('heat_score', 0):.2f}")
        print(f"    State: {mod_state.get('state', 'N/A')}")
        print(f"    Dominant Factor: {mod_state.get('dominant_factor', 'N/A')}")
        if mod_state.get('factors_in_alert'):
            print(f"    Factors in Alert: {mod_state['factors_in_alert']}")


if __name__ == '__main__':
    print("Testing TrendScore (v4.0 - 数据驱动权重版)...")

    ts = TrendScore()

    print("\n[Configuration Summary]")
    summary = ts.get_summary()
    print(f"  Enabled factors: {summary['enabled_factors']}/{summary['total_factors']}")
    for mod_name, mod_info in summary['modules'].items():
        print(f"  Module {mod_name} ({mod_info['name']}): {mod_info['count']} factors")

    print("\n[v4.0 Factor Reliability Weights]")
    for factor, weight in sorted(ts.factor_reliability_weights.items()):
        print(f"  {factor}: {weight:.3f}")

    print("\n[v4.0 Module Reliability Weights]")
    for mod, weight in sorted(ts.module_reliability_weights.items()):
        print(f"  Module {mod}: {weight:.3f}")

    print("\n[Latest TrendScore]")
    result = ts.compute_latest()
    print_trend_status(result)
