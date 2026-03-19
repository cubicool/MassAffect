import express from "express";

import { verifyIP, verifyHMAC } from "../middleware/auth.js";
import { Client, addClient, removeClient } from "../state/clients.js";
import { Events } from "../lib.js";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	router.get("/stream/:agent/:collector", (req, res) => {
		const { agent, collector } = req.params;
		const key = `${agent}:${collector}`;

		const client = new Client(req, res);

		addClient(key, client);

		client.send({ status: "connected" });
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
