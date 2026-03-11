import express from "express";
import ejs from "ejs";
import path from "node:path";

import { cfg } from "../config.js";
import { verifyIP, verifyHMAC } from "../middleware/auth.js";
import { getClients } from "../state/clients.js";

export default function collectRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	router.post("/", verifyHMAC, async(req, res) => {
		const events = Array.isArray(req.body) ? req.body : [req.body];
		const ip = req.ip.replace("::ffff:", "");
		const hostname = cfg().controller.agents[ip];

		if(!hostname) return res.status(403).json({ error: "Unknown agent IP" });

		console.log("Received system metrics:", hostname);

		await redis.sAdd("ma:agent:index", hostname);

		for(const event of events) {
			if(!event.collector || !event.ts || !event.metrics) continue;

			const key = `ma:agent:${hostname}:${event.collector}:events`;

			await redis.lPush(key, JSON.stringify(event));
			await redis.lTrim(key, 0, 1999);
			await redis.sAdd(`ma:agent:${hostname}:collectors:index`, event.collector);

			// TODO: This is essentially our "cold storage" for historical analysis later.
			try {
				await pg.query(
					`INSERT INTO events (agent, collector, ts, metrics)
					VALUES ($1, $2, $3, $4)`,
					[
						hostname,
						event.collector,
						event.ts,
						event.metrics
					]
				);
			}

			catch(err) {
				console.error("Postgres insert failed:", err.message);
			}

			const rendered = await ejs.renderFile(
				path.join(process.cwd(), "views/partials/log-entry.ejs"),
				{ event }
			);

			/* const clients = getClients(`${hostname}:${event.collector}`);

			if(clients) {
				for(const client of clients || []) {
					if(client.format === "json") {
						client.res.write(`data: ${JSON.stringify(event)}\n\n`);
					}

					else {
						client.res.write(`data: ${JSON.stringify(rendered)}\n\n`);
					}
				}
			} */

			for(const client of getClients(`${hostname}:${event.collector}`)) {
				client.send(rendered);
			}
		}

		res.json({ ok: true });
	});

	return router;
}
