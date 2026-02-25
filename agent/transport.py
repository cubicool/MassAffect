import aiohttp
# import asyncio
import hmac
import hashlib
import logging
import json

from config import CONTROLLER_URL, AGENT_SECRET

class Transport:
	def __init__(self):
		self.session = aiohttp.ClientSession(
			timeout=aiohttp.ClientTimeout(total=5)
		)

	async def send(self, payload):
		"""
		Accepts a batch of payloads (list) and sends them
		as a single JSON array to the controller.
		"""

		# Ensure we always send a list (defensive safety)
		if not isinstance(payload, list):
			payload = [payload]

		body = json.dumps(
			payload,
			separators=(",", ":"),
		).encode()

		signature = hmac.new(
			AGENT_SECRET.encode(),
			body,
			hashlib.sha256,
		).hexdigest()

		headers = {
			"Content-Type": "application/json",
			"x-agent-signature": signature,
		}

		async with self.session.post(
			CONTROLLER_URL,
			data=body,
			headers=headers,
		) as resp:
			if resp.status != 200:
				raise Exception(f"Bad response: {resp.status}")

	async def close(self):
		await self.session.close()

class DebugTransport:
	async def send(self, payload):
		logging.info(f"[DebugTransport] Would send: {payload}")

	async def close(self):
		logging.info("[DebugTransport] Closed")

class TestTransport:
	def __init__(self):
		self.sent = []

	async def send(self, payload):
		self.sent.append(payload)

	async def close(self):
		pass
