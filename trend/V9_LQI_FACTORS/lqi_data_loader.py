"""
LQI Data Loader - 市场数据加载器
================================

从 Yahoo Finance 和 FRED 加载 Trend 层需要的各种市场数据。

数据源:
- Yahoo Finance: VIX, VIX3M, SKEW, ETF prices/shares
- FRED: EFFR, SOFR, Treasury yields, Credit spreads
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

try:
    import yfinance as yf
except ImportError:
    yf = None
    print("Warning: yfinance not installed. Some data sources unavailable.")

try:
    from fredapi import Fred
    # Use the project's FRED API key from config, with env override
    FRED_API_KEY = os.environ.get('FRED_API_KEY', 'd80e78bc5adcf35b76e7cde9d2f4e4b7')
    fred = Fred(api_key=FRED_API_KEY)
except ImportError:
    fred = None
    print("Warning: fredapi not installed. Some data sources unavailable.")


class LQIDataLoader:
    """市场流动性和风险指标数据加载器"""

    def __init__(self, start_date: str = '1990-01-01'):
        self.start_date = start_date
        self.cache = {}

    def _fetch_yahoo(self, ticker: str, col: str = 'Close') -> pd.Series:
        """从 Yahoo Finance 获取数据"""
        if yf is None:
            return pd.Series(dtype=float)

        cache_key = f'yahoo_{ticker}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            data = yf.download(ticker, start=self.start_date, progress=False)
            if len(data) > 0:
                series = data[col].squeeze()
                series.index = pd.to_datetime(series.index)
                series.name = ticker
                self.cache[cache_key] = series
                return series
        except Exception as e:
            print(f"  Warning: Failed to fetch {ticker} from Yahoo: {e}")

        return pd.Series(dtype=float)

    def _fetch_fred(self, series_id: str) -> pd.Series:
        """从 FRED 获取数据"""
        if fred is None:
            return pd.Series(dtype=float)

        cache_key = f'fred_{series_id}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            data = fred.get_series(series_id, observation_start=self.start_date)
            if data is not None and len(data) > 0:
                data.index = pd.to_datetime(data.index)
                data.name = series_id
                self.cache[cache_key] = data
                return data
        except Exception as e:
            print(f"  Warning: Failed to fetch {series_id} from FRED: {e}")

        return pd.Series(dtype=float)

    # =========================================================================
    # Module A: Volatility
    # =========================================================================

    def load_vix(self) -> pd.Series:
        """VIX Index - prefer FRED (VIXCLS), fallback to Yahoo"""
        # FRED has daily VIX data (VIXCLS)
        vix = self._fetch_fred('VIXCLS')
        if len(vix) > 0:
            return vix
        # Fallback to Yahoo
        return self._fetch_yahoo('^VIX')

    def load_vix3m(self) -> pd.Series:
        """VIX 3-Month - prefer FRED (VXVCLS), fallback to Yahoo"""
        # FRED has VIX3M data (VXVCLS)
        vix3m = self._fetch_fred('VXVCLS')
        if len(vix3m) > 0:
            return vix3m
        # Fallback to Yahoo
        return self._fetch_yahoo('^VIX3M')

    def load_skew(self) -> pd.Series:
        """CBOE SKEW Index - prefer FRED (SKEW), fallback to Yahoo"""
        # FRED has SKEW data
        skew = self._fetch_fred('SKEW')
        if len(skew) > 0:
            return skew
        # Fallback to Yahoo
        return self._fetch_yahoo('^SKEW')

    def load_move(self) -> pd.Series:
        """MOVE Index - ICE BofAML MOVE Index from Yahoo (^MOVE)"""
        return self._fetch_yahoo('^MOVE')

    # =========================================================================
    # Module B: Funding / Liquidity
    # =========================================================================

    def load_effr(self) -> pd.Series:
        """Effective Federal Funds Rate"""
        return self._fetch_fred('EFFR')

    def load_sofr(self) -> pd.Series:
        """Secured Overnight Financing Rate"""
        return self._fetch_fred('SOFR')

    def load_ted_spread(self) -> pd.Series:
        """TED Spread (3M LIBOR - 3M T-Bill)"""
        # TED Spread 在 FRED 上已停止更新，使用 EFFR-SOFR spread 作为替代
        effr = self.load_effr()
        sofr = self.load_sofr()
        if len(effr) > 0 and len(sofr) > 0:
            spread = effr - sofr
            spread.name = 'EFFR_SOFR_spread'
            return spread.dropna()
        return pd.Series(dtype=float)

    def load_gcf_repo(self) -> pd.Series:
        """GCF Repo Rate - Tri-Party General Collateral Rate"""
        # Try multiple FRED series for repo rates
        # RRPONTSYD: Overnight Reverse Repo Rate
        # SOFR: Secured Overnight Financing Rate (broader repo market)
        for series_id in ['RRPONTSYD', 'SOFR']:
            gcf = self._fetch_fred(series_id)
            if len(gcf) > 0:
                gcf.name = 'GCF_Repo'
                return gcf
        return pd.Series(dtype=float)

    def load_gcf_repo_full(self) -> pd.DataFrame:
        """GCF Repo Rate - 返回完整 DataFrame 包含 Treasury_Rate"""
        gcf = self.load_gcf_repo()
        if len(gcf) > 0:
            df = pd.DataFrame({'Treasury_Rate': gcf})
            return df
        return pd.DataFrame(columns=['Treasury_Rate'])

    def load_iorb(self) -> pd.Series:
        """Interest on Reserve Balances"""
        return self._fetch_fred('IORB')

    def load_3m_tbill(self) -> pd.Series:
        """3-Month Treasury Bill Rate"""
        return self._fetch_fred('DTB3')

    # =========================================================================
    # Module C: Credit
    # =========================================================================

    def load_hy_oas(self) -> pd.Series:
        """High Yield OAS (Option-Adjusted Spread)"""
        return self._fetch_fred('BAMLH0A0HYM2')

    def load_ig_oas(self) -> pd.Series:
        """Investment Grade OAS"""
        return self._fetch_fred('BAMLC0A0CM')

    def load_10y_yield(self) -> pd.Series:
        """10-Year Treasury Yield"""
        return self._fetch_fred('DGS10')

    def load_hy_spread(self) -> pd.Series:
        """HY Yield - 10Y Treasury"""
        hy = self.load_hy_oas()
        t10 = self.load_10y_yield()
        if len(hy) > 0 and len(t10) > 0:
            # HY OAS 已经是相对于国债的利差，直接返回
            return hy
        return pd.Series(dtype=float)

    def load_ig_spread(self) -> pd.Series:
        """IG Yield - 10Y Treasury"""
        ig = self.load_ig_oas()
        if len(ig) > 0:
            return ig
        return pd.Series(dtype=float)

    # =========================================================================
    # Module D: Flow (从本地缓存文件读取历史数据)
    # =========================================================================

    def _load_etf_from_cache(self, filename: str) -> pd.DataFrame:
        """从本地缓存文件加载 ETF 数据"""
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_path = os.path.join(data_dir, 'data', filename)

        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
        return pd.DataFrame()

    def load_hyg_shares(self) -> pd.Series:
        """HYG ETF Shares Outstanding - 从缓存文件读取"""
        df = self._load_etf_from_cache('d1_hyg_flow.csv')
        if 'hyg_shares' in df.columns:
            return df['hyg_shares']
        return pd.Series(dtype=float)

    def load_lqd_shares(self) -> pd.Series:
        """LQD ETF Shares Outstanding - 从缓存文件读取"""
        df = self._load_etf_from_cache('d2_lqd_flow.csv')
        if 'lqd_shares' in df.columns:
            return df['lqd_shares']
        return pd.Series(dtype=float)

    def load_tlt_shares(self) -> pd.Series:
        """TLT ETF Shares Outstanding - 从缓存文件读取"""
        df = self._load_etf_from_cache('d3_tlt_flow.csv')
        if 'tlt_shares' in df.columns:
            return df['tlt_shares']
        return pd.Series(dtype=float)

    def load_hyg_price(self) -> pd.Series:
        """HYG ETF Price"""
        return self._fetch_yahoo('HYG')

    def load_lqd_price(self) -> pd.Series:
        """LQD ETF Price"""
        return self._fetch_yahoo('LQD')

    def load_tlt_price(self) -> pd.Series:
        """TLT ETF Price"""
        return self._fetch_yahoo('TLT')

    def load_hyg_full(self) -> pd.DataFrame:
        """HYG ETF - 返回完整 DataFrame 包含 Shares"""
        df = self._load_etf_from_cache('d1_hyg_flow.csv')
        if 'hyg_shares' in df.columns:
            return pd.DataFrame({'Shares': df['hyg_shares']})
        return pd.DataFrame(columns=['Shares'])

    def load_lqd_full(self) -> pd.DataFrame:
        """LQD ETF - 返回完整 DataFrame 包含 Shares"""
        df = self._load_etf_from_cache('d2_lqd_flow.csv')
        if 'lqd_shares' in df.columns:
            return pd.DataFrame({'Shares': df['lqd_shares']})
        return pd.DataFrame(columns=['Shares'])

    def load_tlt_full(self) -> pd.DataFrame:
        """TLT ETF - 返回完整 DataFrame 包含 Shares"""
        df = self._load_etf_from_cache('d3_tlt_flow.csv')
        if 'tlt_shares' in df.columns:
            return pd.DataFrame({'Shares': df['tlt_shares']})
        return pd.DataFrame(columns=['Shares'])

    def load_us_10y_yield(self) -> pd.Series:
        """10-Year Treasury Yield (alias for load_10y_yield)"""
        return self.load_10y_yield()

    # =========================================================================
    # Utilities
    # =========================================================================

    def load_spx(self) -> pd.Series:
        """S&P 500 Index"""
        return self._fetch_yahoo('^GSPC')

    def clear_cache(self):
        """清除缓存"""
        self.cache = {}


# =============================================================================
# Test
# =============================================================================

if __name__ == '__main__':
    print("Testing LQIDataLoader...")
    loader = LQIDataLoader(start_date='2020-01-01')

    print("\n[Module A: Volatility]")
    vix = loader.load_vix()
    print(f"  VIX: {len(vix)} rows, latest: {vix.index.max() if len(vix) > 0 else 'N/A'}")

    vix3m = loader.load_vix3m()
    print(f"  VIX3M: {len(vix3m)} rows, latest: {vix3m.index.max() if len(vix3m) > 0 else 'N/A'}")

    skew = loader.load_skew()
    print(f"  SKEW: {len(skew)} rows, latest: {skew.index.max() if len(skew) > 0 else 'N/A'}")

    print("\n[Module B: Funding]")
    effr = loader.load_effr()
    print(f"  EFFR: {len(effr)} rows, latest: {effr.index.max() if len(effr) > 0 else 'N/A'}")

    print("\n[Module C: Credit]")
    hy = loader.load_hy_oas()
    print(f"  HY OAS: {len(hy)} rows, latest: {hy.index.max() if len(hy) > 0 else 'N/A'}")

    print("\n[Module D: Flow]")
    hyg = loader.load_hyg_price()
    print(f"  HYG: {len(hyg)} rows, latest: {hyg.index.max() if len(hyg) > 0 else 'N/A'}")

    print("\nDone.")
