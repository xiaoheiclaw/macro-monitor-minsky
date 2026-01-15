"""
Unified Data Loader
===================

Centralized data loading for all indicator system layers:
- Structure factors (V1-V9)
- Trend factors (Module A-D)
- Market data (SPX, Fed Funds)

Features:
- In-memory caching
- Release lag support (--generate-lagged)
- FRED API integration
- Yahoo Finance integration for Trend data

Usage:
    from data.loader import DataLoader

    loader = DataLoader()
    factors = loader.load_structure_factors(use_lagged=True)
    spx = loader.load_spx()

CLI:
    python -m data.loader                  # Load from cache
    python -m data.loader --refresh        # Re-download all
    python -m data.loader --generate-lagged # Generate lagged data
"""

import os
import sys
import argparse
import warnings
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    FRED_API_KEY,
    PROJECT_ROOT,
    RAW_DIR,
    LAGGED_DIR,
    TREND_DATA_DIR,
    RELEASE_LAG,
    FACTOR_FILES,
)


class DataLoader:
    """
    Unified data loader for the indicator system.

    Handles:
    - Structure layer factors (V1-V9) with optional release lag
    - Trend layer factors (Module A-D)
    - Market data (SPX, Fed Funds Rate)
    """

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure data directories exist."""
        os.makedirs(RAW_DIR, exist_ok=True)
        os.makedirs(LAGGED_DIR, exist_ok=True)

    def clear_cache(self):
        """Clear in-memory cache."""
        self._cache.clear()

    # =========================================================================
    # Structure Layer: Factor Loading
    # =========================================================================

    def load_structure_factors(self, use_lagged: bool = True) -> pd.DataFrame:
        """
        Load all Structure layer factors.

        Args:
            use_lagged: If True, load lagged data; otherwise load raw data.

        Returns:
            DataFrame with columns for each factor value.
        """
        cache_key = f'structure_factors_{"lagged" if use_lagged else "raw"}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        data_dir = LAGGED_DIR if use_lagged else RAW_DIR
        factors = {}

        print(f"\n{'=' * 60}")
        print(f"Loading All Factors from {os.path.basename(data_dir)}/")
        print("=" * 60)

        for factor_name, (filename, value_col) in FACTOR_FILES.items():
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                print(f"  {factor_name}: Missing")
                continue

            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            series = df[value_col] if value_col in df.columns else df.iloc[:, 0]
            series = series[~series.index.duplicated(keep='last')]
            series = series.resample('ME').last().ffill()

            lag_info = f" (lag={RELEASE_LAG.get(factor_name, 0)}m)" if use_lagged else ""
            print(f"  {factor_name}: Loaded{lag_info}")

            factors[factor_name] = series

        result = pd.DataFrame(factors)

        print(f"\n  Loaded {len(factors)} factors")
        if len(result) > 0:
            print(f"  Date range: {result.index.min()} to {result.index.max()}")
            print(f"  Shape: {result.shape}")

        self._cache[cache_key] = result
        return result

    def load_factor(self, factor_name: str, use_lagged: bool = True) -> pd.DataFrame:
        """
        Load a single factor's full DataFrame.

        Args:
            factor_name: Factor name (V1-V9)
            use_lagged: If True, load lagged data.

        Returns:
            Full DataFrame for the factor.
        """
        cache_key = f'factor_{factor_name}_{"lagged" if use_lagged else "raw"}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        if factor_name not in FACTOR_FILES:
            raise ValueError(f"Unknown factor: {factor_name}")

        filename, _ = FACTOR_FILES[factor_name]
        data_dir = LAGGED_DIR if use_lagged else RAW_DIR
        filepath = os.path.join(data_dir, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Factor file not found: {filepath}")

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        self._cache[cache_key] = df
        return df

    # =========================================================================
    # Market Data
    # =========================================================================

    def load_spx(self, use_lagged: bool = True) -> pd.Series:
        """
        Load S&P 500 data.

        Returns:
            Series of SPX close prices.
        """
        cache_key = f'spx_{"lagged" if use_lagged else "raw"}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        data_dir = LAGGED_DIR if use_lagged else RAW_DIR
        filepath = os.path.join(data_dir, 'spx.csv')

        if not os.path.exists(filepath):
            # Try raw dir as fallback
            filepath = os.path.join(RAW_DIR, 'spx.csv')

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"SPX data not found: {filepath}")

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        series = df['close'] if 'close' in df.columns else df.iloc[:, 0]

        self._cache[cache_key] = series
        return series

    def load_fed_funds(self, use_lagged: bool = True) -> pd.Series:
        """
        Load Federal Funds Effective Rate.

        Returns:
            Series of Fed Funds rates.
        """
        cache_key = f'fed_funds_{"lagged" if use_lagged else "raw"}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        data_dir = LAGGED_DIR if use_lagged else RAW_DIR
        filepath = os.path.join(data_dir, 'fed_funds.csv')

        if not os.path.exists(filepath):
            filepath = os.path.join(RAW_DIR, 'fed_funds.csv')

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fed Funds data not found: {filepath}")

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        series = df['rate'] if 'rate' in df.columns else df.iloc[:, 0]

        self._cache[cache_key] = series
        return series

    # =========================================================================
    # Trend Layer: Factor Loading
    # =========================================================================

    def load_trend_factors(self) -> Dict[str, pd.DataFrame]:
        """
        Load all Trend layer factors.

        Returns:
            Dict mapping factor names to DataFrames.
        """
        if 'trend_factors' in self._cache:
            return self._cache['trend_factors']

        # Trend data file mapping (from trend/trend_score/config.py)
        TREND_DATA_FILES = {
            # Module A: Volatility
            'VIX': 'a_vix.csv',
            'VIX_TERM': 'a_vix_term.csv',
            'SKEW': 'a_skew.csv',
            'MOVE': 'a_move.csv',
            # Module B: Funding/Liquidity
            'EFFR_SOFR': 'b_effr_sofr_spread.csv',
            'GCF_REPO': 'b_gcf_repo_rate.csv',
            # Module C: Credit
            'HY_SPREAD': 'c_hy_spread.csv',
            'IG_SPREAD': 'c_ig_spread.csv',
            # Module D: Flow
            'HYG_FLOW': 'd_hyg_flow.csv',
            'LQD_FLOW': 'd_lqd_flow.csv',
            'TLT_FLOW': 'd_tlt_flow.csv',
        }

        factors = {}
        for factor_name, filename in TREND_DATA_FILES.items():
            filepath = os.path.join(TREND_DATA_DIR, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                    factors[factor_name] = df
                except Exception as e:
                    print(f"  Warning: Failed to load {factor_name}: {e}")

        self._cache['trend_factors'] = factors
        return factors

    def load_trend_factor(self, factor_name: str) -> pd.DataFrame:
        """
        Load a single Trend factor.

        Args:
            factor_name: Factor name (e.g., 'VIX', 'HY_SPREAD')

        Returns:
            DataFrame for the factor.
        """
        factors = self.load_trend_factors()
        if factor_name not in factors:
            raise ValueError(f"Unknown trend factor: {factor_name}")
        return factors[factor_name]

    # =========================================================================
    # Release Lag Functions
    # =========================================================================

    @staticmethod
    def apply_release_lag(df: pd.DataFrame, factor_name: str) -> pd.DataFrame:
        """
        Apply publication delay to factor data.

        Simulates "data available at decision time" by shifting dates forward.

        Example:
            V4 ICR has 6-month lag: 2024-03-31 data available at 2024-09-30

        Args:
            df: Factor data (index=date)
            factor_name: Factor name (V1-V9)

        Returns:
            Lag-adjusted DataFrame.
        """
        lag_months = RELEASE_LAG.get(factor_name, 0)

        if lag_months == 0:
            return df

        df_lagged = df.copy()
        df_lagged.index = df_lagged.index + pd.DateOffset(months=lag_months)

        return df_lagged

    def generate_lagged_data(self):
        """
        Generate lagged versions of all factor files.

        Reads from raw/, applies release lag, saves to lagged/.
        """
        print("\n" + "=" * 60)
        print("Generating Lagged Data")
        print("=" * 60)

        self._ensure_dirs()

        # Factor files
        files = {
            'V1': 'V1_st_debt.csv',
            'V2': 'V2_uninsured_deposits.csv',
            'V4': 'V4_icr.csv',
            'V5': 'V5_tdsp.csv',
            'V7': 'V7_cape.csv',
            'V8': 'V8_margin_debt.csv',
            'V9': 'V9_cre_lending.csv',
            'spx': 'spx.csv',
            'fed_funds': 'fed_funds.csv',
        }

        for name, filename in files.items():
            raw_path = os.path.join(RAW_DIR, filename)
            if not os.path.exists(raw_path):
                print(f"  {name}: Missing raw data")
                continue

            df = pd.read_csv(raw_path, index_col=0, parse_dates=True)

            # Apply lag for factor data (not SPX/Fed Funds)
            if name.startswith('V'):
                df_lagged = self.apply_release_lag(df, name)
                lag = RELEASE_LAG.get(name, 0)
                print(f"  {name}: Applied {lag}m lag")
            else:
                df_lagged = df
                print(f"  {name}: No lag (copied)")

            # Save to lagged/
            lagged_path = os.path.join(LAGGED_DIR, filename)
            df_lagged.to_csv(lagged_path)

        print("\n" + "=" * 60)
        print(f"DONE - Lagged data saved to: {LAGGED_DIR}")
        print("=" * 60)

    # =========================================================================
    # Data Download (FRED)
    # =========================================================================

    def _get_fred_series(self, series_id: str) -> pd.Series:
        """Download a series from FRED."""
        from fredapi import Fred
        fred = Fred(api_key=FRED_API_KEY)
        return fred.get_series(series_id)

    def _save_factor(self, df: pd.DataFrame, filename: str, subdir: str = 'raw'):
        """Save factor data to CSV."""
        if subdir == 'raw':
            filepath = os.path.join(RAW_DIR, filename)
        elif subdir == 'lagged':
            filepath = os.path.join(LAGGED_DIR, filename)
        else:
            filepath = os.path.join(PROJECT_ROOT, 'structure', 'data', filename)
        df.to_csv(filepath)
        print(f"  Saved: {filepath}")

    # =========================================================================
    # CAPE Download (from multpl.com)
    # =========================================================================

    def _download_cape_from_multpl(self) -> pd.DataFrame:
        """
        Download Shiller CAPE data from multpl.com.

        Note: The first row shows today's date (e.g., "Jan 6, 2026") as real-time data.
        Only month-end rows (e.g., "Dec 1, 2025") are historical confirmed data.
        We normalize all dates to month-end format for consistency.
        """
        url = 'https://www.multpl.com/shiller-pe/table/by-month'
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'datatable'})

        if not table:
            raise ValueError("Could not find CAPE data table on multpl.com")

        rows = table.find_all('tr')
        data = []

        for row in rows[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 2:
                date_str = cols[0].text.strip()
                value_str = cols[1].text.strip()
                try:
                    # Parse date (handles both "Jan 6, 2026" and "Dec 1, 2025" formats)
                    parsed_date = pd.to_datetime(date_str, format='%b %d, %Y')
                    # Normalize to month-end
                    month_end = parsed_date + pd.offsets.MonthEnd(0)
                    value = float(value_str)
                    data.append({'date': month_end, 'cape': value})
                except (ValueError, TypeError):
                    continue

        if not data:
            raise ValueError("No valid CAPE data parsed from multpl.com")

        df = pd.DataFrame(data)
        df = df.drop_duplicates(subset='date', keep='first')  # Keep latest value for current month
        df = df.set_index('date').sort_index()
        df.index.name = 'date'

        print(f"  Downloaded {len(df)} months of CAPE data")
        print(f"  Date range: {df.index.min().strftime('%Y-%m')} to {df.index.max().strftime('%Y-%m')}")

        return df

    def update_cape_data(self) -> bool:
        """
        Update CAPE data by appending new months from multpl.com.

        Returns:
            True if data was updated, False otherwise.
        """
        print("\n[Updating V7: Shiller CAPE]")

        cape_file = os.path.join(RAW_DIR, 'V7_cape.csv')

        # Load existing data
        if os.path.exists(cape_file):
            existing = pd.read_csv(cape_file, index_col=0, parse_dates=True)
            last_date = existing.index.max()
            print(f"  Existing data up to: {last_date.strftime('%Y-%m')}")
        else:
            existing = pd.DataFrame()
            last_date = pd.Timestamp('1900-01-01')
            print("  No existing data, will download full history")

        # Download new data
        try:
            new_data = self._download_cape_from_multpl()
        except Exception as e:
            print(f"  Error downloading CAPE: {e}")
            return False

        # Include all months up to current month (current month uses real-time value)
        # The current month's value will be updated each time until month-end when it becomes final
        new_months = new_data[new_data.index > last_date]

        if len(new_months) == 0:
            print("  No new months to add")
            return False

        # Append new data
        combined = pd.concat([existing, new_months])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()

        # Save
        combined.to_csv(cape_file)
        print(f"  Added {len(new_months)} new months")
        print(f"  New date range: {combined.index.min().strftime('%Y-%m')} to {combined.index.max().strftime('%Y-%m')}")

        return True

    # =========================================================================
    # SPX Download (from Yahoo Finance)
    # =========================================================================

    def _download_spx_from_yahoo(self, start_date: str = '1980-01-01') -> pd.DataFrame:
        """
        Download S&P 500 daily data from Yahoo Finance.

        Args:
            start_date: Start date for download (YYYY-MM-DD format)

        Returns:
            DataFrame with OHLC data.
        """
        import yfinance as yf

        print(f"  Downloading SPX from Yahoo Finance (from {start_date})...")

        df = yf.download('^GSPC', start=start_date, progress=False)

        if df.empty:
            raise ValueError("No SPX data returned from Yahoo Finance")

        # Handle multi-level columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Standardize column names
        df.columns = [c.lower() for c in df.columns]

        # Keep only OHLC columns
        cols_to_keep = ['open', 'high', 'low', 'close']
        df = df[[c for c in cols_to_keep if c in df.columns]]

        df.index.name = 'date'

        print(f"  Downloaded {len(df)} days of SPX data")
        print(f"  Date range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")

        return df

    def update_spx_data(self) -> bool:
        """
        Update SPX data by appending new daily rows from Yahoo Finance.

        Returns:
            True if data was updated, False otherwise.
        """
        print("\n[Updating SPX: S&P 500]")

        spx_file = os.path.join(RAW_DIR, 'spx.csv')

        # Load existing data
        if os.path.exists(spx_file):
            existing = pd.read_csv(spx_file, index_col=0, parse_dates=True)
            last_date = existing.index.max()
            print(f"  Existing data up to: {last_date.strftime('%Y-%m-%d')}")
        else:
            existing = pd.DataFrame()
            last_date = pd.Timestamp('1980-01-01')
            print("  No existing data, will download full history")

        # Download new data (start from day after last date)
        start_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')

        try:
            new_data = self._download_spx_from_yahoo(start_date=start_date)
        except Exception as e:
            print(f"  Error downloading SPX: {e}")
            return False

        if len(new_data) == 0:
            print("  No new days to add")
            return False

        # Filter to only new days
        new_days = new_data[new_data.index > last_date]

        if len(new_days) == 0:
            print("  No new days to add")
            return False

        # Append new data
        combined = pd.concat([existing, new_days])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()

        # Save
        combined.to_csv(spx_file)
        print(f"  Added {len(new_days)} new days")
        print(f"  New date range: {combined.index.min().strftime('%Y-%m-%d')} to {combined.index.max().strftime('%Y-%m-%d')}")

        return True

    def download_all_structure_factors(self):
        """Download all Structure layer factors from FRED."""
        print("=" * 60)
        print("Downloading All Structure Factor Data")
        print("=" * 60)

        self._ensure_dirs()

        # V1: ST Debt Ratio
        print("\n[V1: ST Debt Ratio]")
        print("  Downloading BOGZ1FL104140006Q...")
        st_debt = self._get_fred_series('BOGZ1FL104140006Q')
        df = pd.DataFrame({'st_debt': st_debt})
        df.index.name = 'date'
        self._save_factor(df, 'V1_st_debt.csv')

        # V2: Uninsured Deposits
        print("\n[V2: Uninsured Deposits]")
        print("  Downloading BOGZ1FL763139105Q...")
        uninsured = self._get_fred_series('BOGZ1FL763139105Q')
        print("  Downloading BOGZ1FL763130005Q...")
        time_savings = self._get_fred_series('BOGZ1FL763130005Q')
        ratio = (uninsured / time_savings * 100)
        df = pd.DataFrame({'uninsured': uninsured, 'time_savings': time_savings, 'ratio': ratio})
        df.index.name = 'date'
        self._save_factor(df, 'V2_uninsured_deposits.csv')

        # V4: Interest Coverage Ratio
        print("\n[V4: Interest Coverage Ratio]")
        print("  Downloading A464RC1Q027SBEA...")
        profit = self._get_fred_series('A464RC1Q027SBEA')
        print("  Downloading B471RC1Q027SBEA...")
        interest = self._get_fred_series('B471RC1Q027SBEA')
        icr = profit / interest
        df = pd.DataFrame({'profit': profit, 'interest': interest, 'icr': icr})
        df.index.name = 'date'
        self._save_factor(df, 'V4_icr.csv')

        # V5: TDSP
        print("\n[V5: TDSP]")
        print("  Downloading TDSP...")
        tdsp = self._get_fred_series('TDSP')
        df = pd.DataFrame({'tdsp': tdsp})
        df.index.name = 'date'
        self._save_factor(df, 'V5_tdsp.csv')

        # V7: CAPE (from multpl.com)
        print("\n[V7: Shiller CAPE]")
        try:
            df = self._download_cape_from_multpl()
            self._save_factor(df, 'V7_cape.csv')
        except Exception as e:
            print(f"  Warning: Failed to fetch CAPE from web: {e}")

        # V8: Margin Debt / Market Cap
        print("\n[V8: Margin Debt / Market Cap]")
        print("  Downloading BOGZ1FL663067003Q...")
        margin = self._get_fred_series('BOGZ1FL663067003Q')
        print("  Downloading BOGZ1FL893064105Q...")
        mktcap = self._get_fred_series('BOGZ1FL893064105Q')
        ratio = margin / mktcap * 100
        df = pd.DataFrame({'margin': margin, 'mktcap': mktcap, 'ratio': ratio})
        df.index.name = 'date'
        self._save_factor(df, 'V8_margin_debt.csv')

        # V9: CRE Lending Standards
        print("\n[V9: CRE Lending Standards]")
        print("  Downloading DRTSCLCC...")
        clcc = self._get_fred_series('DRTSCLCC')
        print("  Downloading DRTSCILM...")
        cilm = self._get_fred_series('DRTSCILM')
        print("  Downloading DRTSCIS...")
        cis = self._get_fred_series('DRTSCIS')
        df_temp = pd.DataFrame({'clcc': clcc, 'cilm': cilm, 'cis': cis})
        avg = df_temp.mean(axis=1)
        df = pd.DataFrame({'clcc': clcc, 'cilm': cilm, 'cis': cis, 'avg': avg})
        df.index.name = 'date'
        self._save_factor(df, 'V9_cre_lending.csv')

        # Fed Funds
        print("\n[Fed Funds Rate]")
        print("  Downloading FEDFUNDS...")
        ffr = self._get_fred_series('FEDFUNDS')
        df = pd.DataFrame({'rate': ffr})
        df.index.name = 'date'
        self._save_factor(df, 'fed_funds.csv')

        # SPX (from Yahoo Finance)
        print("\n[SPX: S&P 500]")
        try:
            df = self._download_spx_from_yahoo(start_date='1980-01-01')
            self._save_factor(df, 'spx.csv')
        except Exception as e:
            print(f"  Warning: Failed to fetch SPX from Yahoo: {e}")

        print("\n" + "=" * 60)
        print(f"DONE - All data saved to: {RAW_DIR}")
        print("=" * 60)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Unified Data Loader')
    parser.add_argument('--refresh', action='store_true',
                        help='Re-download all data from sources')
    parser.add_argument('--generate-lagged', action='store_true',
                        help='Generate lagged data files from raw')
    parser.add_argument('--update-cape', action='store_true',
                        help='Update CAPE data from multpl.com (append new months)')
    parser.add_argument('--update-spx', action='store_true',
                        help='Update SPX data from Yahoo Finance (append new days)')
    parser.add_argument('--update-market', action='store_true',
                        help='Update both CAPE and SPX data')
    args = parser.parse_args()

    loader = DataLoader()

    if args.update_cape:
        loader.update_cape_data()
        loader.generate_lagged_data()
    elif args.update_spx:
        loader.update_spx_data()
        loader.generate_lagged_data()
    elif args.update_market:
        loader.update_cape_data()
        loader.update_spx_data()
        loader.generate_lagged_data()
    elif args.refresh:
        loader.download_all_structure_factors()
        loader.generate_lagged_data()
    elif args.generate_lagged:
        loader.generate_lagged_data()
    else:
        # Check if data exists
        test_file = os.path.join(RAW_DIR, 'V1_st_debt.csv')
        if not os.path.exists(test_file):
            print("No cached data found. Run with --refresh to download.")
            return

        print("Loading cached Structure factors (lagged)...")
        factors = loader.load_structure_factors(use_lagged=True)
        print(f"\nLoaded {len(factors.columns)} factors")

        print("\nLoading SPX...")
        try:
            spx = loader.load_spx()
            print(f"  SPX: {len(spx)} rows")
        except FileNotFoundError:
            print("  SPX: Not found")


if __name__ == '__main__':
    main()
