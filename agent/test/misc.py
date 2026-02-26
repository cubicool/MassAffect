#!/usr/bin/env python3
#vimrun! ./test.py

import sys
import json

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

def test_parse_argv():
	from collector import parse_argv

	print(parse_argv(sys.argv[1:]))

def test_logcollector_raw():
	from collector.log import LogCollector

	lc = LogCollector(state_file=".ma_syslog.json")

	for c in lc.collect():
		print(json.dumps(c, indent=2))

def test_logcollector_nginx():
	from collector.log import LogCollector, NginxParser

	lc = LogCollector(parser=NginxParser(), patterns=["/tmp/access.log"], state_file=".ma_nginx.json")

	for c in lc.collect():
		print(json.dumps(c, indent=2))

def test_setup_collectors():
	from agent import discover_collectors, create_collectors

	for c in discover_collectors():
		print(f"{c}: autoload={c.autoload}")

	for c in create_collectors():
		print(f"{c}")

if __name__ == "__main__":
	test_logcollector_raw()
	test_logcollector_nginx()

	# test_setup_collectors()
