

import os
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, DateType, TimestampType
)

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
BRONZE_DIR = os.path.join(PROJECT_ROOT, "data", "bronze")


def get_spark():
    """Create a local SparkSession with Delta Lake support."""
    builder = (
        SparkSession.builder
        .appName("OntarioGrid-BronzeIngestion")
        .master("local[*]")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.3.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.showConsoleProgress", "false")
    )
    return builder.getOrCreate()


def ingest_demand(spark):
    """Read demand CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "demand")
    delta_path = os.path.join(BRONZE_DIR, "demand")

    if not os.path.exists(csv_path):
        print(" No demand data found in data/raw/demand/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    # Drop metadata columns from ETL
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f"  demand: {df.count()} rows → {delta_path}")


def ingest_generation(spark):
    """Read generation CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "generation")
    delta_path = os.path.join(BRONZE_DIR, "generation")

    if not os.path.exists(csv_path):
        print("  No generation data found in data/raw/generation/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f"  generation: {df.count()} rows → {delta_path}")


def ingest_prices(spark):
    """Read prices CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "prices")
    delta_path = os.path.join(BRONZE_DIR, "prices")

    if not os.path.exists(csv_path):
        print("  No price data found in data/raw/prices/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f"  prices: {df.count()} rows → {delta_path}")


def ingest_realtime(spark):
    """Read realtime CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "realtime")
    delta_path = os.path.join(BRONZE_DIR, "realtime")

    if not os.path.exists(csv_path):
        print("   No realtime data found in data/raw/realtime/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f"  realtime: {df.count()} rows → {delta_path}")


def ingest_intertie(spark):
    """Read intertie CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "intertie")
    delta_path = os.path.join(BRONZE_DIR, "intertie")

    if not os.path.exists(csv_path):
        print("  No intertie data found in data/raw/intertie/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f"  intertie: {df.count()} rows → {delta_path}")


def ingest_weather(spark):
    """Read weather CSV → write Delta table."""
    csv_path = os.path.join(RAW_DIR, "weather")
    delta_path = os.path.join(BRONZE_DIR, "weather")

    if not os.path.exists(csv_path):
        print("  No weather data found in data/raw/weather/")
        return

    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    for col in ["_loaded_at", "_source"]:
        if col in df.columns:
            df = df.drop(col)

    df.write.format("delta").mode("overwrite").save(delta_path)
    print(f" weather: {df.count()} rows → {delta_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Step 2: Bronze Ingestion (CSV → Delta Lake)")
    print("=" * 60)

    spark = get_spark()

    ingest_demand(spark)
    ingest_generation(spark)
    ingest_prices(spark)
    ingest_realtime(spark)
    ingest_intertie(spark)
    ingest_weather(spark)

    spark.stop()
    print("\n✅ Bronze ingestion complete")
