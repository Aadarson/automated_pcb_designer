from kiutils.items.zones import Zone
z = Zone()
for attr in dir(z):
    if not attr.startswith("_"):
        print(attr)
