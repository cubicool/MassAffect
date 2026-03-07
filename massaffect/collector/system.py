from . import Collector

import socket

class SystemCollector(Collector):
	NAME = "system"
	AUTOLOAD = True

	def collect(self):
		yield {
			"hostname": socket.gethostname(),
		}
