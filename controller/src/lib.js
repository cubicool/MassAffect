async function getEvents(redis, { agent, collector, limit=200 }) {
	const key = `ma:agent:${agent}:${collector}:events`;

	const items = await redis.lRange(key, 0, limit - 1);

	return items.map(i => JSON.parse(i));
}

/* async function getLogEvents(redis, { agent, log, source, limit=200 }) {
	let events = await getEvents(redis, { agent, collector: `logs.${log}`, limit });

	if(source) {
		events = events.filter(e =>
			e.metrics?.source?.includes(source)
		);
	}

	return events;
} */

// TODO: Improve filtering and possibly move it to `getEvents` instead.
async function getLogEvents(redis, opts) {
	const { log, source } = opts;

	let events = await getEvents(redis, {
		...opts,
		collector: `logs.${log}`
	});

	if(source) {
		events = events.filter(e =>
			e.metrics?.source?.includes(source)
		);
	}

	return events;
}

export const Events = {
	getEvents,
	getLogEvents
};
