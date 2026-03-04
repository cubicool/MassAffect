import express from "express";
import crypto from "node:crypto";
import ejs from "ejs";
import path from "node:path";
import fs from "node:fs";

import { verifyIP, verifyHMAC } from "../middleware/auth.js";
import { addClient, removeClient } from "../state/clients.js";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	/* router.use((req, res, next) => {
		console.log("Monitor router saw:", req.method, req.originalUrl);

		next();
	}); */

	router.get("/stream/:vps/:collector", (req, res) => {
		const { vps, collector } = req.params;
		const format = req.query.format || "html";
		const key = `${vps}:${collector}`;

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

	router.get("/json/vps/:vps/logs/:log", async (req, res) => {
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

		res.render("logs-json", { vps, events: parsed, source, collector: `logs.${log}` });
	});

	return router;
}
