from kiutils.items.zones import Zone, ZonePolygon
from kiutils.items.common import Position

z = Zone()
print(f"Polygons type: {type(z.polygons)}")
zp = ZonePolygon()
print(f"ZonePolygon attributes: {dir(zp)}")
print(f"Position attributes: {dir(Position)}")
