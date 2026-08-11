"""
ETL Pipeline Runner

Orchestrates the full extract → validate → save pipeline.
Runs all extractors and saves the results locally to data/bronze/.

Usage:
    python -m etl.run_pipeline              # Run all extractors (current year)
    python -m etl.run_pipeline --historical # Run with historical backfill
"""

import os
import argparse
import logging
import time
from datetime import datetime

from etl.demand_extractor import DemandExtractor
from etl.generation_extractor import GenerationExtractor
from etl.price_extractor import PriceExtractor
from etl.realtime_extractor import RealtimeExtractor
from etl.intertie_extractor import IntertieExtractor
from etl.weather_extractor import WeatherExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Pipeline")

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def save_to_raw(df, path: str):
    """Save DataFrame to data/raw/ as CSV."""
    full_path = os.path.join(PROJECT_ROOT, "data", "raw", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    df.to_csv(full_path, index=False)
    logger.info(f"Saved: {full_path} ({len(df)} rows)")


def run_pipeline(historical: bool = False):
    """
    Run the full ETL pipeline.

    Args:
        historical: If True, extract data from 2020 onwards.
                   If False, only extract current year.
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Ontario Grid Intelligence — ETL Pipeline Starting")
    logger.info(f"Mode: {'Historical Backfill' if historical else 'Current Year'}")
    logger.info("=" * 60)

    results = {}
    year = datetime.now().year

    # ── 1. Demand Data ──
    try:
        logger.info("\n📊 [1/6] Extracting demand data...")
        extractor = DemandExtractor()
        if historical:
            df = extractor.extract_historical(start_year=2020, end_year=year)
        else:
            df = extractor.run()
        save_to_raw(df, f"demand/demand_{year}.csv")
        results["demand"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Demand extraction failed: {e}")
        results["demand"] = f"❌ {e}"

    # ── 2. Generation by Fuel Type ──
    try:
        logger.info("\n⚡ [2/6] Extracting generation data...")
        extractor = GenerationExtractor()
        if historical:
            df = extractor.extract_historical(start_year=2020, end_year=year)
        else:
            df = extractor.run()
        save_to_raw(df, f"generation/generation_{year}.csv")
        results["generation"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Generation extraction failed: {e}")
        results["generation"] = f"❌ {e}"

    # ── 3. Prices (HOEP) ──
    try:
        logger.info("\n💰 [3/6] Extracting price data...")
        extractor = PriceExtractor()
        df = extractor.run()
        save_to_raw(df, f"prices/prices_{year}.csv")
        results["prices"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Price extraction failed: {e}")
        results["prices"] = f"❌ {e}"

    # ── 4. Realtime Totals ──
    try:
        logger.info("\n📈 [4/6] Extracting realtime totals...")
        extractor = RealtimeExtractor()
        df = extractor.run()
        today = datetime.now().strftime("%Y%m%d")
        save_to_raw(df, f"realtime/rt_totals_{today}.csv")
        results["realtime"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Realtime extraction failed: {e}")
        results["realtime"] = f"❌ {e}"

    # ── 5. Intertie Flows ──
    try:
        logger.info("\n🔌 [5/6] Extracting intertie flows...")
        extractor = IntertieExtractor()
        df = extractor.run()
        save_to_raw(df, f"intertie/intertie_flows_{year}.csv")
        results["intertie"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Intertie extraction failed: {e}")
        results["intertie"] = f"❌ {e}"

    # ── 6. Weather ──
    try:
        logger.info("\n🌡️ [6/6] Extracting weather data...")
        extractor = WeatherExtractor()
        if historical:
            df = extractor.extract_historical(start_year=2024, end_year=year)
        else:
            df = extractor.run()
        save_to_raw(df, f"weather/weather_{year}.csv")
        results["weather"] = f"✅ {len(df)} rows"
    except Exception as e:
        logger.error(f"Weather extraction failed: {e}")
        results["weather"] = f"❌ {e}"

    # ── Summary ──
    elapsed = round(time.time() - start_time, 1)
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Complete — Summary")
    logger.info("=" * 60)
    for source, result in results.items():
        logger.info(f"  {source:15s} {result}")
    logger.info(f"\n  Total time: {elapsed}s")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ontario Grid Intelligence ETL Pipeline")
    parser.add_argument("--historical", action="store_true",
                       help="Run historical backfill (2020 onwards)")
    args = parser.parse_args()

    run_pipeline(historical=args.historical)
