import psycopg
import redis
import time
import re
import textwrap

from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

from . import config

def pg_connect():
	return psycopg.connect(
		**config().system.postgres,
		row_factory=psycopg.rows.dict_row
	)

async def pg_connect_async():
	return await psycopg.AsyncConnection.connect(**config().system.postgres)

@contextmanager
def pg_connection():
	with pg_connect() as con:
		yield con

@contextmanager
def pg_cursor():
	with pg_connection() as con:
		with con.cursor() as cur:
			yield cur

@contextmanager
def pg_execute(q, *args):
	with pg_cursor() as cur:
		cur.execute(q, args or None)

		yield cur

# def redis_connect():
# 	return redis.Redis(decode_responses=True)

def sql_compact(sql: str) -> str:
	"""
	Attempts to remove all extraneous whitespace from an SQL query string;
	NOTE: This is NOT a "security" routine, and is only useful for logging/debugging.
	"""

	return re.sub(r"\s+", " ", textwrap.dedent(sql).strip())

def to_epoch(t):
	if t is None:
		return None

	if isinstance(t, (int, float)):
		return int(t)

	if isinstance(t, datetime):
		return int(t.timestamp())

	raise TypeError(f"Unsupported time type: {type(t)}")

def ago(**kwargs):
	return datetime.utcnow() - timedelta(**kwargs)

def _parse_absolute(s: str):
	try:
		dt = datetime.fromisoformat(s)

		if dt.tzinfo is None:
			dt = dt.replace(tzinfo=timezone.utc)

		return dt

	except Exception:
		raise ValueError(f"Invalid absolute time: {s!r}")

def _parse_duration(s: str):
	try:
		value, unit = s.strip().lower().split()
		value = int(value)

	except Exception:
		raise ValueError(f"Invalid duration: {s!r}")

	if unit.startswith("second"):
		return timedelta(seconds=value)

	elif unit.startswith("minute"):
		return timedelta(minutes=value)

	elif unit.startswith("hour"):
		return timedelta(hours=value)

	elif unit.startswith("day"):
		return timedelta(days=value)

	raise ValueError(f"Invalid duration unit: {unit}")

def parse_time(*, start: str, end: str | None, duration: str | None):
	if not start:
		raise ValueError("start is required")

	if end and duration:
		raise ValueError("cannot specify both end and duration")

	if not end and not duration:
		raise ValueError("must specify either end or duration")

	start_dt = _parse_absolute(start)

	if end:
		end_dt = _parse_absolute(end)

	else:
		delta = _parse_duration(duration)
		end_dt = start_dt + delta

	return start_dt, end_dt

def filter_agent(agent):
	if not agent:
		return None

	return "agent = %s", [agent]

def filter_collector(collector):
	if not collector:
		return None

	return "collector = %s", [collector]

def filter_time(*, start=None, end=None):
	if not start and not end:
		return None

	clauses = []
	args = []

	if start:
		clauses.append("ts >= %s")
		args.append(to_epoch(start))

	if end:
		clauses.append("ts <= %s")
		args.append(to_epoch(end))

	return " AND ".join(clauses), args

def build_where(*filters):
	clauses = ["TRUE"]
	args = []

	for f in filters:
		if not f:
			continue
		clause, f_args = f
		clauses.append(clause)
		args.extend(f_args)

	return " AND ".join(clauses), args

class PostgresDatabase:
	def __init__(self, debug=False):
		self._conn = pg_connect()
		self._debug = debug

	def _execute(self, sql, args=(), *, one=False):
		if self._debug:
			print(f"SQL: {sql_compact(sql)} | ARGS: {args}")

		with self._conn.cursor() as cur:
			cur.execute(sql, args)

			return cur.fetchone() if one else cur.fetchall()

	def query(self, sql: str, *args):
		return self._execute(sql, args)

	def query_one(self, sql: str, *args):
		return self._execute(sql, args, one=True)

class RedisDatabase:
	def __init__(self):
		self.r = redis.Redis(decode_responses=True)

	@property
	def agents(self):
		return self.r.smembers("ma:agent:index")

	def collectors(self, agent):
		return self.r.smembers(f"ma:agent:{agent}:collectors:index")

	def report_state(self, agent, report):
		return self.r.get(f"ma:agent:{agent}:report:{report}")

	def set_report_state(self, agent, report, payload):
		self.r.set(f"ma:agent:{agent}:report:{report}", json.dumps(payload))

	def clear_report_state(self, agent, report):
		self.r.delete(f"ma:agent:{agent}:report:{report}")

__all__ = (
    "pg_connect",
    "pg_connect_async",
    "pg_connection",
    "pg_cursor",
    "pg_execute",
    "sql_compact",
    "to_epoch",
    "ago",
    "parse_time",
    "filter_agent",
    "filter_collector",
    "filter_time",
    "build_where",
    "PostgresDatabase",
    "RedisDatabase",
)
