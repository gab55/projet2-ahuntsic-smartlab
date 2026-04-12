-- queries demonstration
-- 1 - 2 requetes de plus
-- last 10 by time

SELECT * FROM events ORDER BY ts_utc DESC LIMIT 10;



SELECT * FROM telemetry ORDER BY ts_utc DESC LIMIT 10;


-- average over time
SELECT
    DATE(telemetry.ts_utc) as Day,
    HOUR(telemetry.ts_utc) as Hour,
    AVG(value) as AvgHourTemp,
    unit as unit

FROM telemetry
GROUP BY Day, Hour
order by Day DESC, Hour DESC;

