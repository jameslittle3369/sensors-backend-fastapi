-- rollup_and_prune_history.sql
--
-- For every log/history table in the system, collapses rows older than
-- 6 months down to one daily high/low row per device (per metric, for
-- tables with more than one numeric metric per row), then deletes the
-- original rows that were rolled up. Rows newer than 6 months are left
-- completely untouched.
--
-- *** BACK UP THE DATABASE BEFORE RUNNING THIS. IT DELETES DATA. ***
-- Run scripts/preview_history_rollup.sql first to see exactly how many
-- rows/days/devices this will touch.
--
-- Day-boundary safety: the cutoff is a whole calendar day
-- (date_trunc('day', now() - interval '6 months')), not a bare
-- timestamp. If a single calendar day straddled the exact 6-month
-- instant, a timestamp cutoff would roll up only part of that day (say,
-- midnight-2pm) on one run, delete those rows, and then -- on a later
-- run, once the rest of that same day (2pm-midnight) also aged past the
-- cutoff -- try to insert a second rollup row for a day that's already
-- there, hit ON CONFLICT DO NOTHING, and silently discard that second
-- half's data during the DELETE that follows regardless. Truncating to
-- whole days means a day is only ever touched once it's *entirely* more
-- than 6 months old, so it's always rolled up from its complete data in
-- a single pass. This also makes the whole script safe to run daily
-- (as a future cron/systemd-timer job, per plan) with no changes: a
-- day whose rows are already gone just produces no GROUP BY row on the
-- next run, so nothing re-triggers for it.
--
-- Idempotent / safe to re-run: each INSERT uses ON CONFLICT DO NOTHING,
-- and the DELETE only ever removes rows already older than the cutoff
-- (which, given the point above, are always already reflected in a
-- rollup row by the time this DELETE runs).
--
-- Usage: psql -h <host> -U <user> -d <db> -f rollup_and_prune_history.sql

BEGIN;

-- Single shared cutoff for the whole script -- computed once so every
-- table uses the exact same day boundary, not a slightly different
-- now() per statement.
CREATE TEMP TABLE _rollup_cutoff AS
SELECT date_trunc('day', now() - interval '6 months')::date AS d;

-- === tstats_tstatlog (Thermometer, Celsius) ===============================
CREATE TABLE IF NOT EXISTS tstats_tstatlog_daily (
    romid_id varchar(50) NOT NULL,
    day date NOT NULL,
    low numeric(8, 4) NOT NULL,
    high numeric(8, 4) NOT NULL,
    PRIMARY KEY (romid_id, day)
);

INSERT INTO tstats_tstatlog_daily (romid_id, day, low, high)
SELECT romid_id, date_trunc('day', created_at)::date, min(primary_value), max(primary_value)
FROM tstats_tstatlog, _rollup_cutoff
WHERE date_trunc('day', created_at) < _rollup_cutoff.d
GROUP BY romid_id, date_trunc('day', created_at)
ON CONFLICT (romid_id, day) DO NOTHING;

DELETE FROM tstats_tstatlog USING _rollup_cutoff
WHERE date_trunc('day', tstats_tstatlog.created_at) < _rollup_cutoff.d;

-- === tstats_thermohygrostatlog (temp_f + humidity) ========================
CREATE TABLE IF NOT EXISTS tstats_thermohygrostatlog_daily (
    thermohygrometer_id varchar(50) NOT NULL,
    day date NOT NULL,
    temp_f_low numeric(8, 4) NOT NULL,
    temp_f_high numeric(8, 4) NOT NULL,
    humidity_low numeric(8, 1) NOT NULL,
    humidity_high numeric(8, 1) NOT NULL,
    PRIMARY KEY (thermohygrometer_id, day)
);

INSERT INTO tstats_thermohygrostatlog_daily
    (thermohygrometer_id, day, temp_f_low, temp_f_high, humidity_low, humidity_high)
SELECT thermohygrometer_id, date_trunc('day', created_at)::date,
       min(temp_f), max(temp_f), min(humidity), max(humidity)
FROM tstats_thermohygrostatlog, _rollup_cutoff
WHERE date_trunc('day', created_at) < _rollup_cutoff.d
GROUP BY thermohygrometer_id, date_trunc('day', created_at)
ON CONFLICT (thermohygrometer_id, day) DO NOTHING;

DELETE FROM tstats_thermohygrostatlog USING _rollup_cutoff
WHERE date_trunc('day', tstats_thermohygrostatlog.created_at) < _rollup_cutoff.d;

-- === energy_circuit_logs (watts) ==========================================
CREATE TABLE IF NOT EXISTS energy_circuit_logs_daily (
    circuit_id integer NOT NULL,
    day date NOT NULL,
    watts_low numeric(10, 2) NOT NULL,
    watts_high numeric(10, 2) NOT NULL,
    PRIMARY KEY (circuit_id, day)
);

INSERT INTO energy_circuit_logs_daily (circuit_id, day, watts_low, watts_high)
SELECT circuit_id, date_trunc('day', recorded_at)::date, min(watts), max(watts)
FROM energy_circuit_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY circuit_id, date_trunc('day', recorded_at)
ON CONFLICT (circuit_id, day) DO NOTHING;

DELETE FROM energy_circuit_logs USING _rollup_cutoff
WHERE date_trunc('day', energy_circuit_logs.recorded_at) < _rollup_cutoff.d;

-- === ikea_device_logs (battery_pct) ========================================
CREATE TABLE IF NOT EXISTS ikea_device_logs_daily (
    device_id integer NOT NULL,
    day date NOT NULL,
    battery_pct_low integer NOT NULL,
    battery_pct_high integer NOT NULL,
    PRIMARY KEY (device_id, day)
);

INSERT INTO ikea_device_logs_daily (device_id, day, battery_pct_low, battery_pct_high)
SELECT device_id, date_trunc('day', recorded_at)::date, min(battery_pct), max(battery_pct)
FROM ikea_device_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY device_id, date_trunc('day', recorded_at)
ON CONFLICT (device_id, day) DO NOTHING;

DELETE FROM ikea_device_logs USING _rollup_cutoff
WHERE date_trunc('day', ikea_device_logs.recorded_at) < _rollup_cutoff.d;

-- === ring_device_logs (battery_life) =======================================
CREATE TABLE IF NOT EXISTS ring_device_logs_daily (
    device_id integer NOT NULL,
    day date NOT NULL,
    battery_life_low integer NOT NULL,
    battery_life_high integer NOT NULL,
    PRIMARY KEY (device_id, day)
);

INSERT INTO ring_device_logs_daily (device_id, day, battery_life_low, battery_life_high)
SELECT device_id, date_trunc('day', recorded_at)::date, min(battery_life), max(battery_life)
FROM ring_device_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY device_id, date_trunc('day', recorded_at)
ON CONFLICT (device_id, day) DO NOTHING;

DELETE FROM ring_device_logs USING _rollup_cutoff
WHERE date_trunc('day', ring_device_logs.recorded_at) < _rollup_cutoff.d;

-- === hvac_zone_logs (7 numeric metrics; string/bool/enum fields have no
-- meaningful high/low and are dropped on rollup) ===========================
CREATE TABLE IF NOT EXISTS hvac_zone_logs_daily (
    hvac_zone_id varchar(50) NOT NULL,
    day date NOT NULL,
    disp_temperature_low integer, disp_temperature_high integer,
    heat_setpoint_low integer, heat_setpoint_high integer,
    cool_setpoint_low integer, cool_setpoint_high integer,
    schedule_heat_sp_low integer, schedule_heat_sp_high integer,
    schedule_cool_sp_low integer, schedule_cool_sp_high integer,
    indoor_humidity_low integer, indoor_humidity_high integer,
    outdoor_temperature_low integer, outdoor_temperature_high integer,
    PRIMARY KEY (hvac_zone_id, day)
);

INSERT INTO hvac_zone_logs_daily (
    hvac_zone_id, day,
    disp_temperature_low, disp_temperature_high,
    heat_setpoint_low, heat_setpoint_high,
    cool_setpoint_low, cool_setpoint_high,
    schedule_heat_sp_low, schedule_heat_sp_high,
    schedule_cool_sp_low, schedule_cool_sp_high,
    indoor_humidity_low, indoor_humidity_high,
    outdoor_temperature_low, outdoor_temperature_high
)
SELECT hvac_zone_id, date_trunc('day', recorded_at)::date,
       min(disp_temperature), max(disp_temperature),
       min(heat_setpoint), max(heat_setpoint),
       min(cool_setpoint), max(cool_setpoint),
       min(schedule_heat_sp), max(schedule_heat_sp),
       min(schedule_cool_sp), max(schedule_cool_sp),
       min(indoor_humidity), max(indoor_humidity),
       min(outdoor_temperature), max(outdoor_temperature)
FROM hvac_zone_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY hvac_zone_id, date_trunc('day', recorded_at)
ON CONFLICT (hvac_zone_id, day) DO NOTHING;

DELETE FROM hvac_zone_logs USING _rollup_cutoff
WHERE date_trunc('day', hvac_zone_logs.recorded_at) < _rollup_cutoff.d;

-- === anemometer_logs (speed_mph + direction_deg) ==========================
CREATE TABLE IF NOT EXISTS anemometer_logs_daily (
    anemometer_id varchar(50) NOT NULL,
    day date NOT NULL,
    speed_mph_low numeric(6, 1) NOT NULL,
    speed_mph_high numeric(6, 1) NOT NULL,
    direction_deg_low numeric(5, 1) NOT NULL,
    direction_deg_high numeric(5, 1) NOT NULL,
    PRIMARY KEY (anemometer_id, day)
);

INSERT INTO anemometer_logs_daily
    (anemometer_id, day, speed_mph_low, speed_mph_high, direction_deg_low, direction_deg_high)
SELECT anemometer_id, date_trunc('day', recorded_at)::date,
       min(speed_mph), max(speed_mph), min(direction_deg), max(direction_deg)
FROM anemometer_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY anemometer_id, date_trunc('day', recorded_at)
ON CONFLICT (anemometer_id, day) DO NOTHING;

DELETE FROM anemometer_logs USING _rollup_cutoff
WHERE date_trunc('day', anemometer_logs.recorded_at) < _rollup_cutoff.d;

-- === photo_uvmeter_logs (lumens + uv_index) ===============================
CREATE TABLE IF NOT EXISTS photo_uvmeter_logs_daily (
    photo_uvmeter_id varchar(50) NOT NULL,
    day date NOT NULL,
    lumens_low integer NOT NULL,
    lumens_high integer NOT NULL,
    uv_index_low integer NOT NULL,
    uv_index_high integer NOT NULL,
    PRIMARY KEY (photo_uvmeter_id, day)
);

INSERT INTO photo_uvmeter_logs_daily
    (photo_uvmeter_id, day, lumens_low, lumens_high, uv_index_low, uv_index_high)
SELECT photo_uvmeter_id, date_trunc('day', recorded_at)::date,
       min(lumens), max(lumens), min(uv_index), max(uv_index)
FROM photo_uvmeter_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY photo_uvmeter_id, date_trunc('day', recorded_at)
ON CONFLICT (photo_uvmeter_id, day) DO NOTHING;

DELETE FROM photo_uvmeter_logs USING _rollup_cutoff
WHERE date_trunc('day', photo_uvmeter_logs.recorded_at) < _rollup_cutoff.d;

-- === raingauge_logs (rain_in -- a raw accumulating counter; daily
-- low/high is mechanically well-defined but low is typically just the
-- first reading of the day and high the last, given rain_in only resets
-- on hardware rollover) ====================================================
CREATE TABLE IF NOT EXISTS raingauge_logs_daily (
    raingauge_id varchar(50) NOT NULL,
    day date NOT NULL,
    rain_in_low numeric(6, 2) NOT NULL,
    rain_in_high numeric(6, 2) NOT NULL,
    PRIMARY KEY (raingauge_id, day)
);

INSERT INTO raingauge_logs_daily (raingauge_id, day, rain_in_low, rain_in_high)
SELECT raingauge_id, date_trunc('day', recorded_at)::date, min(rain_in), max(rain_in)
FROM raingauge_logs, _rollup_cutoff
WHERE date_trunc('day', recorded_at) < _rollup_cutoff.d
GROUP BY raingauge_id, date_trunc('day', recorded_at)
ON CONFLICT (raingauge_id, day) DO NOTHING;

DELETE FROM raingauge_logs USING _rollup_cutoff
WHERE date_trunc('day', raingauge_logs.recorded_at) < _rollup_cutoff.d;

-- === aqsensors_aqlog (measurement/value pairs -- grouped by sensor +
-- measurement type + day, since one row = one (measurement, value) pair
-- rather than one column per metric like the other tables) ================
CREATE TABLE IF NOT EXISTS aqsensors_aqlog_daily (
    aq_sensor_id integer NOT NULL,
    measurement varchar(20) NOT NULL,
    day date NOT NULL,
    value_low numeric(10, 1) NOT NULL,
    value_high numeric(10, 1) NOT NULL,
    PRIMARY KEY (aq_sensor_id, measurement, day)
);

INSERT INTO aqsensors_aqlog_daily (aq_sensor_id, measurement, day, value_low, value_high)
SELECT aq_sensor_id, measurement, date_trunc('day', created_at)::date,
       min(value), max(value)
FROM aqsensors_aqlog, _rollup_cutoff
WHERE date_trunc('day', created_at) < _rollup_cutoff.d
GROUP BY aq_sensor_id, measurement, date_trunc('day', created_at)
ON CONFLICT (aq_sensor_id, measurement, day) DO NOTHING;

DELETE FROM aqsensors_aqlog USING _rollup_cutoff
WHERE date_trunc('day', aqsensors_aqlog.created_at) < _rollup_cutoff.d;

COMMIT;
