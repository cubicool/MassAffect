import os
import asyncio
import signal
import logging
import pkgutil
import importlib

from transport import Transport
from config import INTERVAL, SOCKET_NAME

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s %(levelname)s %(message)s",
)

def load_collectors():
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
				collectors.append(obj())

	return collectors

class Agent:
	def __init__(self):
		self.collectors = load_collectors()
		self.transport = Transport()
		self.running = True
		self.server = None

	# Used with `asyncio.create_task` as a "server" that listens for incoming data on a socket
	# and immediately forwards it to the transport layer.
	async def handle_socket(self, reader, writer):
		try:
			data = await reader.read(4096)

			if data:
				message = data.decode().strip()

				logging.info(f"Socket received: {message}")

				# TODO: later -> parse JSON and forward to transport
				# await self.transport.send(parsed_payload)

		except Exception as e:
			logging.warning(f"Socket error: {e}")

		finally:
			writer.close()

			await writer.wait_closed()

	# Used with `asyncio.create_task` as the "main logic" for running collectors.
	async def handle_collector(self):
		while self.running:
			for c in self.collectors:
				try:
					payload = c.collect()

					# await self.transport.send(payload)

					logging.info(f"{c}: sent metrics successfully")

				except Exception as e:
					logging.warning(f"{c}: send failed: {e}")

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

		try:
			await asyncio.gather(collector_task, server_task)

		except asyncio.CancelledError:
			pass

		finally:
			logging.info("Shutting down...")

			server_task.cancel()
			collector_task.cancel()

			await asyncio.gather(server_task, collector_task, return_exceptions=True)

			self.server.close()

			await self.server.wait_closed()
			await self.transport.close()

			logging.info("Agent stopped cleanly")

	def stop(self):
		logging.info("Agent shutdown")

		self.running = False

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
