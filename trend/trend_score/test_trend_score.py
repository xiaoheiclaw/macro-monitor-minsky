#!/usr/bin/env python3
"""
TrendScore 验证脚本
==================

测试内容:
1. 单因子 intensity 映射
2. 权重计算
3. TrendScore 聚合
4. 历史回测 (危机期间表现)
5. 与 Structure 层集成测试
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from trend.trend_score.config import (
    FACTOR_CONFIG,
    FACTOR_WEIGHTS,
    get_enabled_factors,
    get_normalized_weights,
)
from trend.trend_score.intensity import (
    intensity_upper,
    intensity_lower,
    intensity_band,
    compute_intensity,
)
from trend.trend_score.trend_score import TrendScore, get_current_trend_score


def test_intensity_functions():
    """测试 intensity 映射函数"""
    print("\n" + "=" * 60)
    print("Test 1: Intensity Mapping Functions")
    print("=" * 60)

    # Test upper
    print("\n[intensity_upper]")
    test_cases = [
        (50, 50, 0.0, "边界"),
        (75, 50, 0.5, "中间"),
        (100, 50, 1.0, "最高"),
        (30, 50, 0.0, "安全区"),
    ]
    for pctl, lower, expected, desc in test_cases:
        result = intensity_upper(pctl, lower)
        status = "PASS" if abs(result - expected) < 0.001 else "FAIL"
        print(f"  {desc}: pctl={pctl}, lower={lower} -> {result:.3f} (expected {expected}) [{status}]")

    # Test lower
    print("\n[intensity_lower]")
    test_cases = [
        (50, 50, 0.0, "边界"),
        (25, 50, 0.5, "中间"),
        (0, 50, 1.0, "最低"),
        (80, 50, 0.0, "安全区"),
    ]
    for pctl, upper, expected, desc in test_cases:
        result = intensity_lower(pctl, upper)
        status = "PASS" if abs(result - expected) < 0.001 else "FAIL"
        print(f"  {desc}: pctl={pctl}, upper={upper} -> {result:.3f} (expected {expected}) [{status}]")

    # Test band
    print("\n[intensity_band]")
    test_cases = [
        (0, 0, 90, 0.0, "下界"),
        (45, 0, 90, 0.5, "中间"),
        (90, 0, 90, 1.0, "上界"),
        (95, 0, 90, 0.5, "超出衰减"),
    ]
    for pctl, low, high, expected, desc in test_cases:
        result = intensity_band(pctl, low, high)
        status = "PASS" if abs(result - expected) < 0.1 else "FAIL"
        print(f"  {desc}: pctl={pctl}, zone=({low},{high}) -> {result:.3f} (expected ~{expected}) [{status}]")

    print("\n✓ Intensity functions test completed")


def test_weights():
    """测试权重计算"""
    print("\n" + "=" * 60)
    print("Test 2: Factor Weights")
    print("=" * 60)

    weights = get_normalized_weights()

    print("\n[Computed Weights]")
    total = 0
    for name, weight in sorted(weights.items(), key=lambda x: -x[1]):
        cfg = FACTOR_CONFIG[name]
        gates = cfg.get('gates', 0)
        lift = cfg.get('lift', 1.0)
        quality = (gates / 5) * max(0, lift - 1)
        print(f"  {name}: {weight*100:.1f}% (gates={gates}, lift={lift:.2f}, quality={quality:.3f})")
        total += weight

    print(f"\n  Total: {total*100:.1f}% (should be 100%)")

    # 验证 T1 VTS 是最高权重
    max_factor = max(weights, key=weights.get)
    assert max_factor == 'T1_VTS', f"Expected T1_VTS to have max weight, got {max_factor}"
    print(f"\n✓ T1_VTS has highest weight ({weights['T1_VTS']*100:.1f}%) as expected")


def test_trend_score_class():
    """测试 TrendScore 类"""
    print("\n" + "=" * 60)
    print("Test 3: TrendScore Class")
    print("=" * 60)

    ts = TrendScore()

    print("\n[Weights Summary]")
    summary = ts.get_weights_summary()
    print(summary.to_string(index=False))

    print("\n[Latest TrendScore]")
    result = ts.compute_latest()

    if not np.isnan(result.get('trend_score', np.nan)):
        print(f"  Score: {result['trend_score']:.3f}")
        print(f"  State: {result['trend_state']}")
        print(f"  Weighted Sum: {result.get('weighted_sum', 0):.3f}")
        print(f"  Max Intensity: {result.get('max_intensity', 0):.3f}")
        print(f"  Coverage: {result.get('coverage', 0)*100:.1f}%")

        if result.get('top_contributors'):
            print(f"  Top Contributors:")
            for factor, intensity in result['top_contributors']:
                print(f"    - {factor}: {intensity:.3f}")

        if result.get('percentiles'):
            print(f"  Percentiles:")
            for factor, pctl in result['percentiles'].items():
                if not np.isnan(pctl):
                    print(f"    - {factor}: {pctl:.1f}%")
    else:
        print("  No data available")

    print("\n✓ TrendScore class test completed")


def test_crisis_detection():
    """测试危机检测能力"""
    print("\n" + "=" * 60)
    print("Test 4: Crisis Detection (Historical Backtest)")
    print("=" * 60)

    ts = TrendScore()

    # 定义危机期间
    crises = {
        'GFC': ('2007-10-01', '2009-03-01'),
        'COVID': ('2020-02-01', '2020-03-31'),
        '2022 Rate Hike': ('2022-01-01', '2022-10-01'),
    }

    # 计算历史
    history = ts.compute_history(start_date='2008-01-01')

    if len(history) == 0:
        print("  No historical data available")
        return

    print(f"\n[Historical TrendScore Stats]")
    print(f"  Date Range: {history.index.min().date()} to {history.index.max().date()}")
    print(f"  Mean: {history['trend_score'].mean():.3f}")
    print(f"  Std: {history['trend_score'].std():.3f}")
    print(f"  Median: {history['trend_score'].median():.3f}")

    # 各危机期间的表现
    print("\n[Crisis Period Performance]")
    for crisis_name, (start, end) in crises.items():
        mask = (history.index >= start) & (history.index <= end)
        crisis_data = history[mask]

        if len(crisis_data) > 0:
            mean_score = crisis_data['trend_score'].mean()
            max_score = crisis_data['trend_score'].max()
            pct_stress = (crisis_data['trend_state'] == 'STRESS').mean() * 100
            pct_risk_off = (crisis_data['trend_state'].isin(['STRESS', 'RISK_OFF'])).mean() * 100

            print(f"\n  {crisis_name} ({start} to {end}):")
            print(f"    Mean Score: {mean_score:.3f}")
            print(f"    Max Score: {max_score:.3f}")
            print(f"    % in STRESS: {pct_stress:.1f}%")
            print(f"    % in STRESS/RISK_OFF: {pct_risk_off:.1f}%")

    # 非危机期间
    print("\n[Non-Crisis Baseline]")
    non_crisis_mask = pd.Series(True, index=history.index)
    for _, (start, end) in crises.items():
        non_crisis_mask &= ~((history.index >= start) & (history.index <= end))

    non_crisis = history[non_crisis_mask]
    if len(non_crisis) > 0:
        print(f"  Mean Score: {non_crisis['trend_score'].mean():.3f}")
        print(f"  % in CALM: {(non_crisis['trend_state'] == 'CALM').mean()*100:.1f}%")

    print("\n✓ Crisis detection test completed")


def test_trend_amplifier():
    """测试 Trend 放大器"""
    print("\n" + "=" * 60)
    print("Test 5: Trend Amplifier (Structure Integration)")
    print("=" * 60)

    ts = TrendScore()

    print("\n[Amplifier Effect]")
    print("  Formula: amplified_ewi = base_ewi + (100 - base_ewi) × 0.6 × trend_score")

    test_cases = [
        (30, 0.0, "CALM market, no amplification"),
        (30, 0.5, "TENSE market, moderate amplification"),
        (30, 0.8, "STRESS market, strong amplification"),
        (50, 0.5, "Medium EWI + TENSE"),
        (70, 0.8, "High EWI + STRESS"),
    ]

    print(f"\n  {'Base EWI':<10} {'TrendScore':<12} {'Amplified':<12} {'Change':<10} Description")
    print("  " + "-" * 60)

    for base, score, desc in test_cases:
        amplified = ts.apply_trend_amplifier(base, score)
        change = amplified - base
        print(f"  {base:<10.0f} {score:<12.2f} {amplified:<12.1f} {change:+<10.1f} {desc}")

    print("\n✓ Trend amplifier test completed")


def test_current_status():
    """显示当前状态"""
    print("\n" + "=" * 60)
    print("CURRENT TREND STATUS")
    print("=" * 60)

    result = get_current_trend_score()

    if np.isnan(result.get('trend_score', np.nan)):
        print("\n  No current data available")
        return

    score = result['trend_score']
    state = result['trend_state']

    # 状态颜色指示
    state_indicator = {
        'CALM': '🟢',
        'TENSE': '🟡',
        'RISK_OFF': '🟠',
        'STRESS': '🔴',
        'NO_DATA': '⚪',
    }

    print(f"\n  {state_indicator.get(state, '⚪')} TrendScore: {score:.3f}")
    print(f"  State: {state}")
    print(f"  Coverage: {result.get('coverage', 0)*100:.1f}%")

    if result.get('factor_intensities'):
        print(f"\n  [Factor Intensities]")
        for factor, intensity in sorted(result['factor_intensities'].items(),
                                        key=lambda x: -x[1]):
            bar = '█' * int(intensity * 20) + '░' * (20 - int(intensity * 20))
            print(f"    {factor:<12} [{bar}] {intensity:.2f}")

    # 放大效果示例
    print(f"\n  [Amplification Example]")
    base_ewi = 40
    amplified = TrendScore().apply_trend_amplifier(base_ewi, score)
    print(f"    If Structure EWI = {base_ewi}")
    print(f"    Amplified EWI = {amplified:.1f} (+{amplified-base_ewi:.1f})")


def main():
    print("=" * 60)
    print("TrendScore Validation Suite")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_intensity_functions()
    test_weights()
    test_trend_score_class()
    test_crisis_detection()
    test_trend_amplifier()
    test_current_status()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    main()
