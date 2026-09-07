-- preview_history_rollup.sql
--
-- READ-ONLY. Run this first, before rollup_and_prune_history.sql, to see
-- how many rows/days/devices would actually be affected. Nothing here
-- writes or deletes anything.
--
-- Cutoff matches rollup_and_prune_history.sql exactly: whole calendar
-- days strictly before (today's date minus 6 months) -- see that
-- script's header comment for why it's day-aligned rather than a bare
-- "6 months ago" timestamp.
--
-- Usage: psql -h <host> -U <user> -d <db> -f preview_history_rollup.sql

\pset pager off

WITH cutoff AS (SELECT date_trunc('day', now() - interval '6 months')::date AS d)

SELECT 'tstats_tstatlog' AS table_name,
       count(*) AS rows_to_delete,
       count(DISTINCT date_trunc('day', created_at)) AS distinct_days,
       count(DISTINCT romid_id) AS distinct_devices,
       min(created_at) AS oldest, max(created_at) AS newest_affected
FROM tstats_tstatlog, cutoff
WHERE date_trunc('day', created_at) < cutoff.d

UNION ALL
SELECT 'tstats_thermohygrostatlog', count(*),
       count(DISTINCT date_trunc('day', created_at)), count(DISTINCT thermohygrometer_id),
       min(created_at), max(created_at)
FROM tstats_thermohygrostatlog, cutoff
WHERE date_trunc('day', created_at) < cutoff.d

UNION ALL
SELECT 'energy_circuit_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT circuit_id),
       min(recorded_at), max(recorded_at)
FROM energy_circuit_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'ikea_device_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT device_id),
       min(recorded_at), max(recorded_at)
FROM ikea_device_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'ring_device_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT device_id),
       min(recorded_at), max(recorded_at)
FROM ring_device_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'hvac_zone_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT hvac_zone_id),
       min(recorded_at), max(recorded_at)
FROM hvac_zone_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'anemometer_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT anemometer_id),
       min(recorded_at), max(recorded_at)
FROM anemometer_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'photo_uvmeter_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT photo_uvmeter_id),
       min(recorded_at), max(recorded_at)
FROM photo_uvmeter_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'raingauge_logs', count(*),
       count(DISTINCT date_trunc('day', recorded_at)), count(DISTINCT raingauge_id),
       min(recorded_at), max(recorded_at)
FROM raingauge_logs, cutoff
WHERE date_trunc('day', recorded_at) < cutoff.d

UNION ALL
SELECT 'aqsensors_aqlog', count(*),
       count(DISTINCT date_trunc('day', created_at)), count(DISTINCT (aq_sensor_id, measurement)),
       min(created_at), max(created_at)
FROM aqsensors_aqlog, cutoff
WHERE date_trunc('day', created_at) < cutoff.d

ORDER BY table_name;
