import fs from "node:fs";
import path from "node:path";

import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default async function loadRoutes(app, ...deps) {
	const files = fs.readdirSync(__dirname);

	for(const file of files) {
		if(!file.endsWith(".js") || file === "index.js") continue;

		const name = file.replace(".js", "");
		const module = await import(`./${file}`);

		const router = module.default(...deps);

		app.use(`/${name}`, router);

		console.log(`Loaded route /${name}`);
	}
}
