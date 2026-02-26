#!/usr/bin/env bash

# redis-cli flushdb
# redis-cli --raw LRANGE ma:vps:xeno:logs:events 0 0 | jq .
redis-cli --raw LRANGE ma:vps:xeno:logs:events 0 100 | jq .
# redis-cli SCAN 0 MATCH 'ma:vps:*' COUNT 100
# redis-cli KEYS 'ma:vps:*'
