#!/usr/bin/env python3
"""
Cache All Trend Factors Historical Data (v2)
=============================================

按新的模块结构缓存所有 Trend 层因子的历史数据。

模块结构:
=========
A. Volatility Regime (波动性制度)
   - 主指标: VTS (VIX/VIX3M - 1)
   - 辅指标: SKEW, MOVE

B. Funding / Liquidity Stress (资金/流动性压力)
   - 主指标: Funding Spread (TED/EFFR-SOFR)
   - 辅指标: GCF-IORB Spread

C. Credit Compensation (信用补偿)
   - 主指标: HY Yield - 10Y Yield
   - 辅指标: IG Yield - 10Y Yield

D. Flow Confirmation (资金流确认)
   - 主指标: HYG Flow
   - 辅指标: LQD Flow, TLT Flow

数据滞后性:
==========
- T+0 (实时): VIX, VIX3M, SKEW, MOVE
- T+1: EFFR, SOFR, GCF Repo, 10Y Yield, HY/IG OAS, ETF Shares
- T+7: Dealer Inventory (周频，发布滞后7天)
"""

import os
import sys
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from trend.V9_LQI_FACTORS.lqi_data_loader import LQIDataLoader

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# 通用工具函数
# =============================================================================

def compute_percentile(series: pd.Series, window: int, min_periods: int = None) -> pd.Series:
    """计算滚动历史分位数 (0-100)"""
    if min_periods is None:
        min_periods = window // 2
    return series.rolling(window, min_periods=min_periods).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).sum() / len(x.iloc[:-1]) * 100 if len(x) > 1 else 50
    )


def compute_zscore(series: pd.Series, window: int, min_periods: int = None) -> pd.Series:
    """计算滚动 Z-score"""
    if min_periods is None:
        min_periods = window // 2
    rolling_mean = series.rolling(window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window, min_periods=min_periods).std()
    return (series - rolling_mean) / rolling_std


def compute_all_zscores(series: pd.Series, prefix: str) -> dict:
    """计算所有时间窗口的 Z-score 及其变化

    返回:
    - {prefix}_zscore_3m: 3个月(63天)窗口 z-score
    - {prefix}_zscore_1y: 1年(252天)窗口 z-score
    - {prefix}_zscore_3y: 3年(756天)窗口 z-score
    - {prefix}_delta_zscore_3m: 1年 z-score 的 3个月变化 (当前 - 63天前)
    - {prefix}_delta_zscore_1y: 3年 z-score 的 1年变化 (当前 - 252天前)
    """
    results = {}

    # Z-scores at different windows
    zscore_3m = compute_zscore(series, 63, 32)
    zscore_1y = compute_zscore(series, 252)
    zscore_3y = compute_zscore(series, 756, 378)

    results[f'{prefix}_zscore_3m'] = zscore_3m
    results[f'{prefix}_zscore_1y'] = zscore_1y
    results[f'{prefix}_zscore_3y'] = zscore_3y

    # Delta z-scores (change over period)
    # 1年 z-score 的 3个月变化
    results[f'{prefix}_delta_zscore_3m'] = zscore_1y - zscore_1y.shift(63)
    # 3年 z-score 的 1年变化
    results[f'{prefix}_delta_zscore_1y'] = zscore_3y - zscore_3y.shift(252)

    return results


# =============================================================================
# Module A: Volatility Regime
# =============================================================================

def cache_a1_vts():
    """
    A1: VIX Term Structure (主指标)

    VTS = VIX / VIX3M - 1
    - 正值 = 期限结构倒挂 = 短期恐慌高于长期
    - 高分位 = 市场处于短期恐慌状态

    数据频率: 日频
    发布滞后: T+0 (实时)
    """
    print("\n" + "=" * 70)
    print("A1: VIX Term Structure (VTS) - 主指标")
    print("=" * 70)

    loader = LQIDataLoader()
    vix = loader.load_vix()
    vix3m = loader.load_vix3m()

    # Align
    common_idx = vix.dropna().index.intersection(vix3m.dropna().index)
    vix_aligned = vix.loc[common_idx]
    vix3m_aligned = vix3m.loc[common_idx]

    # VTS = VIX / VIX3M - 1
    vts = vix_aligned / vix3m_aligned - 1

    df = pd.DataFrame({
        'vix': vix_aligned,
        'vix3m': vix3m_aligned,
        'vts_raw': vts,
    })

    # Percentile transforms (日频: 252天=1年, 1260天=5年)
    df['vts_pctl_1y'] = compute_percentile(vts, 252)
    df['vts_pctl_5y'] = compute_percentile(vts, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(vts, 'vts')
    for col, series in zscore_cols.items():
        df[col] = series

    df['vts_is_inverted'] = (vts > 0).astype(int)

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'a1_vts.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Current VTS: {df['vts_raw'].iloc[-1]:.4f}")
    print(f"Saved: a1_vts.csv")

    return df


def cache_a2_skew():
    """
    A2: CBOE SKEW Index (辅指标)

    OTM Put vs Call 隐含波动率偏斜
    - 高SKEW = 投资者大量买入深度OTM Put对冲尾部风险
    - 反映对黑天鹅事件的担忧

    数据频率: 日频
    发布滞后: T+0 (实时)
    """
    print("\n" + "=" * 70)
    print("A2: CBOE SKEW Index - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()
    skew = loader.load_skew()

    df = pd.DataFrame({
        'skew_raw': skew,
    })

    df['skew_pctl_1y'] = compute_percentile(skew, 252)
    df['skew_pctl_5y'] = compute_percentile(skew, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(skew, 'skew')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'a2_skew.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Current SKEW: {df['skew_raw'].iloc[-1]:.1f}")
    print(f"Saved: a2_skew.csv")

    return df


def cache_a3_move():
    """
    A3: MOVE Index (辅指标)

    ICE BofA MOVE Index - 债券市场波动率
    - 类似VIX但针对债券市场
    - 高MOVE = 利率波动预期高 = 固收市场不确定性

    数据频率: 日频
    发布滞后: T+0 (实时)
    """
    print("\n" + "=" * 70)
    print("A3: MOVE Index - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()
    try:
        move = loader.load_move()
    except Exception as e:
        print(f"Error loading MOVE: {e}")
        return None

    df = pd.DataFrame({
        'move_raw': move,
    })

    df['move_pctl_1y'] = compute_percentile(move, 252)
    df['move_pctl_5y'] = compute_percentile(move, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(move, 'move')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'a3_move.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Current MOVE: {df['move_raw'].iloc[-1]:.1f}")
    print(f"Saved: a3_move.csv")

    return df


# =============================================================================
# Module B: Funding / Liquidity Stress
# =============================================================================

def cache_b1_funding():
    """
    B1: Funding Spread (主指标)

    TED(2018前) 或 EFFR-SOFR(2018后) 利差的 Z-score
    - 高值 = 银行间拆借成本上升 = 流动性紧张
    - 银行不愿互相借贷

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("B1: Funding Spread - 主指标")
    print("=" * 70)

    loader = LQIDataLoader()
    results = {}

    # TED Spread (日频)
    ted_zscores = {}
    try:
        ted = loader.load_ted_spread().dropna()
        results['ted_raw'] = ted
        results['ted_pctl_1y'] = compute_percentile(ted, 252)
        results['ted_pctl_5y'] = compute_percentile(ted, 1260, 504)

        # Z-score transforms for TED
        ted_zscores = compute_all_zscores(ted, 'ted')
        for col, series in ted_zscores.items():
            results[col] = series

        print(f"[TED] Range: {ted.index.min().date()} to {ted.index.max().date()}, rows={len(ted)}")
    except Exception as e:
        print(f"[TED] Error: {e}")

    # EFFR-SOFR (日频)
    effr_sofr_zscores = {}
    try:
        effr = loader.load_effr()
        sofr = loader.load_sofr()
        common_idx = effr.dropna().index.intersection(sofr.dropna().index)
        spread = effr.loc[common_idx] - sofr.loc[common_idx]

        results['effr'] = effr
        results['sofr'] = sofr
        results['effr_sofr_raw'] = spread
        results['effr_sofr_pctl_1y'] = compute_percentile(spread, 252)
        results['effr_sofr_pctl_5y'] = compute_percentile(spread, 1260, 504)

        # Z-score transforms for EFFR-SOFR
        effr_sofr_zscores = compute_all_zscores(spread, 'effr_sofr')
        for col, series in effr_sofr_zscores.items():
            results[col] = series

        print(f"[EFFR-SOFR] Range: {spread.index.min().date()} to {spread.index.max().date()}, rows={len(spread)}")
    except Exception as e:
        print(f"[EFFR-SOFR] Error: {e}")

    # Combined (spliced at 2018-04)
    if ted_zscores and effr_sofr_zscores:
        splice_date = pd.Timestamp('2018-04-01')

        # Helper function to splice two series
        def splice_series(ted_series, effr_series):
            if ted_series is None or len(ted_series) == 0:
                return effr_series
            if effr_series is None or len(effr_series) == 0:
                return ted_series
            # Ensure index is DatetimeIndex for comparison
            if not isinstance(ted_series.index, pd.DatetimeIndex):
                ted_series.index = pd.to_datetime(ted_series.index)
            if not isinstance(effr_series.index, pd.DatetimeIndex):
                effr_series.index = pd.to_datetime(effr_series.index)
            ted_part = ted_series[ted_series.index < splice_date]
            effr_part = effr_series[effr_series.index >= splice_date]
            combined = pd.concat([ted_part, effr_part])
            return combined[~combined.index.duplicated(keep='last')].sort_index()

        # Combined pctl_1y
        results['funding_pctl_1y_combined'] = splice_series(
            results['ted_pctl_1y'], results['effr_sofr_pctl_1y'])

        # Combined pctl_5y
        results['funding_pctl_5y_combined'] = splice_series(
            results['ted_pctl_5y'], results['effr_sofr_pctl_5y'])

        # Combined all z-score transforms
        for suffix in ['zscore_3m', 'zscore_1y', 'zscore_3y', 'delta_zscore_3m', 'delta_zscore_1y']:
            ted_col = f'ted_{suffix}'
            effr_col = f'effr_sofr_{suffix}'
            if ted_col in results and effr_col in results:
                results[f'funding_{suffix}_combined'] = splice_series(
                    results[ted_col], results[effr_col])

    df = pd.DataFrame(results)
    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'b1_funding.csv'))
    print(f"Total rows: {len(df)}")
    print(f"Saved: b1_funding.csv")

    return df


def cache_b2_gcf_iorb():
    """
    B2: GCF-IORB Spread (辅指标)

    GCF Repo Rate - EFFR (作为IORB代理)
    - 高值 = 回购市场利率高于政策利率
    - 抵押品紧张或流动性压力，货币市场stress的早期信号

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("B2: GCF-IORB Spread - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()

    try:
        gcf = loader.load_gcf_repo_full()
        effr = loader.load_effr()

        if len(gcf) == 0 or len(effr) == 0:
            print("  Warning: GCF or EFFR data not available, skipping B2")
            return pd.DataFrame()

        # Align
        common_idx = gcf.index.intersection(effr.index)
        if len(common_idx) == 0:
            print("  Warning: No overlapping dates between GCF and EFFR")
            return pd.DataFrame()

        gcf_aligned = gcf['Treasury_Rate'].reindex(common_idx)
        effr_aligned = effr.reindex(common_idx)

        # GCF - IORB spread (日频)
        spread = gcf_aligned - effr_aligned

        df = pd.DataFrame({
            'gcf_treasury': gcf_aligned,
            'effr': effr_aligned,
            'gcf_iorb_raw': spread,
        })

        df['gcf_iorb_pctl_1y'] = compute_percentile(spread, 252)
        df['gcf_iorb_pctl_5y'] = compute_percentile(spread, 1260, 504)

        # Z-score transforms (3m, 1y, 3y windows + deltas)
        zscore_cols = compute_all_zscores(spread, 'gcf_iorb')
        for col, series in zscore_cols.items():
            df[col] = series

        df.index.name = 'date'
        df.to_csv(os.path.join(OUTPUT_DIR, 'b2_gcf_iorb.csv'))
        print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
        print(f"Total rows: {len(df)}")
        print(f"Current Spread: {df['gcf_iorb_raw'].iloc[-1]:.4f}%")
        print(f"Saved: b2_gcf_iorb.csv")

        return df
    except Exception as e:
        print(f"  Warning: Failed to compute B2: {e}")
        return pd.DataFrame()


# =============================================================================
# Module C: Credit Compensation
# =============================================================================

def cache_c1_hy_spread():
    """
    C1: HY Yield - 10Y Yield (主指标)

    高收益债收益率 - 10年期国债收益率 = 信用利差
    - 类似"信用版VIX"
    - 高值 = 信用风险溢价高 = 市场对违约风险定价上升

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("C1: HY Yield - 10Y Yield - 主指标")
    print("=" * 70)

    loader = LQIDataLoader()

    try:
        hy_oas = loader.load_hy_oas()
        us_10y = loader.load_us_10y_yield()
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

    # OAS 本身就是利差，但我们也可以计算 HY Yield - 10Y
    # 注意: BAMLH0A0HYM2 是 OAS (Option-Adjusted Spread)，已经是相对无风险利率的利差
    # 所以直接用 OAS 作为信用利差指标

    df = pd.DataFrame({
        'hy_oas_raw': hy_oas,
        'us_10y': us_10y,
    })

    # Percentile transforms
    df['hy_spread_pctl_1y'] = compute_percentile(hy_oas, 252)
    df['hy_spread_pctl_5y'] = compute_percentile(hy_oas, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(hy_oas, 'hy_spread')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'c1_hy_spread.csv'))
    print(f"Range: {df.dropna().index.min().date()} to {df.dropna().index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Current HY OAS: {df['hy_oas_raw'].dropna().iloc[-1]:.2f}%")
    print(f"Saved: c1_hy_spread.csv")

    return df


def cache_c2_ig_spread():
    """
    C2: IG Yield - 10Y Yield (辅指标)

    投资级债收益率 - 10年期国债收益率
    - 更偏"高质量信用"
    - 相对于HY，IG更稳定，但极端情况下也会走阔

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("C2: IG Yield - 10Y Yield - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()

    try:
        ig_oas = loader.load_ig_oas()
        us_10y = loader.load_us_10y_yield()
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

    df = pd.DataFrame({
        'ig_oas_raw': ig_oas,
        'us_10y': us_10y,
    })

    # Percentile transforms
    df['ig_spread_pctl_1y'] = compute_percentile(ig_oas, 252)
    df['ig_spread_pctl_5y'] = compute_percentile(ig_oas, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(ig_oas, 'ig_spread')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'c2_ig_spread.csv'))
    print(f"Range: {df.dropna().index.min().date()} to {df.dropna().index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Current IG OAS: {df['ig_oas_raw'].dropna().iloc[-1]:.2f}%")
    print(f"Saved: c2_ig_spread.csv")

    return df


# =============================================================================
# Module D: Flow Confirmation
# =============================================================================

# iShares ETF configuration
ISHARES_ETFS = {
    'HYG': {
        'fund_id': '239565',
        'slug': 'ishares-iboxx-high-yield-corporate-bond-etf',
        'cache_file': 'd1_hyg_flow.csv',
        'shares_col': 'hyg_shares',
    },
    'LQD': {
        'fund_id': '239566',
        'slug': 'ishares-iboxx-investment-grade-corporate-bond-etf',
        'cache_file': 'd2_lqd_flow.csv',
        'shares_col': 'lqd_shares',
    },
    'TLT': {
        'fund_id': '239454',
        'slug': 'ishares-20-year-treasury-bond-etf',
        'cache_file': 'd3_tlt_flow.csv',
        'shares_col': 'tlt_shares',
    },
}


def fetch_ishares_shares_outstanding(ticker: str) -> dict:
    """
    Fetch current shares outstanding from iShares website.

    Args:
        ticker: ETF ticker (HYG, LQD, TLT)

    Returns:
        dict with 'date' and 'shares', or None if failed
    """
    if ticker not in ISHARES_ETFS:
        print(f"  Unknown ticker: {ticker}")
        return None

    config = ISHARES_ETFS[ticker]
    url = f"https://www.ishares.com/us/products/{config['fund_id']}/{config['slug']}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code} for {ticker}")
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text()

        # Pattern: "Shares Outstanding\n\nas of Jan 06, 2026\n\n\n\n266,500,000"
        pattern = r'Shares Outstanding\s+as of ([A-Za-z]+ \d+, \d+)\s+([\d,]+)'
        match = re.search(pattern, text)

        if match:
            date_str = match.group(1)
            shares_str = match.group(2)
            shares = int(shares_str.replace(',', ''))
            return {
                'date': pd.to_datetime(date_str),
                'shares': shares,
            }
        else:
            print(f"  Could not parse shares for {ticker}")
            return None

    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return None


def update_etf_shares(ticker: str) -> bool:
    """
    Update ETF shares outstanding data by appending new data from iShares.

    Args:
        ticker: ETF ticker (HYG, LQD, TLT)

    Returns:
        True if data was updated, False otherwise
    """
    if ticker not in ISHARES_ETFS:
        return False

    config = ISHARES_ETFS[ticker]
    cache_file = os.path.join(OUTPUT_DIR, config['cache_file'])
    shares_col = config['shares_col']

    print(f"\n[Updating {ticker} Shares]")

    # Load existing data
    if os.path.exists(cache_file):
        existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if shares_col in existing.columns:
            shares_data = existing[shares_col].dropna()
            last_date = shares_data.index.max()
            print(f"  Existing data up to: {last_date.strftime('%Y-%m-%d')}")
        else:
            print(f"  No {shares_col} column found")
            return False
    else:
        print(f"  No existing cache file")
        return False

    # Fetch new data from iShares
    new_data = fetch_ishares_shares_outstanding(ticker)
    if not new_data:
        return False

    new_date = new_data['date']
    new_shares = new_data['shares']

    print(f"  iShares data: {new_shares:,} shares as of {new_date.strftime('%Y-%m-%d')}")

    # Check if we need to update
    if new_date <= last_date:
        print(f"  No new data (latest: {last_date.strftime('%Y-%m-%d')})")
        return False

    # Add new row
    existing.loc[new_date, shares_col] = new_shares
    existing = existing.sort_index()

    # Recalculate flow metrics
    shares = existing[shares_col]

    # YoY change (252天, negative = outflow = danger, so flip)
    yoy_pct = shares.pct_change(252) * 100
    flow_signal = -1 * yoy_pct

    # 63天 (3个月) change
    mom_63d = shares.pct_change(63) * 100
    flow_63d = -1 * mom_63d

    prefix = ticker.lower()
    existing[f'{prefix}_flow_yoy'] = flow_signal
    existing[f'{prefix}_flow_3m'] = flow_63d

    # Percentile transforms
    existing[f'{prefix}_flow_pctl_1y'] = compute_percentile(flow_signal, 252)
    existing[f'{prefix}_flow_pctl_5y'] = compute_percentile(flow_signal, 1260, 504)

    # Z-score transforms
    zscore_cols = compute_all_zscores(flow_signal, f'{prefix}_flow')
    for col, series in zscore_cols.items():
        existing[col] = series

    # Save
    existing.to_csv(cache_file)
    print(f"  Added data for {new_date.strftime('%Y-%m-%d')}")
    print(f"  New range: {existing.index.min().strftime('%Y-%m-%d')} to {existing.index.max().strftime('%Y-%m-%d')}")

    return True


def update_all_etf_shares():
    """Update shares outstanding for all ETFs from iShares."""
    print("\n" + "=" * 70)
    print("Updating ETF Shares Outstanding from iShares")
    print("=" * 70)

    for ticker in ISHARES_ETFS:
        update_etf_shares(ticker)


def cache_d1_hyg_flow():
    """
    D1: HYG Flow (主指标)

    iShares高收益债ETF份额变化(取负)
    - 正值 = 资金流出高收益债 = 信用风险偏好下降
    - 投资者逃离垃圾债

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("D1: HYG Flow - 主指标")
    print("=" * 70)

    loader = LQIDataLoader()
    hyg = loader.load_hyg_full()

    if 'Shares' not in hyg.columns:
        print("[HYG] Shares data not available")
        return None

    shares = hyg['Shares']

    # YoY change (252天, negative = outflow = danger, so flip)
    yoy_pct = shares.pct_change(252) * 100
    flow_signal = -1 * yoy_pct

    # 63天 (3个月) change
    mom_63d = shares.pct_change(63) * 100
    flow_63d = -1 * mom_63d

    df = pd.DataFrame({
        'hyg_shares': shares,
        'hyg_flow_yoy': flow_signal,
        'hyg_flow_3m': flow_63d,
    })

    # Percentile transforms
    df['hyg_flow_pctl_1y'] = compute_percentile(flow_signal, 252)
    df['hyg_flow_pctl_5y'] = compute_percentile(flow_signal, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(flow_signal, 'hyg_flow')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'd1_hyg_flow.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Saved: d1_hyg_flow.csv")

    return df


def cache_d2_lqd_flow():
    """
    D2: LQD Flow (辅指标)

    iShares投资级债ETF份额变化(取负)
    - 正值 = 资金流出IG债
    - 连投资级债券都被抛售，避险情绪蔓延到高质量资产

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("D2: LQD Flow - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()
    lqd = loader.load_lqd_full()

    if 'Shares' not in lqd.columns:
        print("[LQD] Shares data not available")
        return None

    shares = lqd['Shares']

    yoy_pct = shares.pct_change(252) * 100
    flow_signal = -1 * yoy_pct

    mom_63d = shares.pct_change(63) * 100
    flow_63d = -1 * mom_63d

    df = pd.DataFrame({
        'lqd_shares': shares,
        'lqd_flow_yoy': flow_signal,
        'lqd_flow_3m': flow_63d,
    })

    # Percentile transforms
    df['lqd_flow_pctl_1y'] = compute_percentile(flow_signal, 252)
    df['lqd_flow_pctl_5y'] = compute_percentile(flow_signal, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(flow_signal, 'lqd_flow')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'd2_lqd_flow.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Saved: d2_lqd_flow.csv")

    return df


def cache_d3_tlt_flow():
    """
    D3: TLT Flow (辅指标)

    iShares长期国债ETF份额变化(取负)
    - 正值 = 资金流出长债
    - Flight-to-Safety逆转，或利率上行预期导致久期风险规避

    数据频率: 日频
    发布滞后: T+1
    """
    print("\n" + "=" * 70)
    print("D3: TLT Flow - 辅指标")
    print("=" * 70)

    loader = LQIDataLoader()
    tlt = loader.load_tlt_full()

    if 'Shares' not in tlt.columns:
        print("[TLT] Shares data not available")
        return None

    shares = tlt['Shares']

    yoy_pct = shares.pct_change(252) * 100
    flow_signal = -1 * yoy_pct

    mom_63d = shares.pct_change(63) * 100
    flow_63d = -1 * mom_63d

    df = pd.DataFrame({
        'tlt_shares': shares,
        'tlt_flow_yoy': flow_signal,
        'tlt_flow_3m': flow_63d,
    })

    # Percentile transforms
    df['tlt_flow_pctl_1y'] = compute_percentile(flow_signal, 252)
    df['tlt_flow_pctl_5y'] = compute_percentile(flow_signal, 1260, 504)

    # Z-score transforms (3m, 1y, 3y windows + deltas)
    zscore_cols = compute_all_zscores(flow_signal, 'tlt_flow')
    for col, series in zscore_cols.items():
        df[col] = series

    df.index.name = 'date'
    df.to_csv(os.path.join(OUTPUT_DIR, 'd3_tlt_flow.csv'))
    print(f"Range: {df.index.min().date()} to {df.index.max().date()}")
    print(f"Total rows: {len(df)}")
    print(f"Saved: d3_tlt_flow.csv")

    return df


# =============================================================================
# Summary
# =============================================================================

def generate_summary():
    """Generate summary of cached data"""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # 只统计 a/b/c/d 开头的文件
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv') and f[0] in 'abcd']

    summary = []
    for f in sorted(files):
        filepath = os.path.join(OUTPUT_DIR, f)
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        summary.append({
            'file': f,
            'rows': len(df),
            'cols': len(df.columns),
            'start': df.index.min().strftime('%Y-%m-%d') if len(df) > 0 else 'N/A',
            'end': df.index.max().strftime('%Y-%m-%d') if len(df) > 0 else 'N/A',
        })

    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))

    # Save summary
    summary_df.to_csv(os.path.join(OUTPUT_DIR, '_factor_summary.csv'), index=False)

    return summary_df


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Cache Trend Factors')
    parser.add_argument('--update-etf', action='store_true',
                        help='Update ETF shares from iShares (append new data)')
    parser.add_argument('--update-all', action='store_true',
                        help='Update all trend factors (FRED/Yahoo + ETF shares)')
    parser.add_argument('--refresh', action='store_true',
                        help='Full refresh of all cached data')
    args = parser.parse_args()

    print("=" * 70)
    print("Cache All Trend Factors (v2)")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if args.update_etf:
        # Only update ETF shares from iShares
        update_all_etf_shares()
        generate_summary()
        print("\n" + "=" * 70)
        print("ETF SHARES UPDATE COMPLETE")
        print("=" * 70)
        return

    if args.update_all:
        # Update all: FRED/Yahoo factors + ETF shares
        # Module A-C: These pull fresh data from FRED/Yahoo
        print("\n" + "=" * 70)
        print("MODULE A: VOLATILITY REGIME")
        print("=" * 70)
        cache_a1_vts()
        cache_a2_skew()
        cache_a3_move()

        print("\n" + "=" * 70)
        print("MODULE B: FUNDING / LIQUIDITY STRESS")
        print("=" * 70)
        cache_b1_funding()
        cache_b2_gcf_iorb()

        print("\n" + "=" * 70)
        print("MODULE C: CREDIT COMPENSATION")
        print("=" * 70)
        cache_c1_hy_spread()
        cache_c2_ig_spread()

        # Module D: Update ETF shares from iShares
        update_all_etf_shares()

        generate_summary()
        print("\n" + "=" * 70)
        print("ALL TREND FACTORS UPDATE COMPLETE")
        print("=" * 70)
        return

    # Default: Full refresh (original behavior)
    # Module A: Volatility Regime
    print("\n" + "=" * 70)
    print("MODULE A: VOLATILITY REGIME")
    print("=" * 70)
    cache_a1_vts()
    cache_a2_skew()
    cache_a3_move()

    # Module B: Funding / Liquidity Stress
    print("\n" + "=" * 70)
    print("MODULE B: FUNDING / LIQUIDITY STRESS")
    print("=" * 70)
    cache_b1_funding()
    cache_b2_gcf_iorb()

    # Module C: Credit Compensation
    print("\n" + "=" * 70)
    print("MODULE C: CREDIT COMPENSATION")
    print("=" * 70)
    cache_c1_hy_spread()
    cache_c2_ig_spread()

    # Module D: Flow Confirmation
    print("\n" + "=" * 70)
    print("MODULE D: FLOW CONFIRMATION")
    print("=" * 70)
    cache_d1_hyg_flow()
    cache_d2_lqd_flow()
    cache_d3_tlt_flow()

    # Summary
    generate_summary()

    print("\n" + "=" * 70)
    print("CACHING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
