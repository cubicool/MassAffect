import logging

class Loggable:
	def __init_subclass__(cls):
		cls.log = logging.getLogger(f"{cls.__name__}")
