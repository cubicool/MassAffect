from abc import ABC, abstractmethod
from typing import Iterator, Any

from .. import Loggable

class Report(ABC, Loggable):
	NAME = "base"
	AUTOLOAD = False

	@abstractmethod
	def evaluate(self) -> Iterator[dict[str, Any]]:
		pass

	def name(self) -> str:
		return self.NAME

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.name()})"
