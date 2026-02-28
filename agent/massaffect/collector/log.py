import json
import re

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
# from typing import Optional

from . import Collector

class LogStateStore:
	def __init__(self, path: Path):
		self.path = path

		self._state = {}
		self._load()

	def _load(self):
		if self.path.exists():
			self._state = json.loads(self.path.read_text())

	def save(self):
		self.path.parent.mkdir(parents=True, exist_ok=True)
		self.path.write_text(json.dumps(self._state, indent=2))

	def get(self, path: Path):
		return self._state.get(str(path))

	def update(self, path: Path, inode: int, offset: int):
		self._state[str(path)] = {
			"inode": inode,
			"offset": offset,
		}

class LogFileCursor:
	def __init__(self, path: Path, store: LogStateStore):
		self.path = path
		self.store = store

	def read_new(self):
		if not self.path.exists():
			return []

		st = self.path.stat()
		inode = st.st_ino
		size = st.st_size
		saved = self.store.get(self.path)
		offset = 0

		if saved:
			if saved["inode"] == inode:
				offset = saved["offset"]

				# File was probably truncated.
				if size < offset:
					offset = 0

			# Likely rotated to .1, .2, etc.
			else:
				offset = 0

		lines = []

		with self.path.open("r") as f:
			f.seek(offset)

			for line in f:
				lines.append(line.rstrip("\n"))

			new_offset = f.tell()

		self.store.update(self.path, inode, new_offset)

		return lines

class Parser(ABC):
	NAME = ""

	@abstractmethod
	def parse(self, line: str) -> dict:
		pass

class RawParser:
	NAME = "raw"

	# def parse(self, line: str) -> Optional[dict]:
	def parse(self, line: str) -> dict:
		return {"raw": line}

NGINX_COMBINED_RE = re.compile(
	r'^"?'                          # optional outer quote (some logs wrap entire line)
	r'(?P<remote_addr>\S+) '        # $remote_addr (client IP)
	r'\S+ \S+ '                     # $remote_user / ident (usually "-" "-")
	r'\[(?P<time_local>[^\]]+)\] '  # [$time_local]
	r'"(?P<request>[^"]*)" '        # "$request" (method path protocol)
	r'(?P<status>\d{3}) '           # $status (HTTP status code)
	r'(?P<body_bytes_sent>\S+) '    # $body_bytes_sent (may be "-")
	r'"(?P<http_referer>[^"]*)" '   # "$http_referer"
	r'"(?P<http_user_agent>[^"]*)"' # "$http_user_agent"
	r'(?:\s+.*)?'                   # optional extra fields (e.g., request_id, upstream data)
	r'"?$'                          # optional closing outer quote
)

OLS_ACCESS_RE = re.compile(
	r'^"?'                         # optional outer quote
	r'(?P<vhost>\S+) '             # %v
	r'(?P<remote_addr>\S+) '       # %h
	r'\S+ '                        # %l (ident, usually -)
	r'\S+ '                        # %u (user, usually -)
	r'\[(?P<time_local>[^\]]+)\] ' # %t
	r'"(?P<request>[^"]*)" '       # "%r"
	r'(?P<status>\d{3}) '          # %>s
	r'(?P<body_bytes_sent>\S+)'    # %b
	r'"?$'                         # optional closing quote
)

class NginxParser:
	NAME = "nginx"

	# def parse(self, line: str) -> Optional[dict]:
	def parse(self, line: str) -> dict | None:
		m = NGINX_COMBINED_RE.match(line)

		if not m:
			return None

		data = m.groupdict()

		# Optional coercion
		data["status"] = int(data["status"])
		data["body_bytes_sent"] = (
			int(data["body_bytes_sent"])
			if data["body_bytes_sent"].isdigit() else 0
		)

		# Normalize timestamp
		tl = data.get("time_local")

		if tl:
			try:
				data["time_local"] = datetime.strptime(
					tl,
					"%d/%b/%Y:%H:%M:%S %z"
				).astimezone(timezone.utc).isoformat()

			except Exception:
				data["time_local"] = None

		# Split request line
		if data["request"]:
			parts = data["request"].split()

			if len(parts) == 3:
				data["method"], data["path"], data["protocol"] = parts

		return data

class LogCollector(Collector):
	NAME = "logs"

	def __init__(self,
		patterns=None,
		parser=None,
		state_file=None
	):
		self.patterns = patterns or [
			# "/var/log/nginx/access*.log"
			"/var/log/syslog"
		]

		self.parser = parser or RawParser()
		self.state = LogStateStore(Path(state_file or ".ma_logstate.json"))

	def name(self):
		n = self.NAME

		if self.parser.NAME:
			n = f"{n}.{self.parser.NAME}"

		return n

	def collect(self):
		for pattern in self.patterns:
			base = Path("/")

			for path in base.glob(pattern.lstrip("/")):
				cursor = LogFileCursor(path, self.state)

				for line in cursor.read_new():
					parsed = self.parser.parse(line)

					if not parsed:
						continue

					yield {
						"source": str(path),
						**parsed,
					}

		self.state.save()
