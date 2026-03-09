#!/usr/bin/env bash

# For clearing out Redis when we want to start over.
if [ "${1}" = "purge" ]; then
	redis-cli flushdb

# Agent Range Events (are); requires second argument like "foo:system" or
# "bar:logs.nginx", dumping all matching values.
elif [ "${1}" = "are" ]; then
	shift 1

	redis-cli --raw LRANGE "ma:agent:${1}:events" 0 -1

# ???
elif [ "${1}" = "scan" ]; then
	redis-cli --scan | while read key; do
		echo "$(redis-cli TYPE "${key}") ${key}"
	done | sort

else
	echo "Uknown command: ${1}"

	exit 1
fi

# redis-cli SCAN 0 MATCH 'ma:agent:*' COUNT 100
# redis-cli KEYS 'ma:agent:*'
# ./ma-redis.sh | jq 'select(.metrics.source == "/var/log/syslog")'
