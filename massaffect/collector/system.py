import socket
import os
import time

from . import Collector

class SystemCollector(Collector):
	NAME = "system"
	AUTOLOAD = True

	def collect(self):
		load1, load5, load15 = os.getloadavg()

		cpu_cur = self._read_cpu()
		cpu_prev = self.state.get("cpu.prev")
		ts_prev = self.state.get("cpu.ts")

		cpu = None

		if cpu_prev and ts_prev:
			total_delta = cpu_cur["total"] - cpu_prev["total"]

			if total_delta > 0:
				cpu = {
					"cpu_user": (cpu_cur["user"] - cpu_prev["user"]) / total_delta * 100,
					"cpu_system": (cpu_cur["system"] - cpu_prev["system"]) / total_delta * 100,
					"cpu_idle": (cpu_cur["idle"] - cpu_prev["idle"]) / total_delta * 100,
					"cpu_iowait": (cpu_cur["iowait"] - cpu_prev["iowait"]) / total_delta * 100,
				}

		# update state
		self.state.set("cpu.prev", cpu_cur)
		self.state.set("cpu.ts", time.time())

		yield {
			# "hostname": socket.gethostname(),
			"load1": load1,
			"load5": load5,
			"load15": load15,
			**(cpu or {}),
		}

	def _read_cpu(self):
		with open("/proc/stat") as f:
			parts = f.readline().split()

		values = list(map(int, parts[1:]))

		user, nice, system, idle, iowait, irq, softirq, steal = values[:8]

		total = sum(values)

		return {
			"user": user,
			"system": system,
			"idle": idle,
			"iowait": iowait,
			"total": total,
		}
