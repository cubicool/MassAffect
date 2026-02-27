import express from "express";
import crypto from "crypto";
import ejs from "ejs";
import path from "path";

export default function monitorRoutes(redis) {
	const router = express.Router();

	router.use((req, res, next) => {
		console.log("Monitor router saw:", req.method, req.originalUrl);
		next();
	});

	const AGENTS = {
		"104.13.36.111": "xeno", // Jeremy
		"73.229.39.141": "chris",
		"199.241.139.173": "omicron",
		"144.202.111.30": "lambda",
		"127.0.0.1": "localhost",
		"::1": "localhost"
	};

	// Represents all the active SSE connections.
	// const clients = new Set();

	const clients = new Map();
	// key = "vps:collector"
	// value = Set(res)

	function verifyIP(req, res, next) {
		const ip = req.ip.replace("::ffff:", "");

		if(!AGENTS[ip]) {
			console.log("verifyIP failure:", ip);

			return res.status(403).json({ error: "Forbidden" });
		}

		next();
	}

	function verifyHMAC(req, res, next) {
		const SECRET = process.env.AGENT_SECRET;
		const signature = req.headers["x-agent-signature"];
		const body = JSON.stringify(req.body);

		const expected = crypto
			.createHmac("sha256", SECRET)
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

	router.get("/stream", (req, res) => {
		res.setHeader("Content-Type", "text/event-stream");
		res.setHeader("Cache-Control", "no-cache");
		res.setHeader("Connection", "keep-alive");
		res.flushHeaders?.();

		const defaultKey = "global";

		if(!clients.has(defaultKey)) {
			clients.set(defaultKey, new Set());
		}

		clients.get(defaultKey).add(res);

		res.write(`data: ${JSON.stringify({ status: "connected" })}\n\n`);

		req.on("close", () => {
			clients.get(defaultKey)?.delete(res);
		});
	});

	router.get("/stream/:vps/:collector", (req, res) => {
		const { vps, collector } = req.params;
		const streamKey = `${vps}:${collector}`;

		res.setHeader("Content-Type", "text/event-stream");
		res.setHeader("Cache-Control", "no-cache");
		res.setHeader("Connection", "keep-alive");
		res.flushHeaders?.();

		if(!clients.has(streamKey)) {
			clients.set(streamKey, new Set());
		}

		clients.get(streamKey).add(res);

		res.write(`data: ${JSON.stringify({ status: "connected" })}\n\n`);

		req.on("close", () => {
			clients.get(streamKey)?.delete(res);
		});
	});

	// POST collector endpoint
	router.post("/collect", verifyHMAC, async(req, res) => {
		const events = Array.isArray(req.body) ? req.body : [req.body];
		const ip = req.ip.replace("::ffff:", "");
		const hostname = AGENTS[ip];

		if(!hostname) return res.status(403).json({ error: "Unknown agent IP" });

		console.log("Received system metrics:", hostname);

		// TODO: We'll eventually need/want these!
		// await redis.sAdd("ma:vps:index", hostname);
		// await redis.sAdd(`ma:vps:${hostname}:collectors`, event.collector);

		for(const event of events) {
			if(!event.collector || !event.ts || !event.metrics) continue;

			const key = `ma:vps:${hostname}:${event.collector}:events`;

			await redis.lPush(key, JSON.stringify(event));
			await redis.lTrim(key, 0, 1999);

			// Broadcast directly to any currently connected SSE clients (above).
			// const message = `data: ${JSON.stringify(event)}\n\n`;

			const rendered = await ejs.renderFile(
				path.join(process.cwd(), "views/partials/log-entry.ejs"),
				{ event }
			);

			const message = `data: ${JSON.stringify({ html: rendered })}\n\n`;

			const globalClients = clients.get("global");

			if(globalClients) {
				for(const client of globalClients) {
					client.write(message);
				}
			}

			const scopedKey = `${hostname}:${event.collector}`;
			const scopedClients = clients.get(scopedKey);

			if(scopedClients) {
				for(const client of scopedClients) {
					client.write(message);
				}
			}
		}

		res.json({ ok: true });
	});

	// GET viewer(history + live updates)
	router.get("/", async (req, res) => {
		const key = "ma:vps:xeno:logs:events";

		const items = await redis.lRange(key, 0, 19);
		const parsed = items.map(i => JSON.parse(i));

		res.type("html").send(`
			<html>
			<body style="background:#111;color:#0f0;font-family:monospace;padding:20px;">
			<h2>MassAffect Live</h2>
			<pre id="output">${JSON.stringify(parsed, null, 2)}</pre>

			<script>
				const output = document.getElementById("output");
				const evtSource = new EventSource("/monitor/stream");

				evtSource.onmessage = function(event) {
					const data = JSON.parse(event.data);

					output.textContent =
						JSON.stringify(data, null, 2)
						+ "\\n\\n"
						+ output.textContent
					;
				};

				/* const interval = setInterval(() => {
					res.write(": keepalive\n\n");
				}, 15000);

				req.on("close", () => {
					clearInterval(interval);
				}); */
			</script>

			</body>
			</html>
		`);
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

	// Now, let's start building up VPS-specific viewing routes...
	router.get("/vps/:vps/logs", async (req, res) => {
		const { vps } = req.params;
		const { source } = req.query;

		const key = `ma:vps:${vps}:logs:events`;

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
