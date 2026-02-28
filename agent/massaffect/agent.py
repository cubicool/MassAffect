import os
import asyncio
import signal
import logging
import json
import time

from . import config, create_collectors, Loggable
from . import transport
from . import dispatch

logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

class Agent(Loggable):
	def __init__(self):
		self.collectors = create_collectors()
		# self.transport = transport.HTTPTransport()
		self.transport = transport.DebugTransport()
		self.dispatcher = dispatch.Dispatcher(self.transport, config().INTERVAL)
		self.server = None

		self._running = True

	async def handle_socket(self, reader, writer):
		try:
			data = await reader.read(4096)

			if not data:
				return

			try:
				payload = json.loads(data.decode())

			except json.JSONDecodeError:
				self.log.warning("Invalid JSON received")

				return

			# Normalize to list
			if not isinstance(payload, list):
				payload = [payload]

			for item in payload:
				if not isinstance(item, dict):
					self.log.warning("Non-object JSON received")

					continue

				if "collector" not in item:
					self.log.warning("Missing 'collector' field")

					continue

				await self.dispatcher.enqueue(item)

			self.log.info("Socket payload accepted")

		except Exception as e:
			self.log.warning(f"Socket error: {e}")

		finally:
			writer.close()

			await writer.wait_closed()

	async def handle_collector(self):
		"""
		Periodically runs collectors and enqueues their payloads.
		"""

		def _build_event(collector_name, metrics):
			return {
				"collector": collector_name,
				"ts": int(time.time()),
				"metrics": metrics,
			}

		while self._running:
			for c in self.collectors:
				try:
					count = 0

					for metrics in c.collect():
						payload = _build_event(c.name(), metrics)

						await self.dispatcher.enqueue(payload)

						count += 1

					self.log.info(f"{c}: queued {count} events")

				except Exception as e:
					self.log.warning(f"{c}: collect failed: {e}")

			await asyncio.sleep(config().INTERVAL)

	async def run(self):
		self.log.info("Running")

		if not config().SOCKET_NAME.startswith("\0"):
			if os.path.exists(config().SOCKET_NAME):
				os.unlink(config().SOCKET_NAME)

		self.server = await asyncio.start_unix_server(
			self.handle_socket,
			path=config().SOCKET_NAME,
		)

		self.log.debug(f"Created socket: {config().SOCKET_NAME}")

		dispatcher_task = asyncio.create_task(self.dispatcher.run())
		server_task = asyncio.create_task(self.server.serve_forever())
		collector_task = asyncio.create_task(self.handle_collector())

		try:
			await asyncio.gather(
				collector_task,
				server_task,
				dispatcher_task
			)

		except asyncio.CancelledError:
			pass

		finally:
			self.log.info("Stopping tasks")

			server_task.cancel()
			collector_task.cancel()
			dispatcher_task.cancel()

			await asyncio.gather(
				server_task,
				collector_task,
				dispatcher_task,
				return_exceptions=True,
			)

			if self.server:
				self.server.close()

				await self.server.wait_closed()

			await self.dispatcher.close()
			await self.transport.close()

			self.log.info("Stopping tasks complete")

	def stop(self):
		self.log.info("Stopping")

		self._running = False

		if self.server:
			self.server.close()

async def main():
	agent = Agent()
	loop = asyncio.get_running_loop()

	loop.add_signal_handler(signal.SIGTERM, agent.stop)
	loop.add_signal_handler(signal.SIGINT, agent.stop)

	await agent.run()

if __name__ == "__main__":
	asyncio.run(main())
