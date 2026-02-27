import express from "express";
import dotenv from "dotenv";
import morgan from "morgan";
import path from "node:path";

console.log("dotenv result:", dotenv.config());

import { createClient } from 'redis';

const redis = createClient();
await redis.connect();

import { Pool } from "pg";

const pg = new Pool({
	host: process.env.PG_HOST || "127.0.0.1",
	port: process.env.PG_PORT || 5432,
	user: process.env.PG_USER,
	password: process.env.PG_PASSWORD,
	database: process.env.PG_DATABASE,
});

pg.on("error", err => {
	console.error("Unexpected PG error:", err);
});

import monitorRoutes from "./monitor.js";

const app = express();

// This line ensures we get the REAL IP from OLS, which is proxying us.
app.set("trust proxy", true);
app.set("view engine", "ejs");
app.set("views", path.join(process.cwd(), "views"));

app.use(express.json({ limit: "10mb" }));
app.use(morgan("dev"));
app.use("/monitor", monitorRoutes(redis, pg));

app.listen(process.env.PORT, () => {
	console.log(`Monitor server running on port ${process.env.PORT}`);
});
