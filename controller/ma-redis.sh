#!/usr/bin/env bash

redis-cli --raw LRANGE collector:index 0 -1 | \
	sed 's/^/collector:/' | \
	xargs redis-cli --raw MGET
