import express from "express";
import morgan from "morgan";
import path from "node:path";

import { createClient } from 'redis';
import { Pool } from "pg";

import { cfg } from "./config.js";

const config = cfg();

// TODO: Setup Redis config!
const redis = createClient();

redis.on('error', (err) => {
	console.error('Redis error:', err);
});

redis.on('connect', () => {
	console.log('Redis connected');
});

redis.on('reconnecting', () => {
	console.log('Redis reconnecting...');
});

redis.on('end', () => {
	console.log('Redis connection closed');
});

await redis.connect();

const pg = new Pool({...config.system.postgres});

pg.on("error", err => {
	console.error("Unexpected PG error:", err);
});

const app = express();

// This line ensures we get the REAL IP from OLS, which is proxying us.
app.set("trust proxy", true);
app.set("view engine", "ejs");
app.set("views", path.join(process.cwd(), "views"));

// app.use(express.json({ limit: "50mb" }));
app.use(express.json({
    verify: (req, res, buf) => { req.rawBody = buf; },
	limit: "50mb"
}));
app.use(morgan("dev"));

/* import monitorRoutes from "./routes/monitor.js";
import collectRoutes from "./routes/collect.js";

app.use("/monitor", monitorRoutes(redis, pg));
app.use("/collect", collectRoutes(redis, pg)); */

import loadRoutes from "./routes/index.js";

loadRoutes(app, redis, pg);

app.listen(config.controller.port, () => {
	console.log(`Monitor server running on port ${config.controller.port}`);
});
