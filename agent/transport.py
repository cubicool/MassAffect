import aiohttp
import hmac
import hashlib
import logging
import json
import gzip

from config import CONTROLLER_URL, AGENT_SECRET, COMPRESSION_THRESHOLD

class Transport:
	@staticmethod
	def headers_body(payload):
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
			AGENT_SECRET.encode(),
			raw_body,
			hashlib.sha256,
		).hexdigest()

		headers = {
			"Content-Type": "application/json",
			"x-agent-signature": signature,
		}

		if len(raw_body) > COMPRESSION_THRESHOLD:
			body = gzip.compress(raw_body)
			ratio = len(body) / len(raw_body)

			headers["Content-Encoding"] = "gzip"

			logging.debug(
				f"[Transport] raw: {len(raw_body)} "
				f"compressed: {len(body)} "
				f"ratio: {ratio:.2f}"
			)

		else:
			body = raw_body

			logging.debug(f"[Transport] raw size: {len(raw_body)}")

		return headers, body

class HTTPTransport(Transport):
	def __init__(self):
		self.session = aiohttp.ClientSession(
			timeout=aiohttp.ClientTimeout(total=5)
		)

	async def send(self, payload):
		headers, body = self.headers_body(payload)

		async with self.session.post(
			CONTROLLER_URL,
			data=body,
			headers=headers,
		) as resp:
			if resp.status != 200:
				raise Exception(f"Bad response: {resp.status}")

	async def close(self):
		await self.session.close()

# Simply logs `send/close`, rather than firing them off.
class DebugTransport(Transport):
	async def send(self, payload):
		headers, body = self.headers_body(payload)

		if "Content-Encoding" in headers:
			body = gzip.decompress(body)

		logging.info(f"[DebugTransport] Would send: {body.decode()}")

	async def close(self):
		logging.info("[DebugTransport] Closed")

# Accumulates into the `.sent` member (for use in pytest, etc).
class TestTransport(Transport):
	def __init__(self):
		self.sent = []

	async def send(self, payload):
		self.sent.append(payload)

	async def close(self):
		pass
