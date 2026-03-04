import express from "express";

import { Events } from "../lib.js";
import { verifyIP, verifyHMAC } from "../middleware/auth.js";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	// TODO: This demos how the REST API would work; nothing fancy. Firefox has a cool, structured
	// JSON viewer it fires up for this. :)
	router.get("/vps/:vps/:collector", async (req, res) => {
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

		// const events = await Events.getLogEvents(redis, { vps, log, source });

		res.json(parsed);
	});

	// Another REST demo for querying the known VPSes.
	router.get("/vps", async (req, res) => {
		const vps = await redis.sMembers("ma:vps:index");
		const result = {};

		for(const host of vps) {
			result[host] = await redis.sMembers(`ma:vps:${host}:collectors`);
		}

		res.json(result);
	});

	return router;
}
