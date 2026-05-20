from kiutils.items.zones import Zone
from kiutils.items.common import Position

z = Zone()
print(f"Zone attributes: {dir(z)}")

# Let's see if it has 'pts' or 'boundary' instead of 'polygon'
# Older kiutils used 'polygon'
