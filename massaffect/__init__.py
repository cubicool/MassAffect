import os
import sys
import json
import logging
import pkgutil
import pathlib
import importlib

from .config import load_config
from .plugins import create_plugins

class Loggable:
	def __init_subclass__(cls):
		cls.log = logging.getLogger(f"{cls.__name__}")

_CONFIG = None

def config():
	global _CONFIG

	if _CONFIG is not None:
		return _CONFIG

	path = os.environ.get("MASSAFFECT_CONFIG")

	if not path:
		raise RuntimeError("MASSAFFECT_CONFIG environment variable not set")

	path = pathlib.Path(path)

	if not path.exists():
		raise RuntimeError(f"Config file not found: {path}")

	_CONFIG = load_config(path)

	return _CONFIG

def create_collectors():
	import massaffect.collector

	# If AUTOLOAD is set...
	instances = create_plugins(massaffect.collector, massaffect.collector.Collector)

	# Otherwise, add everything defined in the TOML config.
	if hasattr(config(), "agent") and hasattr(config().agent, "collectors"):
		instances.extend(config().agent.collectors)

	return instances

def create_reports():
	import massaffect.report

	# If AUTOLOAD is set...
	instances = create_plugins(massaffect.report, massaffect.report.Report)

	# Otherwise, add everything defined in the TOML config.
	if hasattr(config(), "reporter") and hasattr(config().reporter, "reports"):
		instances.extend(config().reporter.reports)

	return instances
