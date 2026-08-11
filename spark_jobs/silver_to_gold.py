"""
Step 4: Silver → Gold

Joins Silver tables into analytics-ready Gold tables:
  - dim_date: calendar dimension
  - dim_fuel_type: fuel metadata + carbon factors
  - fct_hourly_grid_snapshot: main fact table (demand + gen + prices + weather)
  - mart_daily_summary: daily aggregates
  - mart_carbon_intensity: gCO2/kWh per hour

Usage:
    python spark_jobs/silver_to_gold.py
    make spark-gold
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, when, year, month, dayofmonth, dayofweek, quarter,
    date_format, round as spark_round, sum as spark_sum,
    avg as spark_avg, max as spark_max, min as spark_min,
    count as spark_count, coalesce, explode, sequence,
    to_date, expr
)
from pyspark.sql.types import DateType, IntegerType, DoubleType, StringType


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SILVER_DIR = os.path.join(PROJECT_ROOT, "data", "silver")
GOLD_DIR = os.path.join(PROJECT_ROOT, "data", "gold")
SEEDS_DIR = os.path.join(PROJECT_ROOT, "seeds")


def get_spark():
    """Create a local SparkSession with Delta Lake support."""
    return (
        SparkSession.builder
        .appName("OntarioGrid-SilverToGold")
        .master("local[*]")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.3.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


# ────────────────────────────────────────────────────────────
# DIMENSION: dim_date
# ────────────────────────────────────────────────────────────

def build_dim_date(spark):
    """
    Build a calendar dimension table.

    One row per date with useful attributes for filtering/grouping.
    """
    gold_path = os.path.join(GOLD_DIR, "dim_date")

    # Generate date range from the demand data
    demand_path = os.path.join(SILVER_DIR, "demand")
    if not os.path.exists(demand_path):
        print("  ⚠️  No silver demand data found — skipping dim_date")
        return

    demand = spark.read.format("delta").load(demand_path)
    min_date = demand.agg(spark_min("date")).collect()[0][0]
    max_date = demand.agg(spark_max("date")).collect()[0][0]

    # Generate all dates in range
    date_range = spark.sql(f"""
        SELECT explode(sequence(
            to_date('{min_date}'),
            to_date('{max_date}'),
            interval 1 day
        )) as date
    """)

    dim = (
        date_range
        .withColumn("year", year("date"))
        .withColumn("quarter", quarter("date"))
        .withColumn("month", month("date"))
        .withColumn("month_name", date_format("date", "MMMM"))
        .withColumn("day_of_month", dayofmonth("date"))
        .withColumn("day_of_week", dayofweek("date"))
        .withColumn("day_name", date_format("date", "EEEE"))
        .withColumn("is_weekday", when(
            dayofweek("date").between(2, 6), True
        ).otherwise(False))
        .withColumn("season", when(
            month("date").isin(12, 1, 2), "Winter"
        ).when(
            month("date").isin(3, 4, 5), "Spring"
        ).when(
            month("date").isin(6, 7, 8), "Summer"
        ).otherwise("Fall"))
    )

    dim.write.format("delta").mode("overwrite").save(gold_path)
    print(f"  ✅ dim_date: {dim.count()} rows")


# ────────────────────────────────────────────────────────────
# DIMENSION: dim_fuel_type
# ────────────────────────────────────────────────────────────

def build_dim_fuel_type(spark):
    """
    Build fuel type dimension from seeds/fuel_type_metadata.csv.

    Contains carbon emission factors used for carbon intensity calculations.
    """
    gold_path = os.path.join(GOLD_DIR, "dim_fuel_type")
    seed_path = os.path.join(SEEDS_DIR, "fuel_type_metadata.csv")

    if not os.path.exists(seed_path):
        print("  ⚠️  No fuel_type_metadata.csv found in seeds/")
        return

    df = spark.read.csv(seed_path, header=True, inferSchema=True)

    df.write.format("delta").mode("overwrite").save(gold_path)
    print(f"  ✅ dim_fuel_type: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# FACT: fct_hourly_grid_snapshot
# ────────────────────────────────────────────────────────────

def build_fct_hourly_grid_snapshot(spark):
    """
    Build the main fact table — one row per hour with everything joined.

    Joins: demand + generation + prices + weather on (date, hour).
    """
    gold_path = os.path.join(GOLD_DIR, "fct_hourly_grid_snapshot")

    # Load Silver tables
    tables = {}
    for name in ["demand", "generation", "prices", "weather"]:
        path = os.path.join(SILVER_DIR, name)
        if os.path.exists(path):
            tables[name] = spark.read.format("delta").load(path)
        else:
            print(f"  ⚠️  No silver {name} data — skipping from snapshot")

    if "demand" not in tables:
        print("  ⚠️  Demand is required for snapshot — skipping")
        return

    # Start with demand as the base (most complete date range)
    snapshot = tables["demand"]

    # Join generation (already pivoted in Silver — one row per hour)
    if "generation" in tables:
        gen_cols = [c for c in tables["generation"].columns
                    if c not in ["date", "hour"] and not c.startswith("day_")
                    and c not in ["is_weekday", "season", "is_peak_hour",
                                  "year", "month", "month_num", "day_name"]]
        gen = tables["generation"].select("date", "hour", *gen_cols)
        snapshot = snapshot.join(gen, on=["date", "hour"], how="left")

    # Join prices
    if "prices" in tables:
        price_cols = [c for c in tables["prices"].columns
                      if c not in ["date", "hour"] and not c.startswith("day_")
                      and c not in ["is_weekday", "season", "is_peak_hour",
                                    "year", "month", "month_num", "day_name",
                                    "price_category"]]
        # Keep price_category
        price_cols.append("price_category")
        price_cols = [c for c in price_cols if c in tables["prices"].columns]
        prices = tables["prices"].select("date", "hour", *price_cols)
        snapshot = snapshot.join(prices, on=["date", "hour"], how="left")

    # Join weather
    if "weather" in tables:
        weather_cols = [c for c in tables["weather"].columns
                        if c not in ["date", "hour"] and not c.startswith("day_")
                        and c not in ["is_weekday", "season", "is_peak_hour",
                                      "year", "month", "month_num", "day_name"]]
        weather = tables["weather"].select("date", "hour", *weather_cols)
        snapshot = snapshot.join(weather, on=["date", "hour"], how="left")

    # Calculate carbon intensity if we have generation data
    # Carbon intensity = weighted average of fuel carbon factors
    # Formula: sum(fuel_mw * carbon_factor) / total_generation_mw
    if "generation" in tables:
        # Carbon factors from seeds (gCO2/kWh)
        carbon_factors = {
            "nuclear_mw": 12, "hydro_mw": 24, "wind_mw": 11,
            "solar_mw": 45, "gas_mw": 490, "biofuel_mw": 230, "other_mw": 0
        }

        carbon_expr_parts = []
        for fuel_col, factor in carbon_factors.items():
            if fuel_col in snapshot.columns:
                carbon_expr_parts.append(
                    coalesce(col(fuel_col), lit(0.0)) * lit(factor)
                )

        if carbon_expr_parts and "total_generation_mw" in snapshot.columns:
            total_carbon = carbon_expr_parts[0]
            for part in carbon_expr_parts[1:]:
                total_carbon = total_carbon + part

            snapshot = snapshot.withColumn("carbon_intensity_gco2_kwh",
                spark_round(total_carbon / col("total_generation_mw"), 2)
            )

    snapshot.write.format("delta").mode("overwrite").save(gold_path)
    print(f"  ✅ fct_hourly_grid_snapshot: {snapshot.count()} rows, {len(snapshot.columns)} columns")


# ────────────────────────────────────────────────────────────
# MART: mart_daily_summary
# ────────────────────────────────────────────────────────────

def build_mart_daily_summary(spark):
    """
    Pre-computed daily aggregates for the dashboard trends page.

    One row per date with daily averages, peaks, and totals.
    """
    gold_path = os.path.join(GOLD_DIR, "mart_daily_summary")
    snapshot_path = os.path.join(GOLD_DIR, "fct_hourly_grid_snapshot")

    if not os.path.exists(snapshot_path):
        print("  ⚠️  fct_hourly_grid_snapshot required — skipping mart_daily_summary")
        return

    snapshot = spark.read.format("delta").load(snapshot_path)

    # Build aggregations
    agg_exprs = [
        # Demand
        spark_avg("ontario_demand").alias("avg_demand_mw"),
        spark_max("ontario_demand").alias("peak_demand_mw"),
        spark_min("ontario_demand").alias("min_demand_mw"),

        # Prices
        spark_avg("hoep").alias("avg_price"),
        spark_max("hoep").alias("max_price"),
        spark_min("hoep").alias("min_price"),
    ]

    # Generation columns (if they exist)
    for fuel in ["nuclear_mw", "gas_mw", "hydro_mw", "wind_mw", "solar_mw"]:
        if fuel in snapshot.columns:
            agg_exprs.append(spark_avg(fuel).alias(f"avg_{fuel}"))

    if "total_generation_mw" in snapshot.columns:
        agg_exprs.append(spark_avg("total_generation_mw").alias("avg_total_gen_mw"))

    if "clean_energy_pct" in snapshot.columns:
        agg_exprs.append(spark_avg("clean_energy_pct").alias("avg_clean_energy_pct"))

    if "carbon_intensity_gco2_kwh" in snapshot.columns:
        agg_exprs.append(spark_avg("carbon_intensity_gco2_kwh").alias("avg_carbon_intensity"))

    # Weather
    if "temperature_c" in snapshot.columns:
        agg_exprs.extend([
            spark_avg("temperature_c").alias("avg_temp_c"),
            spark_max("temperature_c").alias("max_temp_c"),
            spark_min("temperature_c").alias("min_temp_c"),
        ])

    # Group by date + time features
    group_cols = ["date"]
    for c in ["season", "is_weekday", "day_name", "year", "month"]:
        if c in snapshot.columns:
            group_cols.append(c)

    daily = snapshot.groupBy(*group_cols).agg(*agg_exprs)

    # Round everything
    for c in daily.columns:
        if c not in group_cols:
            daily = daily.withColumn(c, spark_round(col(c), 2))

    daily = daily.orderBy("date")

    daily.write.format("delta").mode("overwrite").save(gold_path)
    print(f"  ✅ mart_daily_summary: {daily.count()} rows")


# ────────────────────────────────────────────────────────────
# MART: mart_carbon_intensity
# ────────────────────────────────────────────────────────────

def build_mart_carbon_intensity(spark):
    """
    Hourly carbon intensity of Ontario's grid.

    gCO2/kWh tells you how "dirty" the electricity is at any given hour.
    Low = mostly nuclear/hydro/wind. High = lots of gas.
    """
    gold_path = os.path.join(GOLD_DIR, "mart_carbon_intensity")
    snapshot_path = os.path.join(GOLD_DIR, "fct_hourly_grid_snapshot")

    if not os.path.exists(snapshot_path):
        print("  ⚠️  fct_hourly_grid_snapshot required — skipping mart_carbon_intensity")
        return

    snapshot = spark.read.format("delta").load(snapshot_path)

    if "carbon_intensity_gco2_kwh" not in snapshot.columns:
        print("  ⚠️  No carbon_intensity column found — skipping")
        return

    # Select relevant columns
    select_cols = ["date", "hour", "carbon_intensity_gco2_kwh"]

    for c in ["total_generation_mw", "gas_mw", "nuclear_mw", "hydro_mw",
              "wind_mw", "solar_mw", "clean_energy_pct", "season",
              "is_peak_hour", "temperature_c"]:
        if c in snapshot.columns:
            select_cols.append(c)

    carbon = snapshot.select(*select_cols)

    # Add carbon category
    carbon = carbon.withColumn("carbon_category", when(
        col("carbon_intensity_gco2_kwh") < 50, "Very Clean"
    ).when(
        col("carbon_intensity_gco2_kwh") < 100, "Clean"
    ).when(
        col("carbon_intensity_gco2_kwh") < 200, "Moderate"
    ).otherwise("Dirty"))

    carbon.write.format("delta").mode("overwrite").save(gold_path)
    print(f"  ✅ mart_carbon_intensity: {carbon.count()} rows")


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Step 4: Silver → Gold (Star Schema + Analytics Marts)")
    print("=" * 60)

    spark = get_spark()

    # Dimensions first (referenced by facts)
    build_dim_date(spark)
    build_dim_fuel_type(spark)

    # Main fact table (joins Silver tables)
    build_fct_hourly_grid_snapshot(spark)

    # Marts (aggregate from fact table)
    build_mart_daily_summary(spark)
    build_mart_carbon_intensity(spark)

    spark.stop()
    print("\n✅ Gold layer complete")
