import pkgutil
import importlib
import inspect

def discover_plugins(package, base_class):
	plugins = []

	for _, module_name, _ in pkgutil.iter_modules(package.__path__):
		module = importlib.import_module(f"{package.__name__}.{module_name}")

		for _, obj in inspect.getmembers(module, inspect.isclass):
			if issubclass(obj, base_class) and obj is not base_class:
				plugins.append(obj)

	return plugins

def create_plugins(package, base_class):
	instances = []

	classes = discover_plugins(package, base_class)

	for cls in classes:
		if getattr(cls, "AUTOLOAD", False):
			instances.append(cls())

	return instances
