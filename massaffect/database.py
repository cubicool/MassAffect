import psycopg
import redis

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

class PostgresDatabase:
	pass

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
