from . import Report

class SystemReport(Report):
	NAME = "system"
	AUTOLOAD = True

	def evaluate(self):
		yield {
			"message": "System report triggered",
			"severity": "info"
		}
