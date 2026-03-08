import asyncio
import logging
import time

from . import config, create_reports
from . import application
from . import transport
from . import dispatch

logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

class Reporter(application.Application):
	def __init__(self):
		super().__init__()

		self.reports = create_reports()
		self.transport = transport.DebugPrettyTransport()
		# self.transport = transport.SlackTransport()
		self.dispatcher = dispatch.Dispatcher(self.transport, config().reporter.interval)

	async def handle_reports(self):
		"""
		Periodically evaluates reports and enqueues notifications.
		"""

		def _build_event(report_name, info):
			return {
				"report": report_name,
				"ts": int(time.time()),
				"info": info
			}

		while self.running:
			for r in self.reports:
				try:
					count = 0

					for info in r.evaluate():
						payload = _build_event(r.name(), info)

						await self.dispatcher.enqueue(payload)

						count += 1

					self.log.info(f"{r}: queued {count} notifications")

				except Exception as e:
					self.log.warning(f"{r}: evaluation failed: {e}")

			try:
				await self.wait_shutdown(config().reporter.interval)

			except asyncio.TimeoutError:
				pass

	async def startup(self):
		self.log.info("Reporter starting")

	def tasks(self):
		return [
			self.dispatcher.run(),
			self.handle_reports()
		]

	async def shutdown(self):
		await self.dispatcher.close()
		await self.transport.close()

async def main():
	reporter = Reporter()

	reporter.use_signal_handlers()

	await reporter.run()

if __name__ == "__main__":
	asyncio.run(main())
