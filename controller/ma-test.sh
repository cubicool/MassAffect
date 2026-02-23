#!/usr/bin/env bash

BODY='{"hostname":"testbox"}'; \
SIG=$(echo -n $BODY | openssl dgst -sha256 -hmac "SECRET" | awk '{print $2}'); \
curl http://localhost:3000/monitor/system \
  -H "Content-Type: application/json" \
  -H "x-agent-signature: $SIG" \
  -d "$BODY"

