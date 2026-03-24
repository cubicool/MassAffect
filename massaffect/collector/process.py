import asyncio
import time

from pathlib import Path

from . import Collector

class ProcessCollector(Collector):
	NAME = "process"
	AUTOLOAD = True

	SAMPLE_INTERVAL = 2.5 # seconds
	TOP_N = 5 # number of processes to report

	def __init__(self):
		super().__init__()

		self._samples = [] # list of {pid: cpu_delta}
		self._prev = {} # pid -> total_time

	# --------------------------------------------------------------------------------------------
	# Async sampler loop

	@property
	def tasks(self):
		return [self._sampler_loop()]

	# async def start(self):
	# 	asyncio.create_task(self._sampler_loop())

	async def _sampler_loop(self):
		while True:
			self._sample()

			await asyncio.sleep(self.SAMPLE_INTERVAL)

	# --------------------------------------------------------------------------------------------
	# Sampling

	def _sample(self):
		now = time.time()

		current = self._read_proc_stat()
		deltas = {}

		for pid, total in current.items():
			prev = self._prev.get(pid)

			# if prev is not None:
			# 	delta = total - prev
            #
			# 	if delta > 0:
			# 		deltas[pid] = delta

			prev = self._prev.get(pid, 0)
			delta = total - prev

			if delta > 0:
				deltas[pid] = delta

		self._prev = current

		if deltas:
			self._samples.append({
				"ts": now,
				"deltas": deltas,
			})

	# --------------------------------------------------------------------------------------------
	# Collection (called at global interval)

	def collect(self):
		if not self._samples:
			return

		# Aggregate all samples
		agg = {}

		for sample in self._samples:
			for pid, delta in sample["deltas"].items():
				agg[pid] = agg.get(pid, 0) + delta

		self._samples.clear()

		if not agg:
			return

		# Sort by total CPU time
		top = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:self.TOP_N]

		metrics = []

		for pid, total in top:
			info = self._read_proc_info(pid)

			if not info:
				continue

			metrics.append({
				"pid": pid,
				"cpu_time": total,
				**info,
			})

		if metrics:
			yield { "top": metrics }

	# --------------------------------------------------------------------------------------------
	# Helpers

	def _read_proc_stat(self):
		"""
		Returns:
			{ pid: total_cpu_time }
		"""
		proc = Path("/proc")

		result = {}

		for p in proc.iterdir():
			if not p.name.isdigit():
				continue

			pid = int(p.name)

			try:
				with (p / "stat").open() as f:
					parts = f.read().split()

				# utime + stime (fields 14, 15)
				utime = int(parts[13])
				stime = int(parts[14])

				result[pid] = utime + stime

			except Exception:
				continue

		return result

	def _read_proc_info(self, pid):
		"""
		Returns:
			{ "comm": ..., "cmdline": ... }
		"""
		base = Path("/proc") / str(pid)

		try:
			comm = (base / "comm").read_text().strip()
		except Exception:
			comm = None

		try:
			cmdline = (base / "cmdline").read_text().replace("\x00", " ").strip()
		except Exception:
			cmdline = None

		if not comm and not cmdline:
			return None

		return {
			"comm": comm,
			"cmdline": cmdline,
		}
