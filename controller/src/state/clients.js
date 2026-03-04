const CLIENTS = new Map();

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
	return CLIENTS.get(key) || new Set();
}

export function clientCount(key) {
        return CLIENTS.get(key)?.size || 0;
}
