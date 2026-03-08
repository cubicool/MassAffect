import psycopg

from psycopg.rows import dict_row
from contextlib import contextmanager

from . import config

def connect():
	return psycopg.connect(
		**config().system.postgres,
		row_factory=dict_row
	)

@contextmanager
def connection():
	# with psycopg.connect(DSN, row_factory=psycopg.rows.dict_row) as con:
	with connect() as con:
		yield con

@contextmanager
def cursor():
	with connection() as con:
		with con.cursor() as cur:
			yield cur

@contextmanager
def execute(q, *args):
	with cursor() as cur:
		cur.execute(q, args or None)

		yield cur
