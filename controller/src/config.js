import path from "node:path";
import fs from "node:fs";
import toml from "toml";

let _CONFIG = null;

function expandEnv(value) {
	if (typeof value === "string") {
		const match = value.match(/^\$\{(.+)\}$/);

		if (match) {
			const varName = match[1];
			const envValue = process.env[varName];

			if (!envValue) {
				throw new Error(`Missing required environment variable: ${varName}`);
			}

			return envValue;
		}

		return value;
	}

	if (Array.isArray(value)) {
		return value.map(expandEnv);
	}

	if (typeof value === "object" && value !== null) {
		const out = {};

		for (const key of Object.keys(value)) {
			out[key] = expandEnv(value[key]);
		}

		return out;
	}

	return value;
}

function loadConfig(filePath) {
	if (!fs.existsSync(filePath)) {
		throw new Error(`Config file not found: ${filePath}`);
	}

	const rawText = fs.readFileSync(filePath, "utf8");
	const parsed = toml.parse(rawText);

	return expandEnv(parsed);
}

export function cfg() {
	if (_CONFIG) return _CONFIG;

	const filePath = process.env.MASSAFFECT_CONFIG;

	if (!filePath) {
		throw new Error("MASSAFFECT_CONFIG environment variable not set");
	}

	_CONFIG = loadConfig(path.resolve(filePath));

	return _CONFIG;
}
