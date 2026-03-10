from abc import ABC, abstractmethod
from typing import Iterator, Any
from enum import Enum
from dataclasses import dataclass

from ..util import Loggable
from ..database import RedisDatabase, PostgresDatabase

class Report(ABC, Loggable):
	class Mode(Enum):
		AGENT = "AGENT"
		GLOBAL = "GLOBAL"

	@dataclass
	class Request:
		redis: RedisDatabase
		pg: PostgresDatabase
		agent: str | None = None

	@dataclass
	class Response:
		status: bool
		info: Any
		agent: str | None = None

	NAME = "base"
	AUTOLOAD = False
	MODE = Mode.AGENT

	@abstractmethod
	def evaluate(self, req: Request) -> Response:
		"""
		In AGENT mode, `req.agent` is populated with a valid Redis key:
			return Response(status, JSON)

		In GLOBAL mode, the Report is expected to do its OWN discovery.
			yield Response(status, JSON, agent)
		"""

		pass

	@property
	def name(self) -> str:
		return self.NAME

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.name})"
