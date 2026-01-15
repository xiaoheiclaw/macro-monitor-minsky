#!/usr/bin/env python3
"""
绘制 TrendScore 历史时间序列 (v3.0 - 温度校准版)

支持：
1. 原始历史图（修正前后对比）
2. 校准后的状态分布统计
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from trend.trend_score.trend_score import TrendScore
from trend.trend_score.config import QUANTILE_THRESHOLDS


def load_spx():
    """Load SPX daily data"""
    filepath = os.path.join(PROJECT_ROOT, 'SPX 1D Data (1).csv')
    df = pd.read_csv(filepath, parse_dates=['time'])
    return df.set_index('time')['close']


def plot_trend_history():
    """绘制 TrendScore 历史与 SPX 对照图 (v3.0 带校准)"""
    print("Computing TrendScore history (v3.0)...")

    ts = TrendScore()
    history = ts.compute_history(freq='D')

    print(f"History range: {history.index.min()} to {history.index.max()}")
    print(f"Total rows: {len(history)}")

    # 校准阈值
    print("\nCalibrating thresholds...")
    thresholds = ts.calibrate(history)
    print(f"Calibrated thresholds:")
    print(f"  CRITICAL (95th pctl): {thresholds['CRITICAL']:.3f}")
    print(f"  ALERT (85th pctl): {thresholds['ALERT']:.3f}")
    print(f"  WATCH (60th pctl): {thresholds['WATCH']:.3f}")

    # 使用校准阈值重新计算状态
    def calibrated_state(heat):
        if heat >= thresholds['CRITICAL']:
            return 'CRITICAL'
        elif heat >= thresholds['ALERT']:
            return 'ALERT'
        elif heat >= thresholds['WATCH']:
            return 'WATCH'
        else:
            return 'CALM'

    history['calibrated_state'] = history['trend_heat_score'].apply(calibrated_state)

    # Load SPX
    spx = load_spx()

    # 找到共同日期范围
    common_start = max(history.index.min(), spx.index.min())
    common_end = min(history.index.max(), spx.index.max())

    history = history[(history.index >= common_start) & (history.index <= common_end)]
    spx = spx[(spx.index >= common_start) & (spx.index <= common_end)]

    # 创建图表
    fig, axes = plt.subplots(6, 1, figsize=(16, 18), sharex=True,
                             gridspec_kw={'height_ratios': [2, 1, 1, 1, 1, 1]})

    # 危机时期
    crisis_periods = [
        ('2008-09-15', '2009-03-09', 'GFC', 'red'),
        ('2011-08-01', '2011-10-04', 'Debt', 'orange'),
        ('2015-08-18', '2016-02-11', 'China', 'yellow'),
        ('2018-10-03', '2018-12-26', 'Q4\'18', 'pink'),
        ('2020-02-19', '2020-03-23', 'COVID', 'red'),
        ('2022-01-03', '2022-10-12', '2022', 'orange'),
    ]

    # 1. SPX
    ax0 = axes[0]
    ax0.plot(spx.index, spx.values, 'k-', linewidth=1)
    ax0.set_ylabel('SPX', fontsize=10)
    ax0.set_title('SPX vs TrendScore History (v3.0 Calibrated)', fontsize=14)
    ax0.grid(True, alpha=0.3)

    for start, end, label, color in crisis_periods:
        try:
            ax0.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.2, color=color)
        except:
            pass

    # 2. Trend Heat Score (with calibrated thresholds)
    ax1 = axes[1]
    ax1.fill_between(history.index, 0, history['trend_heat_score'],
                     color='steelblue', alpha=0.7)
    # 使用校准阈值而不是固定阈值
    ax1.axhline(y=thresholds['CRITICAL'], color='red', linestyle='--', alpha=0.5,
                label=f'CRITICAL ({thresholds["CRITICAL"]:.2f})')
    ax1.axhline(y=thresholds['ALERT'], color='orange', linestyle='--', alpha=0.5,
                label=f'ALERT ({thresholds["ALERT"]:.2f})')
    ax1.axhline(y=thresholds['WATCH'], color='yellow', linestyle='--', alpha=0.5,
                label=f'WATCH ({thresholds["WATCH"]:.2f})')
    ax1.set_ylabel('Trend Heat', fontsize=10)
    ax1.set_ylim(0, 1)
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(True, alpha=0.3)

    for start, end, label, color in crisis_periods:
        try:
            ax1.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.15, color=color)
        except:
            pass

    # 3-6. Module Heat Scores
    module_colors = {'A': 'red', 'B': 'green', 'C': 'blue', 'D': 'purple'}
    module_names = {
        'A': 'Volatility',
        'B': 'Funding',
        'C': 'Credit',
        'D': 'Flow'
    }

    for i, (mod, name) in enumerate(module_names.items()):
        ax = axes[2 + i]
        col = f'module_{mod}_heat'
        if col in history.columns:
            ax.fill_between(history.index, 0, history[col],
                           color=module_colors[mod], alpha=0.6)
            ax.axhline(y=0.8, color='red', linestyle='--', alpha=0.3)
            ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.3)
            ax.axhline(y=0.3, color='yellow', linestyle='--', alpha=0.3)
        ax.set_ylabel(f'Mod {mod}\n{name}', fontsize=9)
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)

        for start, end, label, color in crisis_periods:
            try:
                ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.1, color=color)
            except:
                pass

    plt.xlabel('Date', fontsize=12)
    plt.tight_layout()

    output_path = Path(__file__).parent / 'trend_history_v3.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_path}")
    plt.close()

    # 打印一些统计信息
    print("\n" + "=" * 60)
    print("TREND SCORE STATISTICS (v4.1)")
    print("=" * 60)

    # v4.1: 数据质量分层统计
    print("\n" + "-" * 40)
    print("DATA COVERAGE BY ERA (v4.1)")
    print("-" * 40)
    print("""
Trend 层的 intended backtest window:
  - Primary:     1998+ (A+B+C, 信用模块上线)
  - Recommended: 2004+ (全模块完整版)
  - Earliest:    1991+ (A+B only, 波动+资金面)

1986-1990 的数据用于 Funding 局部压力回溯，而非系统趋势评分。
""")

    # 按时期统计数据质量
    if 'quality_level' in history.columns:
        eras = [
            ('1986-1990', '1986-01-01', '1990-12-31', 'WEAK', 'Module B only'),
            ('1991-1997', '1991-01-01', '1997-12-31', 'OK', 'Module A+B'),
            ('1998-2003', '1998-01-01', '2003-12-31', 'STRONG', 'Module A+B+C'),
            ('2004+', '2004-01-01', '2099-12-31', 'STRONG', 'Full coverage'),
        ]
        print("Data Quality by Era:")
        for era_name, start, end, expected, desc in eras:
            era_data = history[(history.index >= start) & (history.index <= end)]
            if len(era_data) > 0:
                quality_counts = era_data['quality_level'].value_counts()
                trustworthy_rate = era_data['is_trustworthy'].mean() * 100 if 'is_trustworthy' in era_data.columns else 0
                print(f"  {era_name} ({desc}):")
                print(f"    Valid (TrendScore OK): {trustworthy_rate:.1f}%")
                for level in ['STRONG', 'OK', 'WEAK', 'NONE']:
                    count = quality_counts.get(level, 0)
                    if count > 0:
                        print(f"      {level}: {count} ({count/len(era_data)*100:.1f}%)")
    else:
        # 旧格式兼容
        print("(quality_level column not found, using legacy format)")

    print("\n" + "-" * 40)
    print("TREND HEAT SCORE STATISTICS")
    print("-" * 40)

    # 只统计有效数据
    valid_heat = history['trend_heat_score'].dropna()
    print(f"\nTrend Heat Score (valid data only, n={len(valid_heat)}):")
    print(f"  Mean: {valid_heat.mean():.3f}")
    print(f"  Std: {valid_heat.std():.3f}")
    print(f"  Max: {valid_heat.max():.3f}")

    # 原始状态分布 (包含 INSUFFICIENT_DATA)
    print(f"\nState Distribution (all data):")
    state_counts = history['trend_state'].value_counts()
    for state in ['CALM', 'WATCH', 'ALERT', 'CRITICAL', 'INSUFFICIENT_DATA']:
        count = state_counts.get(state, 0)
        if count > 0:
            print(f"  {state}: {count} ({count/len(history)*100:.1f}%)")

    # 校准后状态分布 (仅有效数据)
    valid_data = history[history['trend_state'] != 'INSUFFICIENT_DATA']
    if len(valid_data) > 0:
        valid_data['calibrated_state'] = valid_data['trend_heat_score'].apply(calibrated_state)
        print(f"\nCalibrated State Distribution (valid data only, n={len(valid_data)}):")
        cal_counts = valid_data['calibrated_state'].value_counts()
        for state in ['CALM', 'WATCH', 'ALERT', 'CRITICAL']:
            count = cal_counts.get(state, 0)
            print(f"  {state}: {count} ({count/len(valid_data)*100:.1f}%)")

    return history, thresholds


def plot_crisis_zoom():
    """绘制危机时期的放大图"""
    print("\nComputing crisis period zoom...")

    ts = TrendScore()

    crises = {
        'GFC': ('2007-01-01', '2010-01-01'),
        'COVID': ('2019-06-01', '2021-01-01'),
        '2022': ('2021-06-01', '2023-06-01'),
    }

    fig, axes = plt.subplots(len(crises), 2, figsize=(16, 4 * len(crises)))

    spx = load_spx()

    for i, (crisis_name, (start, end)) in enumerate(crises.items()):
        history = ts.compute_history(start_date=start, end_date=end, freq='D')

        if len(history) == 0:
            continue

        spx_period = spx[(spx.index >= start) & (spx.index <= end)]

        # SPX
        ax_spx = axes[i, 0]
        ax_spx.plot(spx_period.index, spx_period.values, 'k-', linewidth=1)
        ax_spx.set_ylabel('SPX', fontsize=10)
        ax_spx.set_title(f'{crisis_name}: SPX', fontsize=12)
        ax_spx.grid(True, alpha=0.3)

        # Trend Heat
        ax_trend = axes[i, 1]
        ax_trend.fill_between(history.index, 0, history['trend_heat_score'],
                             color='steelblue', alpha=0.7)

        # 绘制各模块
        for mod, color in [('A', 'red'), ('B', 'green'), ('C', 'blue'), ('D', 'purple')]:
            col = f'module_{mod}_heat'
            if col in history.columns:
                ax_trend.plot(history.index, history[col], color=color,
                            alpha=0.5, linewidth=1, label=f'Mod {mod}')

        ax_trend.axhline(y=0.8, color='red', linestyle='--', alpha=0.5)
        ax_trend.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5)
        ax_trend.set_ylabel('Heat Score', fontsize=10)
        ax_trend.set_title(f'{crisis_name}: TrendScore', fontsize=12)
        ax_trend.set_ylim(0, 1)
        ax_trend.legend(loc='upper right', fontsize=8)
        ax_trend.grid(True, alpha=0.3)

    plt.tight_layout()

    output_path = Path(__file__).parent / 'trend_crisis_zoom.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Plotting TrendScore History (v4.1 Data Quality Tiering)")
    print("=" * 60)

    print("\n1. Full history plot with calibration...")
    history, thresholds = plot_trend_history()

    print("\n2. Crisis period zoom...")
    plot_crisis_zoom()

    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    print(f"\nCalibrated Thresholds (based on historical distribution):")
    print(f"  CRITICAL: heat_score >= {thresholds['CRITICAL']:.3f} (top 5%)")
    print(f"  ALERT: heat_score >= {thresholds['ALERT']:.3f} (top 15%)")
    print(f"  WATCH: heat_score >= {thresholds['WATCH']:.3f} (top 40%)")

    # v4.1: 数据质量总结
    if 'quality_level' in history.columns:
        print("\n" + "=" * 60)
        print("DATA QUALITY SUMMARY (v4.1)")
        print("=" * 60)
        quality_counts = history['quality_level'].value_counts()
        total = len(history)
        print(f"\nOverall Quality Distribution:")
        for level in ['STRONG', 'OK', 'WEAK', 'NONE']:
            count = quality_counts.get(level, 0)
            if count > 0:
                print(f"  {level}: {count} ({count/total*100:.1f}%)")

        trustworthy_count = history['is_trustworthy'].sum() if 'is_trustworthy' in history.columns else 0
        print(f"\nTrustworthy Rate (coverage >= 2): {trustworthy_count}/{total} ({trustworthy_count/total*100:.1f}%)")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
