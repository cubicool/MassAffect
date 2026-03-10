from . import Report

class SystemReport(Report):
	NAME = "system"
	AUTOLOAD = True

	def evaluate(self, req: Report.Request) -> Report.Response:
		return Report.Response(
			status=False,
			info= {
				"message": f"System report triggered for {req.agent}",
				"severity": "info"
			}
		)
