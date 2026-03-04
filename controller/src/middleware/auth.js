import crypto from "node:crypto";

import { cfg } from "../config.js";

export function verifyIP(req, res, next) {
	const ip = req.ip.replace("::ffff:", "");

	if(!cfg().controller.agents[ip]) {
		console.log("verifyIP failure:", ip);

		return res.status(403).json({ error: "Forbidden" });
	}

	next();
}

export function verifyHMAC(req, res, next) {
	const signature = req.headers["x-agent-signature"];
	const body = JSON.stringify(req.body);

	const expected = crypto
		.createHmac("sha256", cfg().agent.agent_secret)
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
