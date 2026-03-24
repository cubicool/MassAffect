psql -U massaffect -h localhost -d massaffect <<EOF
\echo '=============================='
\echo 'MassAffect: Basic Overview'
\echo '=============================='

-- Total events
SELECT COUNT(*) AS total_events FROM events;

-- Data time range
SELECT
    to_timestamp(MIN(ts)) AS start_time,
    to_timestamp(MAX(ts)) AS end_time
FROM events;

\echo ''
\echo '=============================='
\echo 'Events Per Hour'
\echo '=============================='

SELECT
    date_trunc('hour', to_timestamp(ts)) AS hour,
    COUNT(*) AS events
FROM events
GROUP BY hour
ORDER BY hour;

\echo ''
\echo '=============================='
\echo 'Events Per Minute (recent sample)'
\echo '=============================='

SELECT
    date_trunc('minute', to_timestamp(ts)) AS minute,
    COUNT(*) AS events
FROM events
WHERE ts > (SELECT MAX(ts) - 3600 FROM events)  -- last hour
GROUP BY minute
ORDER BY minute;

\echo ''
\echo '=============================='
\echo 'Per-Agent Activity'
\echo '=============================='

SELECT
    agent,
    COUNT(*) AS total,
    ROUND(COUNT(*) / 12.0, 2) AS per_hour_estimate
FROM events
GROUP BY agent
ORDER BY total DESC;

\echo ''
\echo '=============================='
\echo 'Per-Collector Activity'
\echo '=============================='

SELECT
    collector,
    COUNT(*) AS total
FROM events
GROUP BY collector
ORDER BY total DESC;

\echo ''
\echo '=============================='
\echo 'Agent + Collector Breakdown'
\echo '=============================='

SELECT
    agent,
    collector,
    COUNT(*) AS total
FROM events
GROUP BY agent, collector
ORDER BY total DESC;

\echo ''
\echo '=============================='
\echo 'Top 10 Busiest Hours'
\echo '=============================='

SELECT
    date_trunc('hour', to_timestamp(ts)) AS hour,
    COUNT(*) AS events
FROM events
GROUP BY hour
ORDER BY events DESC
LIMIT 10;

\echo ''
\echo '=============================='
\echo 'EXAMPLE: xmlrpc IDIOTS'
\echo '=============================='

SELECT
    metrics->>'remote_addr' AS ip,
    COUNT(*) AS hits
FROM events
WHERE collector = 'logs.nginx'
  AND metrics->>'request' ILIKE '%xmlrpc.php%'
GROUP BY ip
ORDER BY hits DESC
LIMIT 20;

\echo ''
\echo '=============================='
\echo 'EXAMPLE: xmlrpc Total Percent'
\echo '=============================='

SELECT
    COUNT(*) AS xmlrpc_hits,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM events), 2) AS percent_of_total
FROM events
WHERE collector = 'logs.nginx'
  AND metrics->>'request' ILIKE '%xmlrpc.php%';

\echo ''
\echo '=============================='
\echo 'Database Size'
\echo '=============================='

SELECT
    pg_size_pretty(pg_total_relation_size('events_2026_03')) AS events_partition_size;

\echo ''
\echo '=============================='
\echo 'Done.'
\echo '=============================='
EOF
