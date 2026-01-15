#!/usr/bin/env python3
"""Prefect flow for Indicator Data Updates."""

import sys
from pathlib import Path
from datetime import datetime

from prefect import flow, get_run_logger

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from data.loader import DataLoader
from trend.data.cache_all_factors import (
    cache_a1_vts, cache_a2_skew, cache_a3_move,
    cache_b1_funding, cache_b2_gcf_iorb,
    cache_c1_hy_spread, cache_c2_ig_spread,
    update_all_etf_shares, generate_summary,
)


@flow(name="Indicator 数据更新")
def indicator_data_update(
    update_structure: bool = True,
    update_trend: bool = True,
    full_fred_refresh: bool = False,
) -> dict:
    """
    更新所有指标数据。

    Args:
        update_structure: 更新 Structure 层 (CAPE, SPX)
        update_trend: 更新 Trend 层 (FRED/Yahoo, ETF shares)
        full_fred_refresh: 完整刷新所有 FRED 数据 (周末运行)
    """
    logger = get_run_logger()

    logger.info("=" * 50)
    logger.info(f"Starting Indicator Data Update at {datetime.now()}")
    logger.info("=" * 50)

    results = {}
    loader = DataLoader()

    # Structure Layer
    if update_structure:
        logger.info("\n[Structure Layer]")

        if full_fred_refresh:
            logger.info("Full FRED refresh...")
            loader.download_all_structure_factors()
            results["fred_refresh"] = True
        else:
            # Daily updates: CAPE + SPX
            logger.info("Updating CAPE from multpl.com...")
            results["cape"] = loader.update_cape_data()

            logger.info("Updating SPX from Yahoo...")
            results["spx"] = loader.update_spx_data()

        logger.info("Generating lagged data...")
        loader.generate_lagged_data()

    # Trend Layer
    if update_trend:
        logger.info("\n[Trend Layer]")

        # Module A: Volatility
        logger.info("Module A: Volatility...")
        cache_a1_vts()
        cache_a2_skew()
        cache_a3_move()

        # Module B: Funding
        logger.info("Module B: Funding...")
        cache_b1_funding()
        cache_b2_gcf_iorb()

        # Module C: Credit
        logger.info("Module C: Credit...")
        cache_c1_hy_spread()
        cache_c2_ig_spread()

        # Module D: ETF Shares from iShares
        logger.info("Module D: ETF Shares from iShares...")
        update_all_etf_shares()

        # Summary
        generate_summary()
        results["trend"] = True

    logger.info("=" * 50)
    logger.info(f"Done at {datetime.now()}")
    logger.info("=" * 50)

    return results


@flow(name="Indicator 周末刷新")
def indicator_weekly_refresh() -> dict:
    """周末完整刷新所有 FRED 数据。"""
    return indicator_data_update(
        update_structure=True,
        update_trend=True,
        full_fred_refresh=True,
    )


if __name__ == "__main__":
    indicator_data_update()
