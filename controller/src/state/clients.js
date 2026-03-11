export class Client {
	constructor(req, res) {
		this.req = req;
		this.res = res;

		this.init();

		req.on("close", () => this.close());
	}

	init() {
		const { res } = this;

		res.setHeader("Content-Type", "text/event-stream");
		res.setHeader("Cache-Control", "no-cache");
		res.setHeader("Connection", "keep-alive");

		res.flushHeaders?.();

		console.log(`Added ${res.socket.remotePort} to CLIENTS`);
	}

	send(event) {
		this.res.write(`data: ${JSON.stringify(event)}\n\n`);
	}

	// TODO: Is this necessary?
	sendRaw(data) {
		this.res.write(`data: ${data}\n\n`);
	}

	close() {
		removeClient(this.key, this);

		console.log(`Removed ${this.res.socket.remotePort} from CLIENTS`);
	}
}

const CLIENTS = new Map();
const EMPTY = new Set();

export function addClient(key, client) {
	if(!CLIENTS.has(key)) CLIENTS.set(key, new Set());

	CLIENTS.get(key).add(client);
}

export function removeClient(key, client) {
	const clients = CLIENTS.get(key);

	if(!clients) return;

	clients.delete(client);

	if(clients.size === 0) CLIENTS.delete(key);
}

export function getClients(key) {
	return CLIENTS.get(key) || EMPTY;
}

/*
	router.get("/stream/:agent/:collector", (req, res) => {
		const { agent, collector } = req.params;
		const format = req.query.format || "html";
		const key = `${agent}:${collector}`;

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

*/

/* export function addClient(key, client) {
	if(!CLIENTS.has(key)) CLIENTS.set(key, new Set());

	CLIENTS.get(key).add(client);
}

export function removeClient(key, client) {
	const clients = CLIENTS.get(key);

	if(!clients) return;

	clients.delete(client);

	if(clients.size === 0) CLIENTS.delete(key);
}

export function getClients(key) {
	return CLIENTS.get(key) || new Set();
} */

export function clientCount(key) {
        return CLIENTS.get(key)?.size || 0;
}
