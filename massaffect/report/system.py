from . import Report

class SystemReport(Report):
	NAME = "system"
	AUTOLOAD = True

	def evaluate(self, redis, pg):
		# for agent in list(r.scan_iter("ma:agent:*")):
		for agent in redis.smembers("ma:agent:index"):
			self.log.debug(f"agent = {agent}")

		yield {
			"message": "System report triggered",
			"severity": "info"
		}
