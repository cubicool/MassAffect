#!/usr/bin/env bash

# redis-cli flushdb
# redis-cli SCAN 0 MATCH 'ma:vps:*' COUNT 100
# redis-cli KEYS 'ma:vps:*'

redis-cli --raw LRANGE "ma:vps:${1}:events" 0 -1

# ./ma-redis.sh | jq 'select(.metrics.source == "/var/log/syslog")'
