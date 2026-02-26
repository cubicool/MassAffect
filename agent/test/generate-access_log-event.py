#!/usr/bin/env python3

import random
import time

from datetime import datetime, UTC
from pathlib import Path

IPS = [
	"192.168.1.10",
	"104.13.36.111",
	"185.223.152.87",
	"8.8.8.8",
]

METHODS = ["GET", "POST"]

PATHS = [
	"/",
	"/wp-login.php",
	"/api/data",
	"/favicon.ico",
	"/robots.txt",
]

STATUSES = [200, 200, 200, 404, 500]

USER_AGENTS = ["MassAffect/0.0 Test"]

def nginx_time():
    return datetime.now(UTC).strftime("%d/%b/%Y:%H:%M:%S +0000")

def generate_line():
	ip = random.choice(IPS)
	method = random.choice(METHODS)
	path = random.choice(PATHS)
	status = random.choice(STATUSES)
	bytes_sent = random.randint(200, 5000)
	referer = "-"
	ua = random.choice(USER_AGENTS)

	request = f"{method} {path} HTTP/1.1"

	line = (
		f'{ip} - - '
		f'[{nginx_time()}] '
		f'"{request}" '
		f'{status} {bytes_sent} '
		f'"{referer}" '
		f'"{ua}"'
	)

	return line

if __name__ == "__main__":
	print(generate_line())
