from abc import ABC, abstractmethod
from typing import Iterator, Any
from enum import Enum

from ..util import Loggable

class Report(ABC, Loggable):
	class Mode(Enum):
		AGENT = "AGENT"
		GLOBAL = "GLOBAL"

	NAME = "base"
	AUTOLOAD = False
	MODE = Mode.AGENT

	@abstractmethod
	def evaluate(self, *args, **kwargs) -> Iterator[dict[str, Any]]:
		pass

	def name(self) -> str:
		return self.NAME

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.name()})"
