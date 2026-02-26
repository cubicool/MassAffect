#!/usr/bin/env python3

import socket
import json
import sys
import time

SOCKET_PATH = "\0massaffect"

def send_payload(payload):
	data = json.dumps(payload).encode()

	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(SOCKET_PATH)
		client.sendall(data)

def send_single():
	payload = {
		"collector": "wordpress",
		"site": "example.com",
		"ts": int(time.time()),
		"metrics": {
			"request_time_ms": 123,
			"db_queries": 17,
			"memory_mb": 42.3
		}
	}

	send_payload(payload)

	print("Sent single event")

def send_batch():
	now = int(time.time())

	payload = [
		{
			"collector": "wordpress",
			"site": "example.com",
			"ts": now,
			"metrics": {
				"request_time_ms": 95,
				"db_queries": 14,
				"memory_mb": 39.1,
			}
		},
		{
			"collector": "wordpress",
			"site": "example.com",
			"ts": now + 1,
			"metrics": {
				"request_time_ms": 211,
				"db_queries": 33,
				"memory_mb": 51.7,
			}
		}
	]

	send_payload(payload)

	print("Sent batch of 2 events")

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: socket_test.py single|batch")

		sys.exit(1)

	mode = sys.argv[1]

	if mode == "single":
		send_single()

	elif mode == "batch":
		send_batch()

	else:
		print("Unknown mode")
