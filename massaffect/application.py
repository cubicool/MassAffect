import asyncio
import signal

from . import Loggable

class Application(Loggable):
	def __init__(self):
		self._shutdown = asyncio.Event()
		self._tasks = []

	async def startup(self):
		pass

	async def shutdown(self):
		pass

	def tasks(self):
		return []

	@property
	def running(self):
		return not self._shutdown.is_set()

	async def wait_stop(self, interval):
		await asyncio.wait_for(self._shutdown.wait(), timeout=interval)

	def stop(self):
		if self._shutdown.is_set():
			return

		self.log.info("Stopping")

		self._shutdown.set()

		for t in list(self._tasks):
			t.cancel()

	def use_signal_handlers(self):
		loop = asyncio.get_running_loop()

		loop.add_signal_handler(signal.SIGTERM, self.stop)
		loop.add_signal_handler(signal.SIGINT, self.stop)

	async def run(self):
		await self.startup()

		# start background tasks
		for coro in self.tasks():
			self._tasks.append(asyncio.create_task(coro))

		try:
			await asyncio.gather(*self._tasks, return_exceptions=True)

		finally:
			self.log.info("Stopping tasks")

			for t in list(self._tasks):
				t.cancel()

			await asyncio.gather(*self._tasks, return_exceptions=True)
			await self.shutdown()

			self.log.info("Stopping tasks complete")
