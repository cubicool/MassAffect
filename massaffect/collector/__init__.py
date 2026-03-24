from abc import ABC, abstractmethod
from typing import Iterator, Any

from ..util import Loggable
from ..state import MemoryStateStore

class Collector(ABC, Loggable):
	NAME = "base"
	AUTOLOAD = False
	# STATE = MemoryStateStore

	def __init__(self, *args, **kwargs):
		self.state = MemoryStateStore()

	@abstractmethod
	# def collect(self) -> Iterator[Dict[str, Any]]:
	def collect(self) -> Iterator[dict[str, Any]]:
		pass

	@property
	def name(self) -> str:
		return self.NAME

	@property
	def tasks(self) -> list:
		return []

	async def start(self):
		pass

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.name})"

	# def _init_state(self):
	# 	state_factory = self.STATE
    #
	# 	# support lambdas or classes
	# 	if callable(state_factory):
	# 		return state_factory()
    #
	# 	return state_factory()
