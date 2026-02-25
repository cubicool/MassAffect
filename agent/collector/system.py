#vimrun! python3 -m collector.system

from . import BaseCollector, cli_run

import socket
import time

class SystemCollector(BaseCollector):
	name = "system"
	autoload = True

	def collect(self):
		return {
			"hostname": socket.gethostname(),
			"timestamp": int(time.time())
		}

cli_run(SystemCollector, __name__)
