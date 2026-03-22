#!/usr/bin/env python3

import sys
import json
import asyncio
import typer
import builtins

from rich import print
from rich.json import JSON
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Always append the "project root" (setup as `ROOT` here) so that the main Python code is found.
sys.path.insert(0, str(ROOT))

from massaffect.database import pg_execute, pg_connect_async

app = typer.Typer()

ENVELOPE = typer.Option(
	False,
	"--envelope", "--env", "-e",
	help="Include the full MassAffect event envelope."
)

PRETTY = typer.Option(
	False,
	"--pretty", "-p",
	help="Print with color, newlines and indentation."
)

def pretty_print(pretty, data):
	if pretty:
		print(JSON.from_data(data))

	else:
		builtins.print(json.dumps(data, separators=(",", ":")))

def envelope_rows(envelope, rows):
	for row in rows:
		yield row if envelope else row["metrics"]

@app.command(name="query")
@app.command(name="q")
def query(
	q: str=typer.Argument(
		None,
		help="Any valid SQL query; reads from STDIN if omitted."
	),
	envelope: bool=ENVELOPE,
	pretty: bool=PRETTY
):
	"""Runs any valid SQL query on the toplevel `massaffect` database."""

	if q is None:
		if sys.stdin.isatty():
			raise typer.BadParameter("Query required (or pipe SQL via stdin).")

		q = sys.stdin.read()

	with pg_execute(q) as rows:
		for row in envelope_rows(envelope, rows):
			pretty_print(pretty, row)

@app.command()
def dump(
	num: int=typer.Argument(
		...,
		help="Number of total rows to dump, sorted by envelope timestamp."
	),
	envelope: bool=ENVELOPE,
	pretty: bool=PRETTY
):
	"""Dumps the specified number of newest `events` rows."""

	with pg_execute("""
		SELECT agent, collector, ts, metrics
		FROM events
		ORDER BY ts DESC
		LIMIT %s
	""", num) as rows:
		for row in envelope_rows(envelope, rows):
			pretty_print(pretty, row)

@app.command()
def dumpall(
	envelope: bool = ENVELOPE,
	pretty: bool = PRETTY
):
	"""Dumps the entire `events` table; use with caution."""

	with pg_execute("SELECT agent, collector, ts, metrics FROM events") as rows:
		for row in envelope_rows(True, rows):
			pretty_print(False, row)

@app.command()
def listen():
	"""A simple demo for async/await realtime listening to Postgres."""

	async def _listen():
		async with await pg_connect_async() as conn:
			await conn.set_autocommit(True)

			async with conn.cursor() as cur:
				await cur.execute("LISTEN events")

				print("Listening for notifications...")

				async for notify in conn.notifies():
					print("Channel:", notify.channel)
					print("Payload:", notify.payload)

	asyncio.run(_listen())

events_table = typer.Typer(help="Manage the events table and its partitions.")

app.add_typer(events_table, name="events-table")

# Create the parent `events` table, from which partitions are derived.
@events_table.command()
def create():
	"""Creates the main `events` table, with partitioning logic."""

	with pg_execute("""
		CREATE TABLE events (
			agent TEXT NOT NULL,
			collector TEXT NOT NULL,
			ts BIGINT NOT NULL,
			metrics JSONB
		) PARTITION BY RANGE (ts);

		CREATE INDEX idx_events_agent_collector_ts
		ON events (agent, collector, ts DESC);

		CREATE OR REPLACE FUNCTION ensure_events_partition()
		RETURNS TRIGGER AS $$
		DECLARE
			start_ts BIGINT;
			end_ts BIGINT;
			part_name TEXT;
			start_date TIMESTAMPTZ;
		BEGIN
			start_date := date_trunc('month', to_timestamp(NEW.ts));

			start_ts := extract(epoch FROM start_date)::BIGINT;
			end_ts := extract(epoch FROM start_date + interval '1 month')::BIGINT;

			part_name := 'events_' || to_char(start_date, 'YYYY_MM');

			IF to_regclass(part_name) IS NULL THEN
				BEGIN
					EXECUTE format(
						'CREATE TABLE %I PARTITION OF events
						 FOR VALUES FROM (%s) TO (%s)',
						part_name,
						start_ts,
						end_ts
					);
				EXCEPTION
					WHEN duplicate_table THEN NULL;
				END;
			END IF;

			RETURN NEW;
		END;
		$$ LANGUAGE plpgsql;

		CREATE TRIGGER ensure_events_partition_trigger
		BEFORE INSERT ON events
		FOR EACH ROW
		EXECUTE FUNCTION ensure_events_partition();
	""") as res:
		print(res.statusmessage)

@events_table.command()
def partition(
	month: int=typer.Argument(
		...,
		min=1,
		max=12,
		help="Single-digit month to use as START of parition."
	),
	year: int=typer.Option(
		None,
		"--year",
		help="4-digit year, defaults to current year."
	)
):
	"""Creates a single-month partition for the `events` table."""

	from datetime import datetime, timezone

	def _month_bounds(_month: int, _year: int):
		start = datetime(_year, _month, 1, tzinfo=timezone.utc)

		if _month == 12:
			end = datetime(_year + 1, 1, 1, tzinfo=timezone.utc)

		else:
			end = datetime(_year, _month + 1, 1, tzinfo=timezone.utc)

		return int(start.timestamp()), int(end.timestamp())

	year = year or datetime.now(timezone.utc).year

	ts_from, ts_to = _month_bounds(month, year)

	with pg_execute(f"""
		CREATE TABLE IF NOT EXISTS events_{year}_{month:02d}
		PARTITION OF events
		FOR VALUES FROM ({ts_from}) TO ({ts_to});
	""") as res:
		print(res.statusmessage)

# Purge the `events` table and start over.
@events_table.command()
def destroy():
	"""Truncates/restarts the `events` table."""

	if not typer.confirm("This will permanently destroy all `events`; continue?"):
		typer.echo("Aborted.")

		raise typer.Exit()

	with pg_execute("TRUNCATE TABLE events RESTART IDENTITY;") as res:
		print(res.statusmessage)

# TODO: Move these (and many more) into the Reporter subsystem, once I start it.
"""
# Busiest sites?
ma_psql_ascii <<EOF
SELECT
  metrics->>'source' AS logfile,
  count(*) AS hits
FROM events
GROUP BY logfile
ORDER BY hits DESC;
EOF

# Rows with NO USER AGENT! Boo! :(
function ma_psql_query_noua() {
ma_psql <<EOF
SELECT
  metrics->>'remote_addr' AS ip,
  count(*) AS hits
FROM events
WHERE metrics->>'http_user_agent' IS NULL
   OR metrics->>'http_user_agent' = ''
GROUP BY ip
ORDER BY hits DESC;
EOF
}

ma_psql_query_noua

# echo "SELECT * FROM events WHERE metrics->>'path' = '/wp-login.php';" | ma_psql
# Shows how many queries each IP made; insane!
# echo "SELECT metrics->>'remote_addr', count(*) FROM events GROUP BY 1 ORDER BY 2 DESC;" | ma_psql

# How long ago did the web queries occur?
ma_psql <<EOF
SELECT
    NOW() - (metrics->>'time_local')::timestamptz AS age
FROM events
ORDER BY ts DESC
LIMIT 10;
EOF

# Or, see who is hitting a particular route/path the most!
ma_psql <<EOF
SELECT
  metrics->>'remote_addr' AS ip,
  count(*) AS hits
FROM events
WHERE metrics->>'path' = '/wp-login.php'
GROUP BY ip
ORDER BY hits DESC;
EOF

# Grab all the 200 response codes...
# ma_psql <<EOF
# SELECT * FROM events WHERE metrics @> '{"status":200}';
# EOF

# Top user-agents...
ma_psql <<EOF
SELECT
  metrics->>'http_user_agent' AS ua,
  count(*) AS hits
FROM events
GROUP BY ua
ORDER BY hits DESC
LIMIT 20;
EOF

# 404 Scanners?
ma_psql <<EOF
SELECT
  metrics->>'source' AS logfile,
  count(*) AS hits
FROM events
WHERE metrics->>'status' = '404'
GROUP BY logfile
ORDER BY hits DESC;
EOF

# Analytics, baby! By hour...
ma_psql <<EOF
SELECT
  date_trunc('hour', to_timestamp(ts)) AS hour,
  count(*) AS events
FROM events
GROUP BY hour
ORDER BY hour DESC;
EOF

# ...and analytics by MINUTE!
ma_psql <<EOF
SELECT
  date_trunc('minute', to_timestamp(ts)) AS minute,
  count(*) AS events
FROM events
GROUP BY minute
ORDER BY minute DESC;
EOF
"""

# TODO: Move something like this (but better!) into a full TUI, and expose it via another
# command like `monitor`.
"""
URL = "https://ambaince.com/monitor/stream/omicron/system"

async def stream():
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as resp:

            async for line in resp.content:
                line = line.decode().strip()

                if line.startswith("data:"):
                    payload = line[5:].strip()
                    event = json.loads(payload)

                    print(event)

asyncio.run(stream())
"""

if __name__ == "__main__":
	app()
