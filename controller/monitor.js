import express from "express";
import crypto from "node:crypto";
import ejs from "ejs";
import path from "node:path";
import fs from "node:fs";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	/* router.use((req, res, next) => {
		console.log("Monitor router saw:", req.method, req.originalUrl);

		next();
	}); */

	const AGENTS = JSON.parse(fs.readFileSync(process.env.AGENT_FILE || "./agents.json"));
	const CLIENTS = new Map();

	function verifyIP(req, res, next) {
		const ip = req.ip.replace("::ffff:", "");

		if(!AGENTS[ip]) {
			console.log("verifyIP failure:", ip);

			return res.status(403).json({ error: "Forbidden" });
		}

		next();
	}

	function verifyHMAC(req, res, next) {
		const signature = req.headers["x-agent-signature"];
		const body = JSON.stringify(req.body);

		const expected = crypto
			.createHmac("sha256", process.env.AGENT_SECRET)
			.update(body)
			.digest("hex")
		;

		if(!signature || signature.length !== expected.length) {
			console.log("verifyHMAC failure A");

			return res.status(401).json({ error: "Invalid signature" });
		}

		const safe = crypto.timingSafeEqual(
			Buffer.from(signature),
			Buffer.from(expected)
		);

		if(!safe) {
			console.log("verifyHMAC failure B");

			return res.status(401).json({ error: "Invalid signature" });
		}

		next();
	}

	router.use(verifyIP);

	router.get("/stream/:vps/:collector", (req, res) => {
		const { vps, collector } = req.params;
		// const format = req.query.format || "html";
		const key = `${vps}:${collector}`;

		res.setHeader("Content-Type", "text/event-stream");
		res.setHeader("Cache-Control", "no-cache");
		res.setHeader("Connection", "keep-alive");
		res.flushHeaders?.();

		if(!CLIENTS.has(key)) {
			CLIENTS.set(key, new Set());
		}

		// CLIENTS.get(key).add({res, format});
		CLIENTS.get(key).add(res);

		res.write(`data: ${JSON.stringify({ status: "connected" })}\n\n`);

		req.on("close", () => {
			/* const set = clients.get(key);
			if(!set) return;

			for(const client of set) {
				if(client.res === res) {
					set.delete(client);

					break;
				}
			} */

			CLIENTS.get(key)?.delete(res);
		});
	});

	router.post("/collect", verifyHMAC, async(req, res) => {
		const events = Array.isArray(req.body) ? req.body : [req.body];
		const ip = req.ip.replace("::ffff:", "");
		const hostname = AGENTS[ip];

		if(!hostname) return res.status(403).json({ error: "Unknown agent IP" });

		console.log("Received system metrics:", hostname);

		await redis.sAdd("ma:vps:index", hostname);

		for(const event of events) {
			if(!event.collector || !event.ts || !event.metrics) continue;

			const key = `ma:vps:${hostname}:${event.collector}:events`;

			await redis.lPush(key, JSON.stringify(event));
			await redis.lTrim(key, 0, 1999);
			await redis.sAdd(`ma:vps:${hostname}:collectors:index`, event.collector);

			// TODO: This is essentially our "cold storage" for historical analysis later.
			try {
				await pg.query(
					`INSERT INTO events (vps, collector, ts, metrics)
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

			const message = `data: ${JSON.stringify({ html: rendered })}\n\n`;
			const clients = CLIENTS.get(`${hostname}:${event.collector}`);

			if(clients) {
				/* for(const client of clients || []) {
					if(client.format === "json") {
						client.res.write(`data: ${JSON.stringify(event)}\n\n`);
					}

					else {
						// TODO: Resolve the `rendered` above...
						// client.res.write(`data: ${JSON.stringify({ html })}\n\n`);
						// client.write(message);
					}
				} */

				for(const client of clients) {
					// client.res.write(message);
					client.write(message);
				}
			}
		}

		res.json({ ok: true });
	});

	// GET viewer(history + live updates)
	router.get("/", async (req, res) => {
		// const key = "ma:vps:xeno:logs:events";
		// const items = await redis.lRange(key, 0, 19);
		// const parsed = items.map(i => JSON.parse(i));

		res.type("txt").send("TODO");
	});

	// TODO: This demos how the REST API would work; nothing fancy. Firefox has a cool, structured
	// JSON viewer it fires up for this. :)
	router.get("/json/:vps/:collector", async (req, res) => {
		const { vps, collector } = req.params;
		const { source } = req.query;

		const key = `ma:vps:${vps}:${collector}:events`;
		const items = await redis.lRange(key, 0, -1);

		let parsed = items.map(i => JSON.parse(i));

		if(source) {
			parsed = parsed.filter(e =>
				e.metrics?.source?.includes(source)
			);
		}

		res.json(parsed);
	});

	// Another REST demo for querying the known VPSes.
	router.get("/json/vps", async (req, res) => {
		const vps = await redis.sMembers("ma:vps:index");
		const result = {};

		for(const host of vps) {
			result[host] = await redis.sMembers(`ma:vps:${host}:collectors`);
		}

		res.json(result);
	});

	// Now, let's start building up VPS-specific viewing routes...
	router.get("/vps/:vps/logs/:log", async (req, res) => {
		const { vps, log } = req.params;
		const { source } = req.query;
		const key = `ma:vps:${vps}:logs.${log}:events`;
		const items = await redis.lRange(key, 0, 199);

		let parsed = items.map(i => JSON.parse(i));

		if(source) {
			parsed = parsed.filter(e =>
				e.metrics?.source?.includes(source)
			);
		}

		res.render("logs", { vps, events: parsed, source });
	});

	return router;
}
