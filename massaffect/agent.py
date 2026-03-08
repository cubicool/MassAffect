import os
import asyncio
import logging
import json
import time

from . import config, create_collectors
from . import application
from . import transport
from . import dispatch

logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

class Agent(application.Application):
	def __init__(self):
		super().__init__()

		self.collectors = create_collectors()
		self.transport = transport.DebugPrettyTransport()
		# self.transport = transport.HTTPTransport()
		self.dispatcher = dispatch.Dispatcher(self.transport, config().agent.interval)
		self.server = None

	async def handle_socket(self, reader, writer):
		try:
			data = await reader.read()

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
				"metrics": metrics
			}

		while self.running:
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

			try:
				await self.wait_shutdown(config().agent.interval)

			except asyncio.TimeoutError:
				pass

	async def startup(self):
		socket_name = config().agent.socket_name

		if not socket_name.startswith("\0"):
			if os.path.exists(socket_name):
				os.unlink(socket_name)

		self.server = await asyncio.start_unix_server(
			self.handle_socket,
			path=socket_name
		)

		self.log.debug(f"Created socket: {socket_name.replace(chr(0), '@')}")

	def tasks(self):
		return [
			self.dispatcher.run(),
			self.server.serve_forever(),
			self.handle_collector()
		]

	async def shutdown(self):
		if self.server:
			self.server.close()

			await self.server.wait_closed()

		await self.dispatcher.close()
		await self.transport.close()

async def main():
	agent = Agent()

	agent.use_signal_handlers()

	await agent.run()

if __name__ == "__main__":
	asyncio.run(main())
