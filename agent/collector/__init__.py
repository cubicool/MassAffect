from abc import ABC, abstractmethod

import sys
import json

class BaseCollector(ABC):
	name = "base"
	autoload = False

	@abstractmethod
	def collect(self) -> dict:
		pass

def _coerce(value: str):
	"""
	Coerce string to int, float, or str (in that order).
	Supports quoted strings.
	"""

	# Strip surrounding quotes if present
	if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
		return value[1:-1]

	# Try int
	try:
		return int(value)

	except ValueError:
		pass

	# Try float
	try:
		return float(value)

	except ValueError:
		pass

	# Fallback to string
	return value

def parse_argv(argv):
	"""
	Parses argv-style list into (args, kwargs).

	Example:
		./foo.py abc 1 foo=2 bar=3.4 baz="hello"
	"""

	args = []
	kwargs = {}

	for token in argv:
		if "=" in token:
			key, value = token.split("=", 1)
			kwargs[key] = _coerce(value)

		else:
			args.append(_coerce(token))

	return args, kwargs

def cli_run(collector_cls, module_name: str):
	if module_name == "__main__":
		print(json.dumps(collector_cls(parse_argv(sys.argv[1:])).collect(), indent=2))
