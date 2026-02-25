#vimrun! python3 -m collector.system

from . import BaseCollector, cli_run

import socket

class SystemCollector(BaseCollector):
	name = "system"
	autoload = True

	def collect(self):
		yield {
			"hostname": socket.gethostname(),
		}

cli_run(SystemCollector, __name__)
