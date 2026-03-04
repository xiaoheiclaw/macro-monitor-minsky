#!/usr/bin/env python3
"""
TrendScore v4.0 测试套件
========================

针对 v2.0+ API 的 pytest 风格测试。

测试内容:
1. intensity 映射函数 (intensity_upper/lower/band, three-tier, continuous)
2. config 辅助函数 (get_enabled_factors, get_module_factors, determine_state_from_heat)
3. TrendScore 类初始化与权重计算
4. 单因子状态计算
5. 模块聚合
6. 趋势输出 (含 data_quality 分层)
7. 历史回测 (危机期间表现)
8. Trend Amplifier (Structure 集成)
9. 校准流程 (calibrate)
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from trend.trend_score.config import (
    FACTOR_CONFIG,
    MODULES,
    DATA_FILE_MAPPING,
    MODULE_STATE_THRESHOLDS,
    TREND_STATE_THRESHOLDS,
    AGGREGATION_PARAMS,
    FACTOR_VALIDATION_METRICS,
    RELIABILITY_CONFIG,
    DATA_QUALITY_CONFIG,
    get_enabled_factors,
    get_module_factors,
    get_factor_zones,
    get_zone_weight,
    determine_state_from_heat,
)
from trend.trend_score.intensity import (
    intensity_upper,
    intensity_lower,
    intensity_band,
    compute_intensity,
    compute_three_tier_intensity,
    compute_continuous_intensity,
    zscore_to_pctl,
)
from trend.trend_score.trend_score import (
    TrendScore,
    get_current_trend_score,
    get_trend_history,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def trend_score():
    """创建 TrendScore 实例（使用默认 data_dir）"""
    return TrendScore()


@pytest.fixture
def trend_score_continuous():
    """创建使用连续强度计算的 TrendScore 实例"""
    return TrendScore(use_continuous_intensity=True)


# ==============================================================================
# Test 1: Intensity Mapping Functions
# ==============================================================================

class TestIntensityFunctions:
    """测试 intensity 映射函数"""

    def test_intensity_upper_at_boundary(self):
        assert intensity_upper(50, 50) == pytest.approx(0.0, abs=0.001)

    def test_intensity_upper_midpoint(self):
        assert intensity_upper(75, 50) == pytest.approx(0.5, abs=0.001)

    def test_intensity_upper_max(self):
        assert intensity_upper(100, 50) == pytest.approx(1.0, abs=0.001)

    def test_intensity_upper_safe_zone(self):
        assert intensity_upper(30, 50) == pytest.approx(0.0, abs=0.001)

    def test_intensity_lower_at_boundary(self):
        assert intensity_lower(50, 50) == pytest.approx(0.0, abs=0.001)

    def test_intensity_lower_midpoint(self):
        assert intensity_lower(25, 50) == pytest.approx(0.5, abs=0.001)

    def test_intensity_lower_max(self):
        assert intensity_lower(0, 50) == pytest.approx(1.0, abs=0.001)

    def test_intensity_lower_safe_zone(self):
        assert intensity_lower(80, 50) == pytest.approx(0.0, abs=0.001)

    def test_intensity_band_lower_bound(self):
        assert intensity_band(0, 0, 90) == pytest.approx(0.0, abs=0.05)

    def test_intensity_band_midpoint(self):
        assert intensity_band(45, 0, 90) == pytest.approx(0.5, abs=0.05)

    def test_intensity_band_upper_bound(self):
        assert intensity_band(90, 0, 90) == pytest.approx(1.0, abs=0.05)

    def test_zscore_to_pctl_zero(self):
        """Z=0 应映射到 50"""
        assert zscore_to_pctl(0) == pytest.approx(50.0, abs=0.1)

    def test_zscore_to_pctl_extreme_positive(self):
        """Z=3 应映射到 100"""
        assert zscore_to_pctl(3.0) == pytest.approx(100.0, abs=0.1)

    def test_zscore_to_pctl_extreme_negative(self):
        """Z=-3 应映射到 0"""
        assert zscore_to_pctl(-3.0) == pytest.approx(0.0, abs=0.1)

    def test_zscore_to_pctl_clipping(self):
        """超出 [-3, 3] 范围应裁剪"""
        assert zscore_to_pctl(5.0) == pytest.approx(100.0, abs=0.1)
        assert zscore_to_pctl(-5.0) == pytest.approx(0.0, abs=0.1)


# ==============================================================================
# Test 2: Three-Tier Intensity
# ==============================================================================

class TestThreeTierIntensity:
    """测试三档 Zone 的 intensity 计算"""

    def test_calm_zone(self):
        """低分位 → tier=CALM, intensity=0"""
        zones = FACTOR_CONFIG['A1_VTS']['zones']
        result = compute_three_tier_intensity(10, zones, 'high_is_danger')
        assert result['tier'] == 'CALM'
        assert result['intensity'] == pytest.approx(0.0, abs=0.01)

    def test_watch_zone(self):
        """WATCH 范围内 → tier=WATCH"""
        zones = FACTOR_CONFIG['A1_VTS']['zones']
        result = compute_three_tier_intensity(60, zones, 'high_is_danger')
        assert result['tier'] == 'WATCH'
        assert 0 < result['intensity'] <= 0.4

    def test_alert_zone(self):
        """ALERT 范围内 → tier=ALERT"""
        zones = FACTOR_CONFIG['A1_VTS']['zones']
        result = compute_three_tier_intensity(88, zones, 'high_is_danger')
        assert result['tier'] == 'ALERT'
        assert result['intensity'] > 0.4

    def test_critical_zone(self):
        """CRITICAL 范围内 → tier=CRITICAL"""
        zones = FACTOR_CONFIG['A1_VTS']['zones']
        result = compute_three_tier_intensity(97, zones, 'high_is_danger')
        assert result['tier'] == 'CRITICAL'
        assert result['intensity'] > 0.7


# ==============================================================================
# Test 3: Config Helper Functions
# ==============================================================================

class TestConfigHelpers:
    """测试 config.py 的辅助函数"""

    def test_get_enabled_factors_excludes_disabled(self):
        enabled = get_enabled_factors()
        for name, cfg in enabled.items():
            assert cfg['enabled'] is True
        # D1_HYG_Flow 应被排除 (enabled=False)
        assert 'D1_HYG_Flow' not in enabled

    def test_get_enabled_factors_count(self):
        enabled = get_enabled_factors()
        # 10 total - 1 disabled (D1_HYG_Flow) = 9
        assert len(enabled) == 9

    def test_get_module_factors(self):
        mod_a = get_module_factors('A')
        assert 'A1_VTS' in mod_a
        assert 'A2_SKEW' in mod_a
        assert 'A3_MOVE' in mod_a

    def test_get_module_factors_invalid(self):
        result = get_module_factors('Z')
        assert result == {}

    def test_get_factor_zones(self):
        zones = get_factor_zones('A1_VTS')
        assert 'WATCH' in zones
        assert 'ALERT' in zones
        assert 'CRITICAL' in zones

    def test_get_zone_weight(self):
        assert get_zone_weight('WATCH') == pytest.approx(0.4)
        assert get_zone_weight('ALERT') == pytest.approx(0.7)
        assert get_zone_weight('CRITICAL') == pytest.approx(1.0)

    def test_determine_state_from_heat(self):
        assert determine_state_from_heat(0.1) == 'CALM'
        assert determine_state_from_heat(0.35) == 'WATCH'
        assert determine_state_from_heat(0.55) == 'ALERT'
        assert determine_state_from_heat(0.75) == 'CRITICAL'

    def test_data_file_mapping_matches_factor_config(self):
        """DATA_FILE_MAPPING 与 FACTOR_CONFIG[x]['file'] 一致"""
        for name, filename in DATA_FILE_MAPPING.items():
            assert name in FACTOR_CONFIG, f"{name} missing from FACTOR_CONFIG"
            assert FACTOR_CONFIG[name]['file'] == filename

    def test_modules_cover_all_enabled_factors(self):
        """所有启用因子都被某个 Module 包含"""
        all_module_factors = set()
        for mod in MODULES.values():
            all_module_factors.update(mod['factors'])
        for name in get_enabled_factors():
            assert name in all_module_factors, f"{name} not in any module"


# ==============================================================================
# Test 4: TrendScore Initialization & Weights
# ==============================================================================

class TestTrendScoreInit:
    """测试 TrendScore 初始化和权重计算"""

    def test_factor_reliability_weights_normalized(self, trend_score):
        """每个模块内因子权重之和应为 1"""
        for mod_name, mod_info in MODULES.items():
            mod_factors = [
                f for f in mod_info['factors']
                if f in trend_score.factor_reliability_weights
            ]
            if mod_factors:
                total = sum(trend_score.factor_reliability_weights[f] for f in mod_factors)
                assert total == pytest.approx(1.0, abs=0.01), \
                    f"Module {mod_name} weights sum to {total}, not 1.0"

    def test_module_reliability_weights_normalized(self, trend_score):
        """模块权重之和应为 1"""
        total = sum(trend_score.module_reliability_weights.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_module_weight_upper_cap(self, trend_score):
        """每个模块权重不应超过上限"""
        max_w = RELIABILITY_CONFIG.get('max_module_weight', 0.55)
        for mod, w in trend_score.module_reliability_weights.items():
            assert w <= max_w + 0.01, f"Module {mod} weight {w} exceeds cap {max_w}"

    def test_module_weight_lower_floor(self, trend_score):
        """每个模块权重不应低于下限（归一化后可能微调，检查原始值）"""
        # 归一化后下限不严格等于 min_module_weight，但应大于 0
        for mod, w in trend_score.module_reliability_weights.items():
            assert w > 0, f"Module {mod} weight is 0"

    def test_summary(self, trend_score):
        summary = trend_score.get_summary()
        assert summary['enabled_factors'] == 9
        assert summary['total_factors'] == len(FACTOR_CONFIG)
        assert 'A' in summary['modules']
        assert 'B' in summary['modules']
        assert 'C' in summary['modules']
        assert 'D' in summary['modules']

    def test_default_not_calibrated(self, trend_score):
        assert trend_score._is_calibrated is False


# ==============================================================================
# Test 5: Factor State Computation
# ==============================================================================

class TestFactorState:
    """测试单因子状态计算"""

    def test_compute_factor_state_calm(self, trend_score):
        """低分位应返回 CALM"""
        result = trend_score.compute_factor_state('A1_VTS', 10.0)
        assert result['tier'] == 'CALM'
        assert result['pctl'] == 10.0

    def test_compute_factor_state_critical(self, trend_score):
        """极高分位应返回 CRITICAL"""
        result = trend_score.compute_factor_state('A1_VTS', 98.0)
        assert result['tier'] == 'CRITICAL'
        assert result['intensity'] > 0.7

    def test_disabled_factor_returns_disabled(self, trend_score):
        """禁用因子应返回 DISABLED"""
        result = trend_score.compute_factor_state('D1_HYG_Flow', 90.0)
        assert result['tier'] == 'DISABLED'
        assert result['intensity'] == 0.0


# ==============================================================================
# Test 6: Module State Computation
# ==============================================================================

class TestModuleState:
    """测试模块聚合"""

    def test_empty_module(self, trend_score):
        result = trend_score.compute_module_state('A', {})
        assert result['state'] == 'NO_DATA'
        assert result['heat_score'] == 0.0

    def test_module_state_with_calm_factors(self, trend_score):
        factor_states = {
            'A1_VTS': {'tier': 'CALM', 'intensity': 0.0},
            'A2_SKEW': {'tier': 'CALM', 'intensity': 0.0},
            'A3_MOVE': {'tier': 'CALM', 'intensity': 0.0},
        }
        result = trend_score.compute_module_state('A', factor_states)
        assert result['state'] == 'CALM'
        assert result['heat_score'] == pytest.approx(0.0, abs=0.01)

    def test_module_state_with_high_factors(self, trend_score):
        factor_states = {
            'A1_VTS': {'tier': 'CRITICAL', 'intensity': 0.95},
            'A2_SKEW': {'tier': 'ALERT', 'intensity': 0.6},
            'A3_MOVE': {'tier': 'ALERT', 'intensity': 0.7},
        }
        result = trend_score.compute_module_state('A', factor_states)
        assert result['heat_score'] > 0.5
        assert result['state'] in ('ALERT', 'CRITICAL')
        assert result['dominant_factor'] == 'A1_VTS'

    def test_module_max_avg_aggregation(self, trend_score):
        """验证 α*max + (1-α)*weighted_mean 公式"""
        alpha = AGGREGATION_PARAMS.get('module_max_weight', 0.4)
        factor_states = {
            'C1_HY_Spread': {'tier': 'ALERT', 'intensity': 0.8},
            'C2_IG_Spread': {'tier': 'WATCH', 'intensity': 0.3},
        }
        result = trend_score.compute_module_state('C', factor_states)
        # heat_score 应介于 max 和 avg 之间
        assert 0.3 <= result['heat_score'] <= 0.8


# ==============================================================================
# Test 7: Trend Output & Data Quality
# ==============================================================================

class TestTrendOutput:
    """测试趋势层输出（含数据质量分层）"""

    def test_no_data_returns_insufficient(self, trend_score):
        result = trend_score.compute_trend_output({})
        assert result['trend_state'] == 'INSUFFICIENT_DATA'
        assert result['data_quality']['quality_level'] == 'NONE'

    def test_single_module_returns_weak(self, trend_score):
        """单模块 → WEAK 模式，输出 local_signals"""
        factor_states = {
            'A1_VTS': trend_score.compute_factor_state('A1_VTS', 85.0),
            'A2_SKEW': trend_score.compute_factor_state('A2_SKEW', 70.0),
            'A3_MOVE': trend_score.compute_factor_state('A3_MOVE', 60.0),
        }
        result = trend_score.compute_trend_output(factor_states)
        dq = result['data_quality']
        assert dq['coverage_modules'] == 1
        assert dq['quality_level'] == 'WEAK'
        assert result['trend_state'] == 'INSUFFICIENT_DATA'
        assert result['local_signals'] is not None
        assert result['local_signals']['active_module'] == 'A'

    def test_two_modules_returns_ok(self, trend_score):
        """两模块 → OK 模式，输出标准 TrendScore"""
        factor_states = {
            'A1_VTS': trend_score.compute_factor_state('A1_VTS', 85.0),
            'A2_SKEW': trend_score.compute_factor_state('A2_SKEW', 70.0),
            'A3_MOVE': trend_score.compute_factor_state('A3_MOVE', 60.0),
            'C1_HY_Spread': trend_score.compute_factor_state('C1_HY_Spread', 80.0),
            'C2_IG_Spread': trend_score.compute_factor_state('C2_IG_Spread', 75.0),
        }
        result = trend_score.compute_trend_output(factor_states)
        dq = result['data_quality']
        assert dq['coverage_modules'] >= 2
        assert dq['quality_level'] in ('OK', 'STRONG')
        assert dq['is_trustworthy'] is True
        assert not np.isnan(result['trend_heat_score'])
        assert result['trend_state'] in ('CALM', 'WATCH', 'ALERT', 'CRITICAL')

    def test_all_calm_is_calm(self, trend_score):
        """所有因子 CALM → 趋势 CALM"""
        factor_states = {}
        for name, cfg in FACTOR_CONFIG.items():
            if cfg.get('enabled', False):
                factor_states[name] = trend_score.compute_factor_state(name, 10.0)
        result = trend_score.compute_trend_output(factor_states)
        assert result['trend_state'] == 'CALM'
        assert result['trend_heat_score'] < 0.3

    def test_critical_needs_credit_or_multi_module(self, trend_score):
        """v3.0: CRITICAL 需要 Credit CRITICAL 或多模块联动"""
        # 只有 Module A 极高，C 不是 CRITICAL → 不应触发 CRITICAL
        factor_states = {}
        for name in ['A1_VTS', 'A2_SKEW', 'A3_MOVE']:
            factor_states[name] = trend_score.compute_factor_state(name, 98.0)
        # 其他模块 CALM
        for name in ['B1_Funding', 'B2_GCF_IORB', 'C1_HY_Spread', 'C2_IG_Spread',
                      'D2_LQD_Flow', 'D3_TLT_Flow']:
            factor_states[name] = trend_score.compute_factor_state(name, 10.0)
        result = trend_score.compute_trend_output(factor_states)
        # 因为只有 A 模块高，C 不是 CRITICAL，也没有多模块联动 → 不应是 CRITICAL
        assert result['trend_state'] != 'CRITICAL'

    def test_trigger_flags(self, trend_score):
        factor_states = {}
        for name, cfg in FACTOR_CONFIG.items():
            if cfg.get('enabled', False):
                factor_states[name] = trend_score.compute_factor_state(name, 95.0)
        result = trend_score.compute_trend_output(factor_states)
        flags = result['trigger_flags']
        assert 'any_critical' in flags
        assert 'multi_module_alert' in flags
        assert 'dominant_module' in flags
        assert 'valid_modules_count' in flags


# ==============================================================================
# Test 8: Data Loading (Integration - uses real data files)
# ==============================================================================

class TestDataLoading:
    """测试数据加载（集成测试，依赖实际数据文件）"""

    def test_load_all_data(self, trend_score):
        data = trend_score.load_all_data()
        assert len(data) > 0, "No data files loaded"
        for name, df in data.items():
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0, f"{name} is empty"

    def test_load_single_factor(self, trend_score):
        df = trend_score.load_factor_data('A1_VTS')
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_unknown_factor_raises(self, trend_score):
        with pytest.raises(ValueError, match="Unknown factor"):
            trend_score.load_factor_data('NONEXISTENT')

    def test_data_file_mapping_files_exist(self, trend_score):
        """DATA_FILE_MAPPING 中的文件都应该存在"""
        for name, filename in DATA_FILE_MAPPING.items():
            filepath = os.path.join(trend_score.data_dir, filename)
            assert os.path.exists(filepath), f"Missing: {filepath}"


# ==============================================================================
# Test 9: Compute Latest & History (Integration)
# ==============================================================================

class TestComputeIntegration:
    """集成测试: compute_latest 和 compute_history"""

    def test_compute_latest(self, trend_score):
        result = trend_score.compute_latest()
        assert 'trend_heat_score' in result
        assert 'trend_state' in result
        assert 'module_states' in result
        assert 'data_quality' in result
        # 应有数据
        assert result['data_quality']['coverage_modules'] >= 2

    def test_compute_latest_state_valid(self, trend_score):
        result = trend_score.compute_latest()
        valid_states = {'CALM', 'WATCH', 'ALERT', 'CRITICAL', 'INSUFFICIENT_DATA'}
        assert result['trend_state'] in valid_states

    def test_compute_history(self, trend_score):
        history = trend_score.compute_history(freq='ME')
        assert isinstance(history, pd.DataFrame)
        assert len(history) > 0
        assert 'trend_heat_score' in history.columns
        assert 'trend_state' in history.columns

    def test_history_has_data_quality_columns(self, trend_score):
        history = trend_score.compute_history(start_date='2020-01-01', freq='ME')
        if len(history) > 0:
            assert 'coverage_modules' in history.columns
            assert 'quality_level' in history.columns


# ==============================================================================
# Test 10: Trend Amplifier
# ==============================================================================

class TestTrendAmplifier:
    """测试 Trend Amplifier (Structure 层集成)"""

    def test_zero_trend_no_amplification(self, trend_score):
        amplified = trend_score.apply_trend_amplifier(30, 0.0)
        assert amplified == pytest.approx(30.0, abs=0.01)

    def test_nan_trend_returns_base(self, trend_score):
        amplified = trend_score.apply_trend_amplifier(30, np.nan)
        assert amplified == pytest.approx(30.0, abs=0.01)

    def test_full_trend_amplifies(self, trend_score):
        amplified = trend_score.apply_trend_amplifier(30, 1.0)
        strength = AGGREGATION_PARAMS.get('amplifier_strength', 0.6)
        expected = 30 + (100 - 30) * strength * 1.0
        assert amplified == pytest.approx(expected, abs=0.1)

    def test_amplified_never_exceeds_100(self, trend_score):
        amplified = trend_score.apply_trend_amplifier(90, 1.0)
        assert amplified <= 100.0

    def test_higher_base_less_room(self, trend_score):
        """高基础 EWI 放大空间更小"""
        amp_low = trend_score.apply_trend_amplifier(20, 0.5)
        amp_high = trend_score.apply_trend_amplifier(80, 0.5)
        assert (amp_low - 20) > (amp_high - 80)


# ==============================================================================
# Test 11: Calibration
# ==============================================================================

class TestCalibration:
    """测试分位数校准"""

    def test_calibrate_returns_thresholds(self, trend_score):
        thresholds = trend_score.calibrate()
        assert 'CRITICAL' in thresholds
        assert 'ALERT' in thresholds
        assert 'WATCH' in thresholds

    def test_calibrate_ordering(self, trend_score):
        thresholds = trend_score.calibrate()
        assert thresholds['WATCH'] <= thresholds['ALERT'] <= thresholds['CRITICAL']

    def test_calibrated_flag(self, trend_score):
        assert trend_score._is_calibrated is False
        trend_score.calibrate()
        assert trend_score._is_calibrated is True

    def test_get_thresholds_after_calibration(self, trend_score):
        trend_score.calibrate()
        th = trend_score.get_thresholds()
        # 校准后阈值应不同于默认值（通常）
        assert 'CRITICAL' in th


# ==============================================================================
# Test 12: Crisis Period Performance (Integration)
# ==============================================================================

class TestCrisisDetection:
    """测试危机期间表现（集成测试）"""

    @pytest.fixture(autouse=True)
    def setup(self, trend_score):
        self.ts = trend_score
        self.history = trend_score.compute_history(
            start_date='2008-01-01', freq='ME'
        )

    def test_history_not_empty(self):
        assert len(self.history) > 0, "No historical data available"

    def test_gfc_elevated(self):
        """GFC 期间 heat_score 应偏高"""
        if len(self.history) == 0:
            pytest.skip("No data")
        mask = (self.history.index >= '2008-09-01') & (self.history.index <= '2009-03-01')
        crisis = self.history[mask]
        if len(crisis) > 0:
            mean_heat = crisis['trend_heat_score'].mean()
            # GFC 期间应比整体均值高
            overall_mean = self.history['trend_heat_score'].dropna().mean()
            assert mean_heat > overall_mean, \
                f"GFC mean heat {mean_heat:.3f} not above overall {overall_mean:.3f}"

    def test_covid_elevated(self):
        """COVID crash 期间 heat_score 应偏高"""
        if len(self.history) == 0:
            pytest.skip("No data")
        mask = (self.history.index >= '2020-02-01') & (self.history.index <= '2020-04-30')
        crisis = self.history[mask]
        if len(crisis) > 0:
            mean_heat = crisis['trend_heat_score'].mean()
            overall_mean = self.history['trend_heat_score'].dropna().mean()
            assert mean_heat > overall_mean, \
                f"COVID mean heat {mean_heat:.3f} not above overall {overall_mean:.3f}"


# ==============================================================================
# Test 13: Convenience Functions
# ==============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_get_current_trend_score(self):
        result = get_current_trend_score()
        assert 'trend_heat_score' in result
        assert 'trend_state' in result

    def test_get_trend_history(self):
        history = get_trend_history(start_date='2023-01-01')
        assert isinstance(history, pd.DataFrame)


# ==============================================================================
# Main (for manual execution)
# ==============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
