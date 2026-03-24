# from __future__ import annotations

import json

from pathlib import Path
from typing import Any

# ================================================================================================
# Base interface

class StateStore:
	def get(self, key: str, default: Any = None) -> Any:
		raise NotImplementedError

	def set(self, key: str, value: Any) -> None:
		raise NotImplementedError

	def delete(self, key: str) -> None:
		raise NotImplementedError

	def save(self) -> None:
		pass


# ================================================================================================
# In-memory (default)

class MemoryStateStore(StateStore):
	def __init__(self):
		self._state: dict[str, Any] = {}

	def get(self, key: str, default: Any = None) -> Any:
		return self._state.get(key, default)

	def set(self, key: str, value: Any) -> None:
		self._state[key] = value

	def delete(self, key: str) -> None:
		self._state.pop(key, None)


# ================================================================================================
# File-backed (persistent)

class FileStateStore(StateStore):
	def __init__(self, path: Path):
		self.path = path

		self._state: dict[str, Any] = {}
		self._load()

	def _load(self) -> None:
		if self.path.exists():
			self._state = json.loads(self.path.read_text())

	def save(self) -> None:
		self.path.parent.mkdir(parents=True, exist_ok=True)
		self.path.write_text(json.dumps(self._state, indent=2))

	def get(self, key: str, default: Any = None) -> Any:
		return self._state.get(key, default)

	def set(self, key: str, value: Any) -> None:
		self._state[key] = value

	def delete(self, key: str) -> None:
		self._state.pop(key, None)
