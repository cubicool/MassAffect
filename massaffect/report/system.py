from . import Report

class SystemReport(Report):
	NAME = "system"
	AUTOLOAD = True

	def evaluate(self, redis, pg):
		# for vps in list(r.scan_iter("ma:vps:*")):
		for vps in redis.smembers("ma:vps:index"):
			self.log.debug(f"vps = {vps}")

		yield {
			"message": "System report triggered",
			"severity": "info"
		}
