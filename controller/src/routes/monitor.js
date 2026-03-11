import express from "express";

import { verifyIP, verifyHMAC } from "../middleware/auth.js";
import { Client, addClient, removeClient } from "../state/clients.js";
import { Events } from "../lib.js";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	/* router.get("/stream/:agent/:collector", (req, res) => {
		const { agent, collector } = req.params;
		const format = req.query.format || "html";
		const key = `${agent}:${collector}`;

		res.setHeader("Content-Type", "text/event-stream");
		res.setHeader("Cache-Control", "no-cache");
		res.setHeader("Connection", "keep-alive");
		res.flushHeaders?.();

		addClient(key, {res, format});

		console.log(`Added ${res.socket.remotePort} (${format}) to CLIENTS`);

		res.write(`data: ${JSON.stringify({ status: "connected" })}\n\n`);

		req.on("close", () => {
			removeClient(key, {res, format});

			console.log(`Removed ${res.socket.remotePort} from CLIENTS`);
		});
	}); */

	router.get("/stream/:agent/:collector", (req, res) => {
		const { agent, collector } = req.params;
		const key = `${agent}:${collector}`;

		const client = new Client(req, res);

		addClient(key, client);

		client.send({ status: "connected" });

		/* req.on("close", () => {
			removeClient(key, client);

			client.close();
		}); */
	});

	router.get("/", async (req, res) => {
		// const key = "ma:agent:xeno:logs:events";
		// const items = await redis.lRange(key, 0, 19);
		// const parsed = items.map(i => JSON.parse(i));

		res.type("txt").send("TODO");
	});

	// Now, let's start building up Agent-specific viewing routes...
	router.get("/agent/:agent/logs/:log", async (req, res) => {
		const { agent, log } = req.params;
		const { source } = req.query;
		const events = await Events.getLogEvents(redis, { agent, log, source });

		res.render("logs", { agent, events, source });
	});

	router.get("/agent/:agent/logsjson/:log", async (req, res) => {
		const { agent, log } = req.params;
		const { source } = req.query;
		const events = await Events.getLogEvents(redis, { agent, log, source });

		res.render("logs-json", { agent, events, source, collector: `logs.${log}` });
	});

	return router;
}
