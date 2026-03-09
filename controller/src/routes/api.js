import express from "express";

import { Events } from "../lib.js";
import { verifyIP, verifyHMAC } from "../middleware/auth.js";

export default function monitorRoutes(redis, pg) {
	const router = express.Router();

	router.use(verifyIP);

	// TODO: This demos how the REST API would work; nothing fancy. Firefox has a cool, structured
	// JSON viewer it fires up for this. :)
	router.get("/agent/:agent/:collector", async (req, res) => {
		const { agent, collector } = req.params;
		const { source } = req.query;

		const key = `ma:agent:${agent}:${collector}:events`;
		const items = await redis.lRange(key, 0, -1);

		let parsed = items.map(i => JSON.parse(i));

		if(source) {
			parsed = parsed.filter(e =>
				e.metrics?.source?.includes(source)
			);
		}

		// const events = await Events.getLogEvents(redis, { agent, log, source });

		res.json(parsed);
	});

	// Another REST demo for querying the known Agents.
	router.get("/agent", async (req, res) => {
		const agent = await redis.sMembers("ma:agent:index");
		const result = {};

		for(const host of agent) {
			result[host] = await redis.sMembers(`ma:agent:${host}:collectors`);
		}

		res.json(result);
	});

	return router;
}
