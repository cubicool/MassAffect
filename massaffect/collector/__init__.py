from abc import ABC, abstractmethod
from typing import Iterator, Any

from ..util import Loggable

class Collector(ABC, Loggable):
	NAME = "base"
	AUTOLOAD = False

	@abstractmethod
	# def collect(self) -> Iterator[Dict[str, Any]]:
	def collect(self) -> Iterator[dict[str, Any]]:
		pass

	@property
	def name(self) -> str:
		return self.NAME

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.name})"
