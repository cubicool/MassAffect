import psycopg
import redis

from contextlib import contextmanager

from . import config

def pg_connect():
	return psycopg.connect(
		**config().system.postgres,
		row_factory=psycopg.rows.dict_row
	)

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

def redis_connect():
	return redis.Redis(decode_responses=True)
