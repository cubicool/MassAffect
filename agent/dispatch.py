import asyncio
import logging

class Dispatcher:
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

		logging.info("Dispatcher started")

		while self._running:
			await asyncio.sleep(self.interval)
			await self.flush()

		logging.info("Dispatcher stopped")

	async def flush(self):
		"""
		Drain queue and send as batch.
		"""

		items = []

		while not self.queue.empty():
			try:
				items.append(self.queue.get_nowait())

			except asyncio.QueueEmpty:
				break

		if not items:
			return

		try:
			await self.transport.send(items)

			logging.info(f"Dispatched batch ({len(items)} items)")

		except Exception as e:
			logging.warning(f"Dispatch failed: {e}")

	async def close(self):
		"""
		Stop dispatcher and flush remaining items.
		"""

		self._running = False

		await self.flush()
