import asyncio
import signal

from . import Loggable

class Application(Loggable):
	def __init__(self):
		self.shutdown = asyncio.Event()
		self._tasks = []

	def stop(self):
		if self.shutdown.is_set():
			return

		self.log.info("Stopping")

		self.shutdown.set()

		# Wake tasks immediately
		for t in list(self._tasks):
			t.cancel()

	def add_task(self, coro):
		task = asyncio.create_task(coro)

		self._tasks.append(task)

		return task

	async def run_tasks(self):
		try:
			await asyncio.gather(*self._tasks, return_exceptions=True)

		finally:
			self.log.info("Stopping tasks")

			for t in list(self._tasks):
				t.cancel()

			await asyncio.gather(*self._tasks, return_exceptions=True)

			self.log.info("Stopping tasks complete")

	def install_signal_handlers(self):
		loop = asyncio.get_running_loop()

		loop.add_signal_handler(signal.SIGTERM, self.stop)
		loop.add_signal_handler(signal.SIGINT, self.stop)
