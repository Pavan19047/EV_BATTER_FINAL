-- infra/create_telemetry_table.sql - TimescaleDB Schema for EV Telemetry

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Drop table if exists for clean setup
DROP TABLE IF EXISTS telemetry CASCADE;

-- Create telemetry table with comprehensive EV battery and vehicle metrics
CREATE TABLE telemetry (
    ts TIMESTAMPTZ NOT NULL,
    soc FLOAT,                      -- State of Charge (%)
    soh FLOAT,                      -- State of Health (%)
    battery_voltage FLOAT,          -- Battery pack voltage (V)
    battery_current FLOAT,          -- Battery current (A)
    battery_temperature FLOAT,      -- Battery temperature (°C)
    motor_temperature FLOAT,        -- Motor temperature (°C)
    motor_vibration FLOAT,          -- Motor vibration level
    power_consumption FLOAT,        -- Power consumption (kW)
    driving_speed FLOAT,            -- Vehicle speed (km/h)
    distance_traveled FLOAT,        -- Cumulative distance (km)
    rul FLOAT,                      -- Remaining Useful Life (prediction)
    failure_probability FLOAT,      -- Probability of failure (prediction)
    PRIMARY KEY (ts)
);

-- Convert to TimescaleDB hypertable for optimized time-series storage
SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_ts_desc ON telemetry (ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_soc ON telemetry (soc) WHERE soc IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_telemetry_rul ON telemetry (rul) WHERE rul IS NOT NULL;

-- Add retention policy: keep data for 30 days
SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- Create continuous aggregate for hourly statistics (optional)
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', ts) AS bucket,
    AVG(soc) AS avg_soc,
    AVG(soh) AS avg_soh,
    AVG(battery_temperature) AS avg_battery_temp,
    AVG(rul) AS avg_rul,
    AVG(failure_probability) AS avg_failure_prob,
    COUNT(*) AS data_points
FROM telemetry
GROUP BY bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('telemetry_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Grant permissions (if needed for additional users)
-- GRANT ALL PRIVILEGES ON telemetry TO twin;
-- GRANT ALL PRIVILEGES ON telemetry_hourly TO twin;

-- Insert sample row to verify table creation
INSERT INTO telemetry (ts, soc, soh, battery_voltage, battery_current, battery_temperature, 
                       motor_temperature, motor_vibration, power_consumption, 
                       driving_speed, distance_traveled)
VALUES (NOW(), 85.0, 95.0, 400.0, 50.0, 25.0, 65.0, 0.5, 35.0, 60.0, 0.0)
ON CONFLICT (ts) DO NOTHING;

-- Verify table creation
SELECT COUNT(*) as initial_count FROM telemetry;
