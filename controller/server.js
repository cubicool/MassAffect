import express from "express";
import dotenv from "dotenv";
import morgan from "morgan";
import path from "path";

import { createClient } from 'redis';

const redis = createClient();
await redis.connect();

console.log("dotenv result:", dotenv.config());
console.log("AGENT_SECRET in server:", process.env.AGENT_SECRET);

import monitorRoutes from "./monitor.js";

const app = express();

// This line ensures we get the REAL IP from OLS, which is proxying us.
app.set("trust proxy", true);
app.set("view engine", "ejs");
app.set("views", path.join(process.cwd(), "views"));

app.use(express.json({ limit: "1mb" }));
app.use(morgan("dev"));
app.use("/monitor", monitorRoutes(redis));

app.listen(process.env.PORT, () => {
	console.log(`Monitor server running on port ${process.env.PORT}`);
});
