-- ============================================================================
-- Pre-computed views for Streamlit dashboard queries
-- ============================================================================

-- Latest grid snapshot (most recent hour)
CREATE OR REPLACE VIEW serving.v_latest_grid_status AS
SELECT *
FROM serving.fct_hourly_grid_snapshot
WHERE (date, hour) = (
    SELECT (date, hour)
    FROM serving.fct_hourly_grid_snapshot
    ORDER BY date DESC, hour DESC
    LIMIT 1
);

-- Daily summary for trend charts
CREATE OR REPLACE VIEW serving.v_daily_summary AS
SELECT
    date,
    ROUND(AVG(ontario_demand_mw), 1) AS avg_demand_mw,
    ROUND(MAX(ontario_demand_mw), 1) AS peak_demand_mw,
    ROUND(MIN(ontario_demand_mw), 1) AS min_demand_mw,
    ROUND(AVG(total_generation_mw), 1) AS avg_generation_mw,
    ROUND(AVG(pct_renewable) * 100, 2) AS avg_pct_renewable,
    ROUND(AVG(rt_price), 2) AS avg_rt_price,
    ROUND(MAX(rt_price), 2) AS max_rt_price,
    ROUND(AVG(carbon_intensity_gco2), 2) AS avg_carbon_intensity,
    ROUND(AVG(temperature_c), 1) AS avg_temperature_c
FROM serving.fct_hourly_grid_snapshot
GROUP BY date
ORDER BY date;

-- Hourly generation mix (for stacked area charts)
CREATE OR REPLACE VIEW serving.v_hourly_generation_mix AS
SELECT
    date, hour,
    nuclear_mw, gas_mw, hydro_mw, wind_mw, solar_mw, biofuel_mw,
    total_generation_mw,
    ROUND(pct_nuclear * 100, 2) AS pct_nuclear,
    ROUND(pct_gas * 100, 2) AS pct_gas,
    ROUND(pct_hydro * 100, 2) AS pct_hydro,
    ROUND(pct_wind * 100, 2) AS pct_wind,
    ROUND(pct_solar * 100, 2) AS pct_solar,
    ROUND(pct_renewable * 100, 2) AS pct_renewable
FROM serving.fct_hourly_grid_snapshot
ORDER BY date, hour;

-- Price analysis view
CREATE OR REPLACE VIEW serving.v_price_analysis AS
SELECT
    date, hour,
    rt_price,
    da_price,
    price_spread,
    is_weekday,
    is_peak_hour,
    season,
    CASE
        WHEN rt_price > 100 THEN 'Spike'
        WHEN rt_price < 0 THEN 'Negative'
        ELSE 'Normal'
    END AS price_regime
FROM serving.fct_hourly_grid_snapshot
ORDER BY date, hour;

-- Carbon intensity by hour-of-day (for "when is Ontario cleanest?" chart)
CREATE OR REPLACE VIEW serving.v_carbon_by_hour AS
SELECT
    hour,
    ROUND(AVG(carbon_intensity_gco2), 2) AS avg_carbon_intensity,
    ROUND(MIN(carbon_intensity_gco2), 2) AS min_carbon_intensity,
    ROUND(MAX(carbon_intensity_gco2), 2) AS max_carbon_intensity,
    COUNT(*) AS sample_count
FROM serving.fct_hourly_grid_snapshot
WHERE carbon_intensity_gco2 IS NOT NULL
GROUP BY hour
ORDER BY hour;

-- Monthly renewable penetration trend
CREATE OR REPLACE VIEW serving.v_monthly_renewables AS
SELECT
    EXTRACT(YEAR FROM date) AS year,
    EXTRACT(MONTH FROM date) AS month,
    ROUND(AVG(pct_renewable) * 100, 2) AS avg_pct_renewable,
    ROUND(AVG(pct_wind) * 100, 2) AS avg_pct_wind,
    ROUND(AVG(pct_solar) * 100, 2) AS avg_pct_solar,
    ROUND(AVG(pct_hydro) * 100, 2) AS avg_pct_hydro,
    ROUND(AVG(pct_nuclear) * 100, 2) AS avg_pct_nuclear,
    ROUND(AVG(pct_gas) * 100, 2) AS avg_pct_gas
FROM serving.fct_hourly_grid_snapshot
GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
ORDER BY year, month;
