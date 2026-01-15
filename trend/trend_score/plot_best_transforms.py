"""
绘制每个因子的 Best Transform 与 SPX 的对照图
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path

# 配置: 每个因子的 Best Transform
BEST_TRANSFORMS = {
    'A1_VTS': 'pctl_5y',           # 5/5 gates
    'A2_SKEW': 'pctl_1y',          # 3/5 gates
    'A3_MOVE': 'delta_zscore_1y',  # 4/5 gates
    'B1_Funding': 'pctl_1y',       # 4/5 gates
    'B2_GCF_IORB': 'pctl_1y',      # 3/5 gates
    'C1_HY_Spread': 'zscore_1y',   # 4/5 gates
    'C2_IG_Spread': 'zscore_1y',   # 4/5 gates
    'D1_HYG_Flow': 'delta_zscore_1y',  # 2/5 gates (REJECTED)
    'D2_LQD_Flow': 'pctl_1y',      # 3/5 gates
    'D3_TLT_Flow': 'zscore_3y',    # 3/5 gates
}

# 文件名映射
FILE_NAMES = {
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

# 列名前缀映射
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


def load_data():
    """加载所有因子数据和 SPX"""
    base_dir = Path(__file__).parent.parent / 'data'

    # 加载 SPX
    spx_path = Path(__file__).parent.parent.parent / 'structure' / 'data' / 'raw' / 'spx.csv'
    spx = pd.read_csv(spx_path, parse_dates=['date'], index_col='date')

    # 加载各因子的 best transform
    factor_data = {}
    for factor_name, transform in BEST_TRANSFORMS.items():
        file_path = base_dir / FILE_NAMES[factor_name]
        if not file_path.exists():
            print(f"Warning: {file_path} not found")
            continue

        df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')

        # 构造列名
        prefix = COL_PREFIX[factor_name]
        col_name = f"{prefix}_{transform}"

        if col_name not in df.columns:
            # 尝试找到匹配的列
            matching_cols = [c for c in df.columns if transform in c]
            if matching_cols:
                col_name = matching_cols[0]
            else:
                print(f"Warning: {col_name} not found in {file_path}")
                print(f"  Available columns: {list(df.columns)}")
                continue

        factor_data[factor_name] = df[[col_name]].rename(columns={col_name: factor_name})

    return spx, factor_data


def plot_all_factors():
    """绘制所有因子与 SPX 的对照图"""
    spx, factor_data = load_data()

    # 创建子图布局: 1个SPX + 10个因子 = 11个子图
    n_factors = len(factor_data)
    fig, axes = plt.subplots(n_factors + 1, 1, figsize=(16, 3 * (n_factors + 1)), sharex=True)

    # 找到共同的日期范围
    all_dates = spx.index
    for name, df in factor_data.items():
        all_dates = all_dates.intersection(df.index)

    start_date = all_dates.min()
    end_date = all_dates.max()

    # 绘制 SPX
    ax0 = axes[0]
    spx_plot = spx.loc[start_date:end_date, 'close']
    ax0.plot(spx_plot.index, spx_plot.values, 'k-', linewidth=1)
    ax0.set_ylabel('SPX', fontsize=10)
    ax0.set_title('SPX Close Price', fontsize=12)
    ax0.grid(True, alpha=0.3)

    # 标记重要危机时期
    crisis_periods = [
        ('2008-09-15', '2009-03-09', 'GFC', 'red'),
        ('2011-08-01', '2011-10-04', 'Debt Crisis', 'orange'),
        ('2015-08-18', '2016-02-11', 'China/Oil', 'yellow'),
        ('2018-10-03', '2018-12-26', 'Q4 2018', 'pink'),
        ('2020-02-19', '2020-03-23', 'COVID', 'red'),
        ('2022-01-03', '2022-10-12', '2022 Bear', 'orange'),
    ]

    for start, end, label, color in crisis_periods:
        try:
            ax0.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.2, color=color, label=label)
        except:
            pass

    # 颜色映射
    colors = plt.cm.tab10(np.linspace(0, 1, n_factors))

    # 绘制各因子
    for i, (factor_name, df) in enumerate(factor_data.items()):
        ax = axes[i + 1]
        transform = BEST_TRANSFORMS[factor_name]

        factor_values = df.loc[start_date:end_date, factor_name]
        ax.plot(factor_values.index, factor_values.values, color=colors[i], linewidth=1)
        ax.set_ylabel(factor_name.replace('_', '\n'), fontsize=9)
        ax.set_title(f'{factor_name} ({transform})', fontsize=10, loc='left')
        ax.grid(True, alpha=0.3)

        # 添加危机阴影
        for start, end, label, color in crisis_periods:
            try:
                ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.15, color=color)
            except:
                pass

    plt.xlabel('Date', fontsize=12)
    plt.tight_layout()

    # 保存图片
    output_path = Path(__file__).parent / 'best_transforms_vs_spx.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def plot_normalized_overlay():
    """在同一张图上绘制所有因子（归一化后）与 SPX"""
    spx, factor_data = load_data()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True,
                                    gridspec_kw={'height_ratios': [1, 2]})

    # 找到共同日期范围
    all_dates = spx.index
    for name, df in factor_data.items():
        all_dates = all_dates.intersection(df.index)

    start_date = all_dates.min()
    end_date = all_dates.max()

    # 上图: SPX
    spx_plot = spx.loc[start_date:end_date, 'close']
    ax1.plot(spx_plot.index, spx_plot.values, 'k-', linewidth=1.5, label='SPX')
    ax1.set_ylabel('SPX Close', fontsize=11)
    ax1.set_title('SPX vs All Factor Best Transforms (Normalized)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # 危机阴影
    crisis_periods = [
        ('2008-09-15', '2009-03-09', 'GFC'),
        ('2011-08-01', '2011-10-04', 'Debt'),
        ('2015-08-18', '2016-02-11', 'China'),
        ('2018-10-03', '2018-12-26', 'Q4\'18'),
        ('2020-02-19', '2020-03-23', 'COVID'),
        ('2022-01-03', '2022-10-12', '2022'),
    ]

    for start, end, label in crisis_periods:
        try:
            ax1.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.2, color='red')
            ax2.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.15, color='red')
        except:
            pass

    # 下图: 所有因子归一化叠加
    colors = plt.cm.tab10(np.linspace(0, 1, len(factor_data)))

    for i, (factor_name, df) in enumerate(factor_data.items()):
        transform = BEST_TRANSFORMS[factor_name]
        factor_values = df.loc[start_date:end_date, factor_name]

        # 标准化到 0-100
        fv_min = factor_values.min()
        fv_max = factor_values.max()
        if fv_max > fv_min:
            normalized = 100 * (factor_values - fv_min) / (fv_max - fv_min)
        else:
            normalized = factor_values * 0 + 50

        label = f'{factor_name} ({transform})'
        ax2.plot(normalized.index, normalized.values, color=colors[i],
                linewidth=1, alpha=0.8, label=label)

    ax2.set_ylabel('Normalized Value (0-100)', fontsize=11)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', fontsize=8, ncol=2)
    ax2.set_ylim(0, 100)

    plt.tight_layout()

    output_path = Path(__file__).parent / 'best_transforms_normalized.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


if __name__ == '__main__':
    print("="*60)
    print("Plotting Best Transforms vs SPX")
    print("="*60)

    print("\n1. Individual subplots...")
    plot_all_factors()

    print("\n2. Normalized overlay...")
    plot_normalized_overlay()

    print("\nDone!")
