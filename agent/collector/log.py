#vimrun! python3 -m collector.system

import json
import os

from pathlib import Path

from . import BaseCollector, cli_run

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
                if size < offset:
                    offset = 0  # truncated
            else:
                offset = 0  # rotated

        lines = []

        with self.path.open("r") as f:
            f.seek(offset)
            for line in f:
                lines.append(line.rstrip("\n"))
            new_offset = f.tell()

        self.store.update(self.path, inode, new_offset)

        return lines

class RawParser:
    def parse(self, line: str) -> dict:
        return {"raw": line}

import re

NGINX_COMBINED_RE = re.compile(
    r'"(?P<remote_addr>\S+) '         # IP
    r'\S+ \S+ '                       # ignore ident/user
    r'\[(?P<time_local>[^\]]+)\] '    # time
    r'"(?P<request>[^"]*)" '          # request line
    r'(?P<status>\d{3}) '             # status
    r'(?P<body_bytes_sent>\S+) '      # bytes
    r'"(?P<http_referer>[^"]*)" '     # referer
    r'"(?P<http_user_agent>[^"]*)"'   # user agent
)

class NginxParser:
    def parse(self, line: str) -> dict | None:
        m = NGINX_COMBINED_RE.match(line)
        if not m:
            return None

        data = m.groupdict()

        # Optional coercion
        data["status"] = int(data["status"])
        data["body_bytes_sent"] = (
            int(data["body_bytes_sent"])
            if data["body_bytes_sent"].isdigit()
            else 0
        )

        # Split request line
        if data["request"]:
            parts = data["request"].split()
            if len(parts) == 3:
                data["method"], data["path"], data["protocol"] = parts

        return data

class LogCollector(BaseCollector):
    name = "logs"

    def __init__(self,
                 patterns=None,
                 parser=None,
                 state_file=None):
        self.patterns = patterns or [
            # "/var/log/nginx/access*.log"
            "/var/log/syslog"
        ]
        self.parser = parser or RawParser()
        self.state = LogStateStore(
            Path(state_file or ".massaffect_logstate.json")
        )

    def collect(self):
        events = []

        for pattern in self.patterns:
            base = Path("/")
            for path in base.glob(pattern.lstrip("/")):
                cursor = LogFileCursor(path, self.state)
                for line in cursor.read_new():
                    parsed = self.parser.parse(line)
                    events.append({
                        "source": str(path),
                        "event": parsed,
                    })

        self.state.save()

        return {
            "collector": self.name,
            "events": events,
        }

cli_run(LogCollector, __name__)
