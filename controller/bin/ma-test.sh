#!/usr/bin/env bash

BODY='{"hostname":"xeno"}'; \
SIG=$(echo -n $BODY | openssl dgst -sha256 -hmac "supersecret" | awk '{print $2}'); \
curl http://ambaince.com/monitor/system \
  -H "Content-Type: application/json" \
  -H "x-agent-signature: $SIG" \
  -d "$BODY"

