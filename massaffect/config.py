from __future__ import annotations

import os

try:
	# In Python 3.11+, this is fine.
	import tomllib

except ModuleNotFoundError:
	# In Python 3.10 or thereabouts, we'll need to install tomli.
	import tomli as tomllib

from pathlib import Path
from dataclasses import dataclass
from typing import Any

# Add additional collector/parser types here as needed.
from .collector.log import LogCollector, NginxParser, RawParser

PARSERS = {
	"raw": RawParser,
	"nginx": NginxParser,
}

COLLECTORS = {
	"LogCollector": LogCollector,
}

@dataclass(slots=True)
class SystemConfig:
	redis: dict[str, Any] | None
	postgres: dict[str, Any] | None

@dataclass(slots=True)
class AgentConfig:
	# hostname: str
	interval: int
	compression_threshold: int
	socket_name: str
	controller_url: str
	agent_secret: str
	collectors: list[Any]

@dataclass(slots=True)
class ReporterConfig:
	interval: int
	rules: list[dict[str, Any]]

@dataclass(slots=True)
class Config:
	system: SystemConfig | None
	agent: AgentConfig | None
	reporter: ReporterConfig | None

class ConfigError(RuntimeError):
	pass

def _expand_env(value: Any) -> Any:
	"""
	Recursively expand ${VAR} environment variables.
	If variable is missing, raise loudly.
	"""

	if isinstance(value, str):
		if value.startswith("${") and value.endswith("}"):
			var = value[2:-1]

			if var not in os.environ:
				raise ConfigError(f"Missing required environment variable: {var}")

			return os.environ[var]

		return value

	if isinstance(value, list):
		return [_expand_env(v) for v in value]

	if isinstance(value, dict):
		return {k: _expand_env(v) for k, v in value.items()}

	return value

def load_config(path: str | Path) -> Config:
	path = Path(path)

	if not path.exists():
		raise ConfigError(f"Config file not found: {path}")

	with path.open("rb") as f:
		raw = tomllib.load(f)

	raw = _expand_env(raw)

	# System Section
	system = None

	if "system" in raw:
		infra = raw["system"]

		system = SystemConfig(
			redis=infra.get("redis"),
			postgres=infra.get("postgres")
		)

	# Agent Section
	agent = None

	if "agent" in raw:
		agent = raw["agent"]

		try:
			# hostname = agent["hostname"]
			controller_url = agent["controller_url"]
			agent_secret = agent["agent_secret"]

		except KeyError as e:
			raise ConfigError(f"Missing required agent config field: {e.args[0]}")

		try:
			interval = int(agent.get("interval", 15))
			compression_threshold = int(agent.get("compression_threshold", 512))

		except ValueError:
			raise ConfigError("interval and compression_threshold must be integers")

		socket_name = "\0" + agent.get("socket_name", "massaffect")

		collectors = []

		for entry in agent.get("collectors", []):
			if "type" not in entry:
				raise ConfigError("Collector entry missing 'type' field")

			type_name = entry["type"]

			if type_name not in COLLECTORS:
				raise ConfigError(f"Unknown collector type: {type_name}")

			cls = COLLECTORS[type_name]

			config = dict(entry)
			config.pop("type")

			if "parser" in config:
				parser_name = config["parser"]

				if parser_name not in PARSERS:
					raise ConfigError(f"Unknown parser: {parser_name}")

				config["parser"] = PARSERS[parser_name]()

			try:
				collectors.append(cls(**config))

			except TypeError as e:
				raise ConfigError(
					f"Invalid configuration for collector '{type_name}': {e}"
				)

		agent = AgentConfig(
			# hostname=hostname,
			interval=interval,
			compression_threshold=compression_threshold,
			socket_name=socket_name,
			controller_url=controller_url,
			agent_secret=agent_secret,
			collectors=collectors
		)

	# Reporter Section
	reporter = None

	if "reporter" in raw:
		reporter = raw["reporter"]

		try:
			interval = int(reporter.get("interval", 10))

		except ValueError:
			raise ConfigError("reporter interval must be integer")

		rules = reporter.get("rules", [])

		reporter = ReporterConfig(
			interval=interval,
			rules=rules
		)

	return Config(
		system=system,
		agent=agent,
		reporter=reporter
	)
