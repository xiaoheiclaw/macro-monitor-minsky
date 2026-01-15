"""
TrendScore Factor Transform Validation
=======================================

对每个 TrendScore 因子测试所有可用的 transform，计算 IC/AUC，找出最优配置。

Transform 类型:
- pctl_1y: 1年滚动分位数
- pctl_5y: 5年滚动分位数
- zscore_1y: 1年滚动 Z-score
- zscore_3y: 3年滚动 Z-score
- delta_zscore_1y: 1年 Delta Z-score (当前 - 1年前)

5-Gate 验证指标:
- Gate 1: AUC > 0.55 (二分类预测能力)
- Gate 2: |IC| > 0.05 (与前向收益相关性)
- Gate 3: Lift > 1.2x (高分位数时危机发生率提升)
- Gate 4: Lead >= 1月 (信号领先于危机)
- Gate 5: Precision > 15% (CRITICAL档位精确率)

Usage:
    python -m trend.trend_score.validate_transforms
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score

# Path setup
TREND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = TREND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Factor configuration
FACTOR_FILES = {
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

# Column prefix mapping
COL_PREFIX = {
    'A1_VTS': 'vts',
    'A2_SKEW': 'skew',
    'A3_MOVE': 'move',
    'B1_Funding': 'funding',
    'B2_GCF_IORB': 'gcf_iorb',
    'C1_HY_Spread': 'hy_spread',
    'C2_IG_Spread': 'ig_spread',
    'D1_HYG_Flow': 'hyg_flow',
    'D2_LQD_Flow': 'lqd_flow',
    'D3_TLT_Flow': 'tlt_flow',
}

# Available transforms for each factor (based on CSV columns)
TRANSFORM_VARIANTS = ['pctl_1y', 'pctl_5y', 'zscore_1y', 'zscore_3y', 'delta_zscore_1y']

# Current configuration (from config.py)
CURRENT_TRANSFORMS = {
    'A1_VTS': 'pctl_5y',
    'A2_SKEW': 'pctl_1y',
    'A3_MOVE': 'delta_zscore_1y',
    'B1_Funding': 'pctl_1y_combined',
    'B2_GCF_IORB': 'pctl_1y',
    'C1_HY_Spread': 'pctl_1y',
    'C2_IG_Spread': 'pctl_1y',
    'D2_LQD_Flow': 'pctl_1y',
    'D3_TLT_Flow': 'zscore_3y',
}


def load_spx() -> pd.Series:
    """加载 SPX 数据"""
    spx_path = PROJECT_ROOT / 'structure' / 'data' / 'raw' / 'spx.csv'
    df = pd.read_csv(spx_path, parse_dates=['date'], index_col='date')
    return df['close']


def compute_forward_return(price: pd.Series, horizon_days: int = 252) -> pd.Series:
    """计算前向收益率"""
    return price.shift(-horizon_days) / price - 1


def compute_forward_mdd(price: pd.Series, horizon_days: int = 252) -> pd.Series:
    """计算前向最大回撤"""
    result = pd.Series(index=price.index, dtype=float)

    for i in range(len(price) - horizon_days):
        future_prices = price.iloc[i:i + horizon_days + 1]
        peak = future_prices.expanding().max()
        drawdown = (future_prices - peak) / peak
        result.iloc[i] = drawdown.min()

    return result


def compute_ic(factor: pd.Series, forward_return: pd.Series) -> Dict:
    """计算 IC (Spearman 相关性)"""
    aligned = pd.DataFrame({
        'factor': factor,
        'return': forward_return
    }).dropna()

    if len(aligned) < 30:
        return {'ic': np.nan, 'p_value': np.nan, 'n': 0}

    corr, p_value = stats.spearmanr(aligned['factor'], aligned['return'])

    return {
        'ic': corr,
        'p_value': p_value,
        'n': len(aligned)
    }


def compute_auc(factor: pd.Series, forward_mdd: pd.Series, threshold: float = -0.20) -> Dict:
    """计算 AUC (预测 MDD < threshold 的能力)"""
    aligned = pd.DataFrame({
        'factor': factor,
        'mdd': forward_mdd
    }).dropna()

    if len(aligned) < 30:
        return {'auc': np.nan, 'n': 0}

    # 二分类标签: MDD < threshold = 1 (危机)
    y_true = (aligned['mdd'] < threshold).astype(int)

    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        return {'auc': np.nan, 'n': len(aligned), 'n_crisis': int(y_true.sum())}

    try:
        auc = roc_auc_score(y_true, aligned['factor'])
    except:
        auc = np.nan

    return {
        'auc': auc,
        'n': len(aligned),
        'n_crisis': int(y_true.sum())
    }


def compute_lift(factor: pd.Series, forward_mdd: pd.Series,
                 threshold: float = -0.20, percentile: float = 80) -> Dict:
    """计算 Lift (高分位数时危机发生率提升)"""
    aligned = pd.DataFrame({
        'factor': factor,
        'mdd': forward_mdd
    }).dropna()

    if len(aligned) < 30:
        return {'lift': np.nan, 'baseline_cr': np.nan, 'high_cr': np.nan}

    crisis = (aligned['mdd'] < threshold).astype(int)
    baseline_cr = crisis.mean()

    if baseline_cr == 0:
        return {'lift': np.nan, 'baseline_cr': 0, 'high_cr': np.nan}

    # 高分位数区域
    pctl_value = aligned['factor'].quantile(percentile / 100)
    high_mask = aligned['factor'] >= pctl_value

    if high_mask.sum() == 0:
        return {'lift': np.nan, 'baseline_cr': baseline_cr, 'high_cr': np.nan}

    high_cr = crisis[high_mask].mean()
    lift = high_cr / baseline_cr

    return {
        'lift': lift,
        'baseline_cr': baseline_cr,
        'high_cr': high_cr
    }


def compute_lead_time(factor: pd.Series, forward_mdd: pd.Series,
                      threshold: float = -0.20, lead_months: List[int] = [1, 2, 3, 6]) -> Dict:
    """计算信号领先时间"""
    results = {}

    for lead in lead_months:
        # Shift factor forward (signal lead_months before crisis)
        shifted_factor = factor.shift(lead * 21)  # ~21 trading days per month

        aligned = pd.DataFrame({
            'factor': shifted_factor,
            'mdd': forward_mdd
        }).dropna()

        if len(aligned) < 30:
            results[f'lead_{lead}m'] = np.nan
            continue

        crisis = (aligned['mdd'] < threshold).astype(int)

        if crisis.sum() == 0 or crisis.sum() == len(crisis):
            results[f'lead_{lead}m'] = np.nan
            continue

        try:
            auc = roc_auc_score(crisis, aligned['factor'])
            results[f'lead_{lead}m'] = auc
        except:
            results[f'lead_{lead}m'] = np.nan

    # Find best lead time
    valid_leads = {k: v for k, v in results.items() if not np.isnan(v) and v > 0.5}
    if valid_leads:
        best_lead = max(valid_leads.items(), key=lambda x: x[1])
        results['best_lead'] = int(best_lead[0].split('_')[1].replace('m', ''))
        results['best_lead_auc'] = best_lead[1]
    else:
        results['best_lead'] = 0
        results['best_lead_auc'] = np.nan

    return results


def run_5gate_validation(factor: pd.Series, forward_return: pd.Series,
                         forward_mdd: pd.Series) -> Dict:
    """运行 5-Gate 验证"""
    results = {
        'gates_passed': 0,
        'gate_details': {}
    }

    # Gate 1: AUC > 0.55
    auc_result = compute_auc(factor, forward_mdd)
    gate1_pass = auc_result['auc'] > 0.55 if not np.isnan(auc_result['auc']) else False
    results['gate_details']['gate1_auc'] = {
        'pass': gate1_pass,
        'value': auc_result['auc'],
        'threshold': 0.55
    }
    if gate1_pass:
        results['gates_passed'] += 1

    # Gate 2: |IC| > 0.05
    ic_result = compute_ic(factor, forward_return)
    gate2_pass = abs(ic_result['ic']) > 0.05 if not np.isnan(ic_result['ic']) else False
    results['gate_details']['gate2_ic'] = {
        'pass': gate2_pass,
        'value': ic_result['ic'],
        'threshold': 0.05
    }
    if gate2_pass:
        results['gates_passed'] += 1

    # Gate 3: Lift > 1.2x
    lift_result = compute_lift(factor, forward_mdd)
    gate3_pass = lift_result['lift'] > 1.2 if not np.isnan(lift_result['lift']) else False
    results['gate_details']['gate3_lift'] = {
        'pass': gate3_pass,
        'value': lift_result['lift'],
        'threshold': 1.2
    }
    if gate3_pass:
        results['gates_passed'] += 1

    # Gate 4: Lead >= 1 month
    lead_result = compute_lead_time(factor, forward_mdd)
    gate4_pass = lead_result['best_lead'] >= 1
    results['gate_details']['gate4_lead'] = {
        'pass': gate4_pass,
        'value': lead_result['best_lead'],
        'threshold': 1
    }
    if gate4_pass:
        results['gates_passed'] += 1

    # Gate 5: Precision > 15% (at 80th percentile)
    precision_result = compute_lift(factor, forward_mdd, percentile=95)
    precision = precision_result['high_cr'] if precision_result['high_cr'] else 0
    gate5_pass = precision > 0.15
    results['gate_details']['gate5_precision'] = {
        'pass': gate5_pass,
        'value': precision,
        'threshold': 0.15
    }
    if gate5_pass:
        results['gates_passed'] += 1

    # Summary metrics
    results['auc'] = auc_result['auc']
    results['ic'] = ic_result['ic']
    results['lift'] = lift_result['lift']
    results['lead'] = lead_result['best_lead']
    results['precision'] = precision

    return results


def validate_factor_transforms(factor_name: str, data_dir: Path,
                               spx: pd.Series, fwd_return: pd.Series,
                               fwd_mdd: pd.Series) -> Dict:
    """验证单个因子的所有 transform"""
    file_path = data_dir / FACTOR_FILES[factor_name]

    if not file_path.exists():
        print(f"  Warning: {file_path} not found")
        return {}

    df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')
    prefix = COL_PREFIX[factor_name]

    results = {}

    for transform in TRANSFORM_VARIANTS:
        col_name = f"{prefix}_{transform}"

        # Try to find matching column
        if col_name not in df.columns:
            matching_cols = [c for c in df.columns if transform in c]
            if matching_cols:
                col_name = matching_cols[0]
            else:
                continue

        factor_series = df[col_name]

        # Resample to daily alignment with SPX
        factor_daily = factor_series.reindex(spx.index, method='ffill')

        # Run validation
        validation = run_5gate_validation(factor_daily, fwd_return, fwd_mdd)
        validation['transform'] = transform
        validation['col_name'] = col_name

        results[transform] = validation

    return results


def generate_report(all_results: Dict) -> str:
    """生成验证报告"""
    lines = []
    lines.append("# TrendScore Factor Transform Validation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary table
    lines.append("## Summary: Best Transform per Factor")
    lines.append("")
    lines.append("| Factor | Current | Best IC | Best AUC | Best Gates | Recommended |")
    lines.append("|--------|---------|---------|----------|------------|-------------|")

    recommendations = {}

    for factor_name, transforms in all_results.items():
        if not transforms:
            continue

        current = CURRENT_TRANSFORMS.get(factor_name, 'N/A')

        # Find best by different metrics
        best_ic = max(transforms.items(), key=lambda x: abs(x[1]['ic']) if not np.isnan(x[1]['ic']) else 0)
        best_auc = max(transforms.items(), key=lambda x: x[1]['auc'] if not np.isnan(x[1]['auc']) else 0)
        best_gates = max(transforms.items(), key=lambda x: x[1]['gates_passed'])

        # Recommendation: prefer gates_passed, then AUC
        if best_gates[1]['gates_passed'] >= 4:
            recommended = best_gates[0]
        elif best_auc[1]['auc'] and best_auc[1]['auc'] > 0.6:
            recommended = best_auc[0]
        else:
            recommended = best_gates[0]

        recommendations[factor_name] = recommended

        current_short = current.replace('_combined', '').replace('_', '')
        lines.append(
            f"| {factor_name} | {current_short} | "
            f"{best_ic[0]} ({best_ic[1]['ic']:.3f}) | "
            f"{best_auc[0]} ({best_auc[1]['auc']:.3f}) | "
            f"{best_gates[0]} ({best_gates[1]['gates_passed']}/5) | "
            f"**{recommended}** |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed results per factor
    for factor_name, transforms in all_results.items():
        if not transforms:
            continue

        lines.append(f"## {factor_name}")
        lines.append("")
        lines.append(f"**Current Transform**: `{CURRENT_TRANSFORMS.get(factor_name, 'N/A')}`")
        lines.append("")
        lines.append("| Transform | AUC | IC | Lift | Lead | Gates |")
        lines.append("|-----------|-----|-----|------|------|-------|")

        for transform, result in sorted(transforms.items(),
                                         key=lambda x: x[1]['gates_passed'],
                                         reverse=True):
            auc = f"{result['auc']:.3f}" if not np.isnan(result['auc']) else "N/A"
            ic = f"{result['ic']:.3f}" if not np.isnan(result['ic']) else "N/A"
            lift = f"{result['lift']:.2f}x" if not np.isnan(result['lift']) else "N/A"
            lead = f"{result['lead']}m" if result['lead'] > 0 else "0"
            gates = f"{result['gates_passed']}/5"

            # Highlight best
            marker = " **" if transform == recommendations.get(factor_name) else ""
            lines.append(f"| {transform}{marker} | {auc} | {ic} | {lift} | {lead} | {gates} |")

        lines.append("")

        # Gate details for recommended transform
        rec = recommendations.get(factor_name)
        if rec and rec in transforms:
            lines.append(f"### Gate Details for `{rec}`")
            lines.append("")
            for gate_name, gate_info in transforms[rec]['gate_details'].items():
                status = "PASS" if gate_info['pass'] else "FAIL"
                value = f"{gate_info['value']:.3f}" if isinstance(gate_info['value'], float) else gate_info['value']
                lines.append(f"- {gate_name}: {status} (value={value}, threshold={gate_info['threshold']})")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Recommended config
    lines.append("## Recommended Configuration")
    lines.append("")
    lines.append("```python")
    lines.append("# trend/trend_score/config.py")
    lines.append("FACTOR_CONFIG = {")
    for factor_name, transform in recommendations.items():
        prefix = COL_PREFIX[factor_name]
        col_name = f"{prefix}_{transform}"
        lines.append(f"    '{factor_name}': {{'transform': '{col_name}', ...}},")
    lines.append("}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    print("=" * 70)
    print("TrendScore Factor Transform Validation")
    print("=" * 70)

    data_dir = TREND_DIR / 'data'

    # Load SPX and compute forward metrics
    print("\nLoading SPX data...")
    spx = load_spx()

    print("Computing forward returns (252 days)...")
    fwd_return = compute_forward_return(spx, horizon_days=252)

    print("Computing forward MDD (252 days)...")
    fwd_mdd = compute_forward_mdd(spx, horizon_days=252)

    print(f"  SPX range: {spx.index.min()} to {spx.index.max()}")
    print(f"  Valid forward return: {fwd_return.dropna().shape[0]} days")
    print(f"  Valid forward MDD: {fwd_mdd.dropna().shape[0]} days")

    # Validate each factor
    all_results = {}

    for factor_name in FACTOR_FILES.keys():
        print(f"\nValidating {factor_name}...")
        results = validate_factor_transforms(
            factor_name, data_dir, spx, fwd_return, fwd_mdd
        )
        all_results[factor_name] = results

        if results:
            best = max(results.items(), key=lambda x: x[1]['gates_passed'])
            print(f"  Best: {best[0]} ({best[1]['gates_passed']}/5 gates)")

    # Generate report
    print("\n" + "=" * 70)
    print("Generating Report...")
    print("=" * 70)

    report = generate_report(all_results)

    # Save report
    output_path = TREND_DIR / 'trend_score' / 'TRANSFORM_VALIDATION_REPORT.md'
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\n| Factor | Current | Recommended | Gates |")
    print("|--------|---------|-------------|-------|")

    for factor_name, transforms in all_results.items():
        if not transforms:
            continue

        current = CURRENT_TRANSFORMS.get(factor_name, 'N/A')
        best = max(transforms.items(), key=lambda x: x[1]['gates_passed'])

        change = "" if current.replace('_combined', '') == best[0] else " <-- CHANGE"
        print(f"| {factor_name} | {current} | {best[0]} | {best[1]['gates_passed']}/5 |{change}")


if __name__ == '__main__':
    main()
