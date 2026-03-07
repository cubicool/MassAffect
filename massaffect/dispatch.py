import asyncio

from . import Loggable

class Dispatcher(Loggable):
	def __init__(self, transport, interval):
		self.transport = transport
		self.interval = interval
		self.queue = asyncio.Queue()

		self._running = True

	async def enqueue(self, payload, flush=False):
		"""
		Add payload to queue.

		If flush=True, immediately flush after enqueue.
		"""

		await self.queue.put(payload)

		if flush:
			await self.flush()

	async def run(self):
		"""
		Periodically flush queued payloads.
		"""

		self.log.info(f"Running with {self.interval}s interval")

		while self._running:
			await asyncio.sleep(self.interval)
			await self.flush()

		self.log.info("Stopped")

	async def flush(self):
		"""
		Drain queue and send as batch.
		"""

		events = []

		while not self.queue.empty():
			try:
				events.append(self.queue.get_nowait())

			except asyncio.QueueEmpty:
				break

		if not events:
			return

		try:
			await self.transport.send(events)

			self.log.info(f"Flushed batch ({len(events)} events)")

		except Exception as e:
			self.log.warning(f"Flush failed: {e}")

	async def close(self):
		"""
		Stop dispatcher and flush remaining events.
		"""

		self._running = False

		await self.flush()
