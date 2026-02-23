import aiohttp
import asyncio
import hmac
import hashlib
import json

from config import CONTROLLER_URL, AGENT_SECRET

class Transport:
	def __init__(self):
		self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))

	async def send(self, payload: dict):
		body = json.dumps(payload, separators=(",", ":")).encode()
		signature = hmac.new(
			AGENT_SECRET.encode(),
			body,
			hashlib.sha256
		).hexdigest()

		headers = {
			"Content-Type": "application/json",
			"x-agent-signature": signature,
		}

		async with self.session.post(CONTROLLER_URL, data=body, headers=headers) as resp:
			if resp.status != 200:
				raise Exception(f"Bad response: {resp.status}")

	async def close(self):
		await self.session.close()
