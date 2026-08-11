-- ============================================================================
-- Performance indexes for dashboard queries
-- ============================================================================

-- Primary query pattern: filter by date range
CREATE INDEX IF NOT EXISTS idx_snapshot_date
    ON serving.fct_hourly_grid_snapshot (date);

CREATE INDEX IF NOT EXISTS idx_snapshot_date_hour
    ON serving.fct_hourly_grid_snapshot (date, hour);

-- Time feature filters
CREATE INDEX IF NOT EXISTS idx_snapshot_season
    ON serving.fct_hourly_grid_snapshot (season);

CREATE INDEX IF NOT EXISTS idx_snapshot_weekday
    ON serving.fct_hourly_grid_snapshot (is_weekday);

CREATE INDEX IF NOT EXISTS idx_snapshot_peak
    ON serving.fct_hourly_grid_snapshot (is_peak_hour);

-- Price analysis queries
CREATE INDEX IF NOT EXISTS idx_snapshot_rt_price
    ON serving.fct_hourly_grid_snapshot (rt_price);

-- Generation mix queries  
CREATE INDEX IF NOT EXISTS idx_gen_mix_date
    ON serving.fct_daily_generation_mix (date);

-- Renewable penetration queries
CREATE INDEX IF NOT EXISTS idx_renewables_date
    ON serving.mart_renewable_penetration (date);

CREATE INDEX IF NOT EXISTS idx_renewables_year_month
    ON serving.mart_renewable_penetration (year, month);

-- Price spreads
CREATE INDEX IF NOT EXISTS idx_spreads_date
    ON serving.fct_price_spreads (date);

-- Carbon intensity
CREATE INDEX IF NOT EXISTS idx_carbon_date
    ON serving.fct_carbon_intensity (date);
