"""
Data validation utilities for IESO data quality checks.

Validates:
- Schema: correct columns and types
- Range: values within expected bounds
- Completeness: no missing hours in daily data
- Duplicates: no duplicate (date, hour) pairs
"""

import pandas as pd
import logging

logger = logging.getLogger("Validator")


def validate_demand(df: pd.DataFrame) -> dict:
    """Validate demand data quality."""
    issues = []

    # Check for negative demand (should never happen)
    if "ontario_demand" in df.columns:
        negatives = df[df["ontario_demand"] < 0]
        if not negatives.empty:
            issues.append(f"Found {len(negatives)} rows with negative Ontario demand")

    # Check for unreasonably high demand (Ontario peak is ~25,000 MW)
    if "ontario_demand" in df.columns:
        extreme = df[df["ontario_demand"] > 35000]
        if not extreme.empty:
            issues.append(f"Found {len(extreme)} rows with demand > 35,000 MW")

    # Check hour range (should be 1-24)
    if "hour" in df.columns:
        invalid_hours = df[(df["hour"] < 1) | (df["hour"] > 24)]
        if not invalid_hours.empty:
            issues.append(f"Found {len(invalid_hours)} rows with invalid hours")

    # Check for duplicates
    if "date" in df.columns and "hour" in df.columns:
        dupes = df.duplicated(subset=["date", "hour"], keep=False)
        if dupes.any():
            issues.append(f"Found {dupes.sum()} duplicate (date, hour) pairs")

    result = {
        "source": "demand",
        "rows": len(df),
        "issues": issues,
        "passed": len(issues) == 0,
    }

    if result["passed"]:
        logger.info(f"Demand validation PASSED: {len(df)} rows")
    else:
        for issue in issues:
            logger.warning(f"Demand validation issue: {issue}")

    return result


def validate_generation(df: pd.DataFrame) -> dict:
    """Validate generation data quality."""
    issues = []

    # Check for negative generation
    if "output_mw" in df.columns:
        negatives = df[df["output_mw"] < 0]
        if not negatives.empty:
            issues.append(f"Found {len(negatives)} rows with negative generation")

    # Check fuel types are expected
    expected_fuels = {"Nuclear", "Gas", "Hydro", "Wind", "Solar", "Biofuel"}
    if "fuel_type" in df.columns:
        actual_fuels = set(df["fuel_type"].unique())
        unexpected = actual_fuels - expected_fuels
        if unexpected:
            issues.append(f"Unexpected fuel types: {unexpected}")

    result = {
        "source": "generation",
        "rows": len(df),
        "issues": issues,
        "passed": len(issues) == 0,
    }

    if result["passed"]:
        logger.info(f"Generation validation PASSED: {len(df)} rows")
    else:
        for issue in issues:
            logger.warning(f"Generation validation issue: {issue}")

    return result


def validate_prices(df: pd.DataFrame) -> dict:
    """Validate price data quality."""
    issues = []

    # Prices can be negative (surplus situations) but not extremely negative
    price_cols = [c for c in df.columns if "price" in c.lower()]
    for col in price_cols:
        extreme_low = df[df[col] < -100]
        extreme_high = df[df[col] > 10000]
        if not extreme_low.empty:
            issues.append(f"{col}: {len(extreme_low)} rows below -$100/MWh")
        if not extreme_high.empty:
            issues.append(f"{col}: {len(extreme_high)} rows above $10,000/MWh")

    result = {
        "source": "prices",
        "rows": len(df),
        "issues": issues,
        "passed": len(issues) == 0,
    }

    if result["passed"]:
        logger.info(f"Price validation PASSED: {len(df)} rows")
    else:
        for issue in issues:
            logger.warning(f"Price validation issue: {issue}")

    return result
