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

from massaffect.database import *

app = typer.Typer()

ENVELOPE = typer.Option(
	False,
	"--envelope", "--env", "-E",
	help="Include the full MassAffect event envelope."
)

PRETTY = typer.Option(
	False,
	"--pretty", "-p",
	help="Print with color, newlines and indentation."
)

AGENT = typer.Option(
	None,
	"--agent", "-a",
	help="Specify a single AGENT to restrict queries to."
)

COLLECTOR = typer.Option(
	None,
	"--collector", "-c",
	help="Specify a single COLLECTOR to restrict queries to."
)

START = typer.Option(
	...,
	"-s", "--start",
	help="Start time (ISO format)"
)

END = typer.Option(
	None,
	"-e", "--end",
	help="End time (ISO format)"
)

DURATION = typer.Option(
	None,
	"-d", "--duration",
	help="Duration (e.g. '1 hour')"
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

def _filter_args(
	agent: str=AGENT,
	collector: str=COLLECTOR,
	start: str=START,
	end: str=END,
	duration: str=DURATION
):
	if end and duration:
		raise typer.BadParameter("Cannot use both --end and --duration")

	if not end and not duration:
		raise typer.BadParameter("Must provide either --end or --duration")

	start_dt, end_dt = parse_time(
		start=start,
		end=end,
		duration=duration
	)

	where, args = build_where(
		filter_time(start=start_dt, end=end_dt),
		filter_agent(agent),
		filter_collector(collector),
	)

	return where, args

@app.command()
def dump(
	num: int=typer.Argument(
		...,
		help="Number of total rows to dump, sorted by envelope timestamp."
	),
	agent: str=AGENT,
	collector: str=COLLECTOR,
	start: str=START,
	end: str=END,
	duration: str=DURATION,
	envelope: bool=ENVELOPE,
	pretty: bool=PRETTY
):
	"""Dumps the specified number of newest `events` rows."""

	where, args = _filter_args(agent, collector, start, end, duration)

	sql = f"""
		SELECT agent, collector, ts, metrics
		FROM events
		WHERE {where}
		ORDER BY ts DESC
		LIMIT %s
	"""

	args.append(num)

	with pg_execute(sql, *args) as rows:
		for row in envelope_rows(envelope, rows):
			pretty_print(pretty, row)

@app.command()
def dumpall(
	agent: str=AGENT,
	collector: str=COLLECTOR,
	start: str=START,
	end: str=END,
	duration: str=DURATION,
	envelope: bool = ENVELOPE,
	pretty: bool = PRETTY
):
	"""Dumps the complete range `events` in ASCENDING order."""

	where, args = _filter_args(agent, collector, start, end, duration)

	sql = f"""
		SELECT agent, collector, ts, metrics
		FROM events
		WHERE {where}
		ORDER BY ts ASC
	"""

	with pg_execute(sql, *args) as rows:
		for row in envelope_rows(True, rows):
			pretty_print(pretty, row)

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

@app.command()
def health():
	"""Reports basic database row/disk sizes (NEEDS IMPROVEMENT)."""

	with pg_execute("""
		SELECT
			inhrelid::regclass AS partition,
			pg_size_pretty(pg_total_relation_size(inhrelid)) AS total_size,
			COALESCE(s.n_live_tup, 0) AS est_rows
		FROM pg_inherits
		LEFT JOIN pg_stat_user_tables s ON s.relid = inhrelid
		WHERE inhparent = 'events'::regclass
		ORDER BY inhrelid::regclass::text;
	""") as rows:
		for row in rows:
			pretty_print(True, row)

	with pg_execute("""
		SELECT
			pg_size_pretty(SUM(pg_total_relation_size(inhrelid))) AS total_size,
			SUM(COALESCE(s.n_live_tup, 0)) AS est_total_rows
		FROM pg_inherits
		LEFT JOIN pg_stat_user_tables s ON s.relid = inhrelid
		WHERE inhparent = 'events'::regclass;
	""") as rows:
		for row in rows:
			print(row)

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

if __name__ == "__main__":
	app()
