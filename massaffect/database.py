import psycopg
import redis
import time
import re
import textwrap

from datetime import datetime, timedelta
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

def ago(*, seconds=0, minutes=0, hours=0, days=0):
	return datetime.utcnow() - timedelta(
		seconds=seconds,
		minutes=minutes,
		hours=hours,
		days=days
	)

def filter_agent(agent):
	if not agent:
		return None
	return "agent = %s", [agent]

def filter_collector(collector):
	if not collector:
		return None
	return "collector = %s", [collector]

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

	def _to_epoch(self, t):
		if t is None:
			return None

		if isinstance(t, (int, float)):
			return int(t)

		if isinstance(t, datetime):
			return int(t.timestamp())

		raise TypeError(f"Unsupported time type: {type(t)}")

	def _execute(self, sql, args, *, one=False):
		if self._debug:
			# self.log.debug(f"SQL:\n{sql}\nARGS: {args}")
			print(f"SQL: {sql_compact(sql)} | ARGS: {args}")

		with self._conn.cursor() as cur:
			cur.execute(sql, args or None)

			if one:
				return cur.fetchone()

			else:
				return cur.fetchall()

	def query(self, sql: str, *args):
		return self._execeute(sql, args or None)

	def query_one(self, sql: str, *args):
		return self._execeute(sql, args or None)

	def query_range(self, sql: str, *, start=None, end=None, args=()):
		"""
		Injects a time filter into a query using ts column.
		Assumes query contains `{time_filter}` placeholder.

		pg.query_range(\"\"\"
			SELECT
				agent,
				COUNT(*) AS total
			FROM events
			WHERE {time_filter}
			GROUP BY agent
			ORDER BY total DESC
		\"\"\", start=req.start, end=req.end)
		"""

		if "{time_filter}" not in sql:
			raise ValueError("Query must include {time_filter}")

		start_ts = self._to_epoch(start) or 0
		end_ts = self._to_epoch(end) or int(time.time())

		sql = sql.format(time_filter="ts BETWEEN %s AND %s")

		return self._execute(sql, list(args) + [start_ts, end_ts])

	def query_last(self, sql: str, seconds: int, args=()):
		"""
		Calls `query_range`, implicitly injecting the start/end time range
		based on the value of `seconds`. For example, specifying a value of
		3600 would only return queries for the last hour. Like `query_range`,
		the `{time_filter}` format must appear in query string.
		"""

		now = int(time.time())

		return self.query_range(
			sql,
			start=now - seconds,
			end=now,
			args=args
		)

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
