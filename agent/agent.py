import os
import asyncio
import signal
import logging
import pkgutil
import importlib
import json
import time

from transport import HTTPTransport, DebugTransport
from dispatch import Dispatcher
from config import INTERVAL, SOCKET_NAME

logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s %(levelname)s %(message)s",
)

def discover_collectors():
	import collector

	collectors = []

	for _, module_name, _ in pkgutil.iter_modules(collector.__path__):
		module = importlib.import_module(f"collector.{module_name}")

		for obj in module.__dict__.values():
			if (
				isinstance(obj, type)
				and issubclass(obj, collector.BaseCollector)
				and obj is not collector.BaseCollector
			):
				collectors.append(obj)

	return collectors

def create_collectors():
	import config

	instances = []
	classes = discover_collectors()
	class_map = {cls.__name__: cls for cls in classes}

	# If autoload is set...
	for cls in classes:
		if getattr(cls, "autoload", False):
			instances.append(cls())

	# Otherwise, check for some config knobs!
	for entry in getattr(config, "COLLECTORS", []):
		cls = class_map.get(entry["type"])

		if not cls:
			raise ValueError(f"Unknown collector: {entry['type']}")

		instances.append(cls(**entry.get("config", {})))

	return instances

class Agent:
	def __init__(self):
		self.collectors = create_collectors()
		# self.transport = HTTPTransport()
		self.transport = DebugTransport()
		self.dispatcher = Dispatcher(self.transport, INTERVAL)
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
				logging.warning("Invalid JSON received")

				return

			# Normalize to list
			if not isinstance(payload, list):
				payload = [payload]

			for item in payload:
				if not isinstance(item, dict):
					logging.warning("Non-object JSON received")

					continue

				if "collector" not in item:
					logging.warning("Missing 'collector' field")

					continue

				await self.dispatcher.enqueue(item)

			logging.info("Socket payload accepted")

		except Exception as e:
			logging.warning(f"Socket error: {e}")

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
					# payload = _build_event(c.name, c.collect())

					# await self.dispatcher.enqueue(payload)

					for metrics in c.collect():
						payload = _build_event(c.name, metrics)

						await self.dispatcher.enqueue(payload)

					logging.info(f"{c}: queued metrics successfully")

				except Exception as e:
					logging.warning(f"{c}: collect failed: {e}")

			await asyncio.sleep(INTERVAL)

	async def run(self):
		logging.info("Agent starting")

		if not SOCKET_NAME.startswith("\0"):
			if os.path.exists(SOCKET_NAME):
				os.unlink(SOCKET_NAME)

		self.server = await asyncio.start_unix_server(
			self.handle_socket,
			path=SOCKET_NAME,
		)

		collector_task = asyncio.create_task(self.handle_collector())
		server_task = asyncio.create_task(self.server.serve_forever())
		dispatcher_task = asyncio.create_task(self.dispatcher.run())

		try:
			await asyncio.gather(
				collector_task,
				server_task,
				dispatcher_task
			)

		except asyncio.CancelledError:
			pass

		finally:
			logging.info("Shutting down...")

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

			logging.info("Agent stopped cleanly")

	def stop(self):
		logging.info("Agent shutdown")

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
