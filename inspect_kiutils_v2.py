from kiutils.items.zones import Zone
import json

z = Zone()
attrs = [a for a in dir(z) if not a.startswith("__")]
print(f"Zone attributes: {attrs}")
