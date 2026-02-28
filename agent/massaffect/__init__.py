import os
import sys
import json
import logging
import importlib
import importlib.util
import pkgutil
import pathlib

class Loggable:
	def __init_subclass__(cls):
		# cls.log = logging.getLogger(f"{cls.__module__}.{cls.__name__}")
		cls.log = logging.getLogger(f"{cls.__name__}")

_CONFIG = None

def config():
	global _CONFIG

	if _CONFIG is not None:
		return _CONFIG

	path = os.environ.get("MASSAFFECT_CONFIG")

	if not path:
		raise RuntimeError(
			"MASSAFFECT_CONFIG environment variable not set"
		)

	path = pathlib.Path(path)

	if not path.exists():
		raise RuntimeError(f"Config file not found: {path}")

	spec = importlib.util.spec_from_file_location("massaffect_user_CONFIG", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)

	_CONFIG = module

	return _CONFIG

def discover_collectors():
	import massaffect.collector

	collectors = []

	for _, module_name, _ in pkgutil.iter_modules(massaffect.collector.__path__):
		module = importlib.import_module(f"massaffect.collector.{module_name}")

		for obj in module.__dict__.values():
			if (
				isinstance(obj, type)
				and issubclass(obj, massaffect.collector.Collector)
				and obj is not massaffect.collector.Collector
			):
				collectors.append(obj)

	return collectors

def create_collectors():
	instances = []
	classes = discover_collectors()
	class_map = {cls.__name__: cls for cls in classes}

	# If AUTOLOAD is set...
	for cls in classes:
		if getattr(cls, "AUTOLOAD", False):
			instances.append(cls())

	# Otherwise, check for some config knobs!
	for entry in getattr(config(), "COLLECTORS", []):
		cls = class_map.get(entry["type"])

		if not cls:
			raise ValueError(f"Unknown collector: {entry['type']}")

		instances.append(cls(**entry.get("config", {})))

	return instances
