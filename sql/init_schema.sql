-- ============================================================================
-- Ontario Grid Intelligence Platform — PostgreSQL Serving Layer
-- ============================================================================
-- This schema receives Gold-layer data from PySpark (via JDBC export)
-- and serves it to the Streamlit dashboard.
-- ============================================================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS staging;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS serving.dim_date (
    date_key        DATE PRIMARY KEY,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    day             INTEGER NOT NULL,
    day_of_week     INTEGER NOT NULL,         -- 1=Monday, 7=Sunday
    day_name        VARCHAR(10) NOT NULL,     -- 'Monday', 'Tuesday', etc.
    month_name      VARCHAR(10) NOT NULL,     -- 'January', 'February', etc.
    quarter         INTEGER NOT NULL,         -- 1-4
    is_weekday      BOOLEAN NOT NULL,
    is_holiday      BOOLEAN DEFAULT FALSE,
    season          VARCHAR(10) NOT NULL,     -- 'Winter', 'Spring', 'Summer', 'Fall'
    week_of_year    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS serving.dim_fuel_type (
    fuel_type_key   SERIAL PRIMARY KEY,
    fuel_type       VARCHAR(50) UNIQUE NOT NULL,  -- 'Nuclear', 'Gas', 'Hydro', etc.
    fuel_category   VARCHAR(20) NOT NULL,         -- 'Baseload', 'Peaking', 'Renewable'
    is_renewable    BOOLEAN NOT NULL,
    carbon_factor   NUMERIC(8,2) NOT NULL,        -- gCO2/kWh
    display_color   VARCHAR(7) NOT NULL,          -- Hex color for charts
    display_order   INTEGER NOT NULL              -- Sort order in charts
);

CREATE TABLE IF NOT EXISTS serving.dim_zone (
    zone_key        SERIAL PRIMARY KEY,
    zone_name       VARCHAR(50) UNIQUE NOT NULL,  -- 'Northwest', 'Northeast', etc.
    zone_code       VARCHAR(10) NOT NULL,
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6)
);

CREATE TABLE IF NOT EXISTS serving.dim_hour (
    hour_key        INTEGER PRIMARY KEY,          -- 1-24 (hour-ending)
    hour_label      VARCHAR(20) NOT NULL,         -- '01:00', '02:00', etc.
    peak_class      VARCHAR(20) NOT NULL,         -- 'Off-Peak', 'Mid-Peak', 'On-Peak'
    is_peak         BOOLEAN NOT NULL
);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- Central fact table: hourly grid snapshot
CREATE TABLE IF NOT EXISTS serving.fct_hourly_grid_snapshot (
    id                      BIGSERIAL PRIMARY KEY,
    date                    DATE NOT NULL,
    hour                    INTEGER NOT NULL,           -- 1-24 (hour-ending)
    
    -- Demand (MW)
    market_demand_mw        NUMERIC(10,1),
    ontario_demand_mw       NUMERIC(10,1),
    
    -- Generation by fuel type (MW)
    nuclear_mw              NUMERIC(10,1),
    gas_mw                  NUMERIC(10,1),
    hydro_mw                NUMERIC(10,1),
    wind_mw                 NUMERIC(10,1),
    solar_mw                NUMERIC(10,1),
    biofuel_mw              NUMERIC(10,1),
    total_generation_mw     NUMERIC(10,1),
    
    -- Generation percentages
    pct_nuclear             NUMERIC(6,4),
    pct_gas                 NUMERIC(6,4),
    pct_hydro               NUMERIC(6,4),
    pct_wind                NUMERIC(6,4),
    pct_solar               NUMERIC(6,4),
    pct_renewable           NUMERIC(6,4),              -- wind + solar + hydro + biofuel
    
    -- Prices ($/MWh)
    rt_price                NUMERIC(10,2),              -- Real-time zonal price
    da_price                NUMERIC(10,2),              -- Day-ahead LMP
    price_spread            NUMERIC(10,2),              -- DA - RT
    
    -- Weather
    temperature_c           NUMERIC(5,1),
    humidity_pct            NUMERIC(5,1),
    wind_speed_kmh          NUMERIC(5,1),
    
    -- Carbon
    carbon_intensity_gco2   NUMERIC(8,2),              -- gCO2/kWh
    
    -- Grid health
    total_loss_mw           NUMERIC(10,1),
    reserve_10s_mw          NUMERIC(10,1),
    reserve_10n_mw          NUMERIC(10,1),
    reserve_30r_mw          NUMERIC(10,1),
    
    -- Time features (denormalized for query performance)
    is_weekday              BOOLEAN,
    is_peak_hour            BOOLEAN,
    season                  VARCHAR(10),
    day_of_week             INTEGER,
    
    -- Metadata
    loaded_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, hour)
);

-- Daily generation mix
CREATE TABLE IF NOT EXISTS serving.fct_daily_generation_mix (
    id                      BIGSERIAL PRIMARY KEY,
    date                    DATE NOT NULL UNIQUE,
    
    -- Daily totals (MWh)
    nuclear_mwh             NUMERIC(12,1),
    gas_mwh                 NUMERIC(12,1),
    hydro_mwh               NUMERIC(12,1),
    wind_mwh                NUMERIC(12,1),
    solar_mwh               NUMERIC(12,1),
    biofuel_mwh             NUMERIC(12,1),
    total_mwh               NUMERIC(12,1),
    
    -- Daily percentages
    pct_nuclear             NUMERIC(6,4),
    pct_gas                 NUMERIC(6,4),
    pct_hydro               NUMERIC(6,4),
    pct_wind                NUMERIC(6,4),
    pct_solar               NUMERIC(6,4),
    pct_renewable           NUMERIC(6,4),
    
    -- Daily demand
    peak_demand_mw          NUMERIC(10,1),
    min_demand_mw           NUMERIC(10,1),
    avg_demand_mw           NUMERIC(10,1),
    
    -- Daily prices
    avg_price               NUMERIC(10,2),
    max_price               NUMERIC(10,2),
    min_price               NUMERIC(10,2),
    
    -- Daily carbon
    avg_carbon_intensity    NUMERIC(8,2),
    
    loaded_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price spread analysis
CREATE TABLE IF NOT EXISTS serving.fct_price_spreads (
    id                      BIGSERIAL PRIMARY KEY,
    date                    DATE NOT NULL,
    hour                    INTEGER NOT NULL,
    
    rt_price                NUMERIC(10,2),
    da_price                NUMERIC(10,2),
    spread                  NUMERIC(10,2),             -- DA - RT
    abs_spread              NUMERIC(10,2),
    is_positive_spread      BOOLEAN,                   -- DA > RT
    
    UNIQUE(date, hour)
);

-- Carbon intensity tracking
CREATE TABLE IF NOT EXISTS serving.fct_carbon_intensity (
    id                      BIGSERIAL PRIMARY KEY,
    date                    DATE NOT NULL,
    hour                    INTEGER NOT NULL,
    
    carbon_intensity_gco2   NUMERIC(8,2),
    nuclear_contribution    NUMERIC(8,2),
    gas_contribution        NUMERIC(8,2),
    hydro_contribution      NUMERIC(8,2),
    wind_contribution       NUMERIC(8,2),
    solar_contribution      NUMERIC(8,2),
    
    UNIQUE(date, hour)
);

-- ============================================================================
-- ANALYTICS MARTS (Materialized for dashboard performance)
-- ============================================================================

CREATE TABLE IF NOT EXISTS serving.mart_renewable_penetration (
    id                      BIGSERIAL PRIMARY KEY,
    date                    DATE NOT NULL UNIQUE,
    year                    INTEGER,
    month                   INTEGER,
    
    -- Daily renewable metrics
    renewable_mwh           NUMERIC(12,1),
    total_mwh               NUMERIC(12,1),
    pct_renewable           NUMERIC(6,4),
    
    -- By source
    wind_mwh                NUMERIC(12,1),
    solar_mwh               NUMERIC(12,1),
    hydro_mwh               NUMERIC(12,1),
    
    -- Rolling averages
    pct_renewable_7d_avg    NUMERIC(6,4),
    pct_renewable_30d_avg   NUMERIC(6,4)
);

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT USAGE ON SCHEMA serving TO grid_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA serving TO grid_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA serving TO grid_admin;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '✅ Ontario Grid Intelligence — PostgreSQL schema initialized successfully';
END $$;
