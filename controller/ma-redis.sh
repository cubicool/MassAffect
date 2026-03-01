#!/usr/bin/env bash

# For clearing out Redis when we want to start over.
if [ "${1}" = "purge" ]; then
	redis-cli flushdb

# VPS Range Events (vre); requires second argument like "foo:system" or
# "bar:logs.nginx", dumping all matching values.
elif [ "${1}" = "vre" ]; then
	shift 1

	redis-cli --raw LRANGE "ma:vps:${1}:events" 0 -1

else
	echo "Uknown command: ${1}"

	exit 1
fi

# redis-cli SCAN 0 MATCH 'ma:vps:*' COUNT 100
# redis-cli KEYS 'ma:vps:*'
# ./ma-redis.sh | jq 'select(.metrics.source == "/var/log/syslog")'
