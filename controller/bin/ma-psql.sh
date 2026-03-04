#!/usr/bin/env bash

function ma_psql() {
	psql -U massaffect -h localhost -d massaffect -t -A ${*}
}

function ma_psql_ascii() {
	psql -U massaffect -h localhost -d massaffect ${*}
}

function ma_psql_query_ip() {
	ma_psql <<-EOF
		SELECT metrics
		FROM events
		WHERE metrics->>'remote_addr' = '${1}';
	EOF
}

# To RESET EVERYTHING, run:
if [ "${1}" = "purge" ]; then
	echo "TRUNCATE TABLE events RESTART IDENTITY;" | ma_psql

elif [ "${1}" = "query" -o "${1}" = "q" ]; then
	shift 1

	echo "${*}" | ma_psql_ascii

elif [ "${1}" = "rows" ]; then
	shift 1

	if [ "${1}" = "dump" ]; then
		# echo "SELECT * FROM events LIMIT 20;" | ma_psql
		echo "SELECT * FROM events;" | ma_psql
	
	elif [ "${1}" = "count" ]; then
		echo "SELECT COUNT(*) FROM events;" | ma_psql

	else
		echo "Unknown 'rows' command: ${1}"

		exit 2
	fi

elif [ "${1}" = "logs.nginx" ]; then
	echo "SELECT metrics FROM events WHERE collector = 'logs.nginx'" | ma_psql

elif [ "${1}" = "ip" ]; then
	shift 1

	ma_psql_query_ip "${1}"

else
	echo "Unknown command: ${1}"

	exit 1
fi

exit 0

# Busiest sites?
ma_psql_ascii <<EOF
SELECT
  metrics->>'source' AS logfile,
  count(*) AS hits
FROM events
GROUP BY logfile
ORDER BY hits DESC;
EOF

# Rows with NO USER AGENT! Boo! :(
function ma_psql_query_noua() {
ma_psql <<EOF
SELECT
  metrics->>'remote_addr' AS ip,
  count(*) AS hits
FROM events
WHERE metrics->>'http_user_agent' IS NULL
   OR metrics->>'http_user_agent' = ''
GROUP BY ip
ORDER BY hits DESC;
EOF
}

ma_psql_query_noua

exit 0


# TODO: Temporary until I comment out the testing queries below!
exit 0

# echo "SELECT * FROM events WHERE metrics->>'path' = '/wp-login.php';" | ma_psql
# Shows how many queries each IP made; insane!
# echo "SELECT metrics->>'remote_addr', count(*) FROM events GROUP BY 1 ORDER BY 2 DESC;" | ma_psql

# How long ago did the web queries occur?
ma_psql <<EOF
SELECT
    NOW() - (metrics->>'time_local')::timestamptz AS age
FROM events
ORDER BY ts DESC
LIMIT 10;
EOF

# Or, see who is hitting a particular route/path the most!
ma_psql <<EOF
SELECT
  metrics->>'remote_addr' AS ip,
  count(*) AS hits
FROM events
WHERE metrics->>'path' = '/wp-login.php'
GROUP BY ip
ORDER BY hits DESC;
EOF

# Grab all the 200 response codes...
# ma_psql <<EOF
# SELECT * FROM events WHERE metrics @> '{"status":200}';
# EOF

# Top user-agents...
ma_psql <<EOF
SELECT
  metrics->>'http_user_agent' AS ua,
  count(*) AS hits
FROM events
GROUP BY ua
ORDER BY hits DESC
LIMIT 20;
EOF

# 404 Scanners?
ma_psql <<EOF
SELECT
  metrics->>'source' AS logfile,
  count(*) AS hits
FROM events
WHERE metrics->>'status' = '404'
GROUP BY logfile
ORDER BY hits DESC;
EOF

# Analytics, baby! By hour...
ma_psql <<EOF
SELECT
  date_trunc('hour', to_timestamp(ts)) AS hour,
  count(*) AS events
FROM events
GROUP BY hour
ORDER BY hour DESC;
EOF

# ...and analytics by MINUTE!
ma_psql <<EOF
SELECT
  date_trunc('minute', to_timestamp(ts)) AS minute,
  count(*) AS events
FROM events
GROUP BY minute
ORDER BY minute DESC;
EOF
