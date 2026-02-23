import asyncio
import signal
import logging

from transport import Transport
from config import INTERVAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

import pkgutil
import importlib

def load_collectors():
    import collector

    collectors = []

    for _, module_name, _ in pkgutil.iter_modules(collector.__path__):
        module = importlib.import_module(f"collector.{module_name}")
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, collector.BaseCollector) and obj is not collector.BaseCollector:
                collectors.append(obj())

    return collectors

class Agent:
    def __init__(self):
        self.collector = Collector()
        self.transport = Transport()
        self.running = True

    async def run(self):
        logging.info("Massaffect agent starting")

        while self.running:
            try:
                payload = self.collector.collect()
                await self.transport.send(payload)
                logging.info("Sent metrics successfully")
            except Exception as e:
                logging.warning(f"Send failed: {e}")

            await asyncio.sleep(INTERVAL)

        await self.transport.close()
        logging.info("Massaffect agent stopped")

    def stop(self):
        logging.info("Shutdown signal received")
        self.running = False


async def main():
    agent = Agent()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, agent.stop)
    loop.add_signal_handler(signal.SIGINT, agent.stop)

    await agent.run()


#if __name__ == "__main__":
#    asyncio.run(main())

