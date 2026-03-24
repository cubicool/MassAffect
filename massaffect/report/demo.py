from . import Report

class Demo(Report):
	NAME = "demo"
	AUTOLOAD = True

	def evaluate(self, req: Report.Request) -> Report.Response:
		pg = req.pg

		# --- total events ---
		total = pg.query_one("""
			SELECT COUNT(*) AS total FROM events
		""")["total"]

		# --- time range ---
		time_range = pg.query_one("""
			SELECT
				to_timestamp(MIN(ts)) AS start,
				to_timestamp(MAX(ts)) AS end
			FROM events
		""")

		# --- per-agent ---
		agents = pg.query("""
			SELECT
				agent,
				COUNT(*) AS total
			FROM events
			GROUP BY agent
			ORDER BY total DESC
		""")

		# --- per-collector ---
		collectors = pg.query("""
			SELECT
				collector,
				COUNT(*) AS total
			FROM events
			GROUP BY collector
			ORDER BY total DESC
		""")

		# --- xmlrpc abuse ---
		xmlrpc = pg.query("""
			SELECT
				metrics->>'remote_addr' AS ip,
				COUNT(*) AS hits
			FROM events
			WHERE collector = 'logs.nginx'
				AND metrics->>'request' ILIKE '%xmlrpc.php%'
			GROUP BY ip
			ORDER BY hits DESC
			LIMIT 10
		""")

		# --- size ---
		size = pg.query_one("""
			SELECT pg_size_pretty(pg_total_relation_size('events_2026_03')) AS size
		""")["size"]

		return Report.Response(
			status=False,
			info={
				"summary": {
					"total_events": total,
					"start": str(time_range["start"]),
					"end": str(time_range["end"]),
					"db_size": size,
				},
				"agents": agents,
				"collectors": collectors,
				"xmlrpc_top": xmlrpc,
			}
		)
