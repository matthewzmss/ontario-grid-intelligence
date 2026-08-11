

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, when, year, month, dayofmonth, dayofweek, hour,
    date_format, round as spark_round, sum as spark_sum,
    first, coalesce
)
from pyspark.sql.types import DateType, IntegerType, DoubleType


# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(PROJECT_ROOT, "data", "bronze")
SILVER_DIR = os.path.join(PROJECT_ROOT, "data", "silver")


def get_spark():
    """Create a local SparkSession with Delta Lake support."""
    return (
        SparkSession.builder
        .appName("OntarioGrid-BronzeToSilver")
        .master("local[*]")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.3.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def add_time_features(df):
    """Add common time-based features to any DataFrame with date and hour columns."""
    return (
        df
        # Day of week: 1=Sunday, 2=Monday, ..., 7=Saturday
        .withColumn("day_of_week", dayofweek(col("date")))
        .withColumn("day_name", date_format(col("date"), "EEEE"))

        # Is it a weekday? (Mon-Fri = True)
        .withColumn("is_weekday", when(
            dayofweek(col("date")).between(2, 6), True
        ).otherwise(False))

        # Season based on month
        .withColumn("month_num", month(col("date")))
        .withColumn("season", when(
            col("month_num").isin(12, 1, 2), "Winter"
        ).when(
            col("month_num").isin(3, 4, 5), "Spring"
        ).when(
            col("month_num").isin(6, 7, 8), "Summer"
        ).otherwise("Fall"))

        # Peak hours: 7am-7pm (hours 7-19 in IESO convention)
        .withColumn("is_peak_hour", when(
            col("hour").between(7, 19), True
        ).otherwise(False))

        # Year and month columns
        .withColumn("year", year(col("date")))
        .withColumn("month", month(col("date")))
    )


# ────────────────────────────────────────────────────────────
# DEMAND
# ────────────────────────────────────────────────────────────

def transform_demand(spark):
    """Clean and enrich demand data."""
    bronze_path = os.path.join(BRONZE_DIR, "demand")
    silver_path = os.path.join(SILVER_DIR, "demand")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze demand data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("market_demand", col("market_demand").cast(IntegerType()))
        .withColumn("ontario_demand", col("ontario_demand").cast(IntegerType()))
    )

    # Remove nulls and duplicates
    df = df.dropna(subset=["date", "hour", "ontario_demand"])
    df = df.dropDuplicates(["date", "hour"])

    # Add time features
    df = add_time_features(df)

    # Add demand category
    df = df.withColumn("demand_category", when(
        col("ontario_demand") < 15000, "Low"
    ).when(
        col("ontario_demand") < 20000, "Medium"
    ).when(
        col("ontario_demand") < 25000, "High"
    ).otherwise("Extreme"))

    # Export demand = Market - Ontario (electricity sold to neighbors)
    df = df.withColumn("export_demand",
        col("market_demand") - col("ontario_demand")
    )

    df.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ demand: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# GENERATION
# ────────────────────────────────────────────────────────────

def transform_generation(spark):
    """
    Clean generation data and pivot fuel types into columns.

    Bronze (7 rows per hour — one per fuel):
        date | hour | fuel_type | output_mw
        Jan 1 | 1   | Nuclear   | 9602
        Jan 1 | 1   | Gas       | 3246
        Jan 1 | 1   | Hydro     | 3137

    Silver (1 row per hour — fuels as columns):
        date | hour | nuclear_mw | gas_mw | hydro_mw | wind_mw | solar_mw | ...
        Jan 1 | 1   | 9602       | 3246   | 3137     | 3358    | 0        | ...
    """
    bronze_path = os.path.join(BRONZE_DIR, "generation")
    silver_path = os.path.join(SILVER_DIR, "generation")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze generation data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("output_mw", col("output_mw").cast(DoubleType()))
    )

    # Remove nulls and invalid values
    df = df.dropna(subset=["date", "hour", "fuel_type", "output_mw"])
    df = df.filter(col("output_mw") >= 0)

    # Pivot: one row per (date, hour) with fuel types as columns
    pivoted = (
        df.groupBy("date", "hour")
        .pivot("fuel_type")
        .agg(first("output_mw"))
    )

    # Rename columns to lowercase_mw format
    for c in pivoted.columns:
        if c not in ["date", "hour"]:
            new_name = c.lower().replace(" ", "_") + "_mw"
            pivoted = pivoted.withColumnRenamed(c, new_name)

    # Fill nulls with 0 (if a fuel type had no output)
    for c in pivoted.columns:
        if c.endswith("_mw"):
            pivoted = pivoted.withColumn(c,
                coalesce(col(c), lit(0.0)).cast(DoubleType())
            )

    # Calculate total generation
    mw_cols = [c for c in pivoted.columns if c.endswith("_mw")]
    total_expr = sum([col(c) for c in mw_cols])
    pivoted = pivoted.withColumn("total_generation_mw", total_expr)

    # Calculate % for each fuel type
    for c in mw_cols:
        pct_name = c.replace("_mw", "_pct")
        pivoted = pivoted.withColumn(pct_name,
            spark_round(col(c) / col("total_generation_mw") * 100, 2)
        )

    # Calculate % clean energy (nuclear + hydro + wind + solar + biofuel)
    clean_cols = [c for c in mw_cols if any(
        fuel in c for fuel in ["nuclear", "hydro", "wind", "solar", "biofuel"]
    )]
    clean_expr = sum([col(c) for c in clean_cols])
    pivoted = pivoted.withColumn("clean_energy_pct",
        spark_round(clean_expr / col("total_generation_mw") * 100, 2)
    )

    # Add time features
    pivoted = add_time_features(pivoted)

    pivoted.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ generation: {pivoted.count()} rows")


# ────────────────────────────────────────────────────────────
# PRICES
# ────────────────────────────────────────────────────────────

def transform_prices(spark):
    """Clean and categorize price data."""
    bronze_path = os.path.join(BRONZE_DIR, "prices")
    silver_path = os.path.join(SILVER_DIR, "prices")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze price data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("hoep", col("hoep").cast(DoubleType()))
    )

    # Remove nulls and duplicates
    df = df.dropna(subset=["date", "hour", "hoep"])
    df = df.dropDuplicates(["date", "hour"])

    # Price category
    df = df.withColumn("price_category", when(
        col("hoep") < 0, "Negative"
    ).when(
        col("hoep") < 20, "Low"
    ).when(
        col("hoep") < 50, "Medium"
    ).when(
        col("hoep") < 100, "High"
    ).otherwise("Spike"))

    # Add time features
    df = add_time_features(df)

    df.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ prices: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# REALTIME TOTALS
# ────────────────────────────────────────────────────────────

def transform_realtime(spark):
    """Clean realtime grid totals."""
    bronze_path = os.path.join(BRONZE_DIR, "realtime")
    silver_path = os.path.join(SILVER_DIR, "realtime")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze realtime data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("total_energy", col("total_energy").cast(DoubleType()))
        .withColumn("total_loss", col("total_loss").cast(DoubleType()))
        .withColumn("total_load", col("total_load").cast(DoubleType()))
    )

    # Net load (energy minus transmission losses)
    df = df.withColumn("net_load", col("total_energy") - col("total_loss"))

    # Loss percentage
    df = df.withColumn("loss_pct",
        spark_round(col("total_loss") / col("total_energy") * 100, 2)
    )

    df.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ realtime: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# INTERTIE FLOWS
# ────────────────────────────────────────────────────────────

def transform_intertie(spark):
    """Clean and enrich intertie flow data."""
    bronze_path = os.path.join(BRONZE_DIR, "intertie")
    silver_path = os.path.join(SILVER_DIR, "intertie")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze intertie data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("schedule_import_mw", col("schedule_import_mw").cast(DoubleType()))
        .withColumn("schedule_export_mw", col("schedule_export_mw").cast(DoubleType()))
    )

    # Net scheduled flow (positive = import, negative = export)
    df = df.withColumn("net_scheduled_flow_mw",
        col("schedule_import_mw") - col("schedule_export_mw")
    )

    # Flow direction
    df = df.withColumn("flow_direction", when(
        col("net_scheduled_flow_mw") > 0, "Import"
    ).when(
        col("net_scheduled_flow_mw") < 0, "Export"
    ).otherwise("Balanced"))

    # Add time features
    df = add_time_features(df)

    df.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ intertie: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# WEATHER
# ────────────────────────────────────────────────────────────

def transform_weather(spark):
    """Clean and categorize weather data."""
    bronze_path = os.path.join(BRONZE_DIR, "weather")
    silver_path = os.path.join(SILVER_DIR, "weather")

    if not os.path.exists(bronze_path):
        print("  ⚠️  No bronze weather data found")
        return

    df = spark.read.format("delta").load(bronze_path)

    # Cast types
    df = (
        df
        .withColumn("date", col("date").cast(DateType()))
        .withColumn("hour", col("hour").cast(IntegerType()))
        .withColumn("temperature_c", col("temperature_c").cast(DoubleType()))
        .withColumn("humidity_pct", col("humidity_pct").cast(DoubleType()))
        .withColumn("wind_speed_kmh", col("wind_speed_kmh").cast(DoubleType()))
    )

    # Remove nulls and duplicates
    df = df.dropna(subset=["date", "hour", "temperature_c"])
    df = df.dropDuplicates(["date", "hour"])

    # Temperature category
    df = df.withColumn("temp_category", when(
        col("temperature_c") < -10, "Extreme Cold"
    ).when(
        col("temperature_c") < 0, "Cold"
    ).when(
        col("temperature_c") < 15, "Mild"
    ).when(
        col("temperature_c") < 25, "Warm"
    ).when(
        col("temperature_c") < 35, "Hot"
    ).otherwise("Extreme Heat"))

    # Heating/cooling degree indicator
    # Below 18°C = heating needed, above 22°C = cooling needed
    df = df.withColumn("hvac_mode", when(
        col("temperature_c") < 18, "Heating"
    ).when(
        col("temperature_c") > 22, "Cooling"
    ).otherwise("Neutral"))

    # Add time features
    df = add_time_features(df)

    df.write.format("delta").mode("overwrite").save(silver_path)
    print(f"  ✅ weather: {df.count()} rows")


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Step 3: Bronze → Silver (Clean + Enrich)")
    print("=" * 60)

    spark = get_spark()

    transform_demand(spark)
    transform_generation(spark)
    transform_prices(spark)
    transform_realtime(spark)
    transform_intertie(spark)
    transform_weather(spark)

    spark.stop()
    print("\n✅ Silver transformation complete")
