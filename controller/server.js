import express from "express";
import morgan from "morgan";
import path from "node:path";

import { createClient } from 'redis';
import { Pool } from "pg";

import { cfg } from "./config.js";

const config = cfg();

// TODO: Setup Redis config!
const redis = createClient();

await redis.connect();

const pg = new Pool({...config.system.postgres});

pg.on("error", err => {
	console.error("Unexpected PG error:", err);
});

// TODO: Move/rename this to something like `routes.js`!
import monitorRoutes from "./monitor.js";

const app = express();

// This line ensures we get the REAL IP from OLS, which is proxying us.
app.set("trust proxy", true);
app.set("view engine", "ejs");
app.set("views", path.join(process.cwd(), "views"));

app.use(express.json({ limit: "10mb" }));
app.use(morgan("dev"));
app.use("/monitor", monitorRoutes(config, redis, pg));

app.listen(config.controller.port, () => {
	console.log(`Monitor server running on port ${config.controller.port}`);
});
