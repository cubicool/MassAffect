import aiohttp
import hmac
import hashlib
import logging
import json
import gzip

from abc import ABC, abstractmethod

from . import config, Loggable

class Transport(ABC, Loggable):
	def __init__(self):
		self.log.debug(f"Compression threshold: {config().COMPRESSION_THRESHOLD}")

	def _headers_body(self, payload):
		# Ensure we always send a list (defensive safety)
		if not isinstance(payload, list):
			payload = [payload]

		# Canonical JSON (no spaces)
		raw_body = json.dumps(
			payload,
			separators=(",", ":"),
		).encode()

		# Sign the RAW JSON
		signature = hmac.new(
			config().AGENT_SECRET.encode(),
			raw_body,
			hashlib.sha256,
		).hexdigest()

		headers = {
			"Content-Type": "application/json",
			"x-agent-signature": signature,
		}

		if len(raw_body) > config().COMPRESSION_THRESHOLD:
			body = gzip.compress(raw_body)
			ratio = len(body) / len(raw_body)

			headers["Content-Encoding"] = "gzip"

			self.log.debug(
				f"size: {len(raw_body)} "
				f"compressed: {len(body)} "
				f"ratio: {ratio:.2f}"
			)

		else:
			body = raw_body

			self.log.debug(f"size: {len(raw_body)}")

		return headers, body

	@abstractmethod
	async def send(self, payload):
		pass

class HTTPTransport(Transport):
	def __init__(self):
		self.session = aiohttp.ClientSession(
			timeout=aiohttp.ClientTimeout(total=5)
		)

		self.log.info(f"Session opened to {config().CONTROLLER_URL}")

	async def send(self, payload):
		headers, body = self._headers_body(payload)

		async with self.session.post(
			config().CONTROLLER_URL,
			data=body,
			headers=headers,
		) as resp:
			if resp.status != 200:
				raise Exception(f"Bad response: {resp.status}")

	async def close(self):
		await self.session.close()

		self.log.info("Session closed")

# Simply logs `send/close`, rather than firing them off.
class DebugTransport(Transport):
	async def send(self, payload):
		headers, body = self._headers_body(payload)

		if "Content-Encoding" in headers:
			body = gzip.decompress(body)

		self.log.info(f"Would send: {body.decode()}")

	async def close(self):
		self.log.info("Closed")

# Accumulates into the `.sent` member (for use in pytest, etc).
class TestTransport(Transport):
	def __init__(self):
		self.sent = []

	async def send(self, payload):
		self.sent.append(payload)

	async def close(self):
		pass
