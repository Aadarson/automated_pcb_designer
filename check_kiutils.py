from kiutils.board import Board
from kiutils.footprint import Footprint

b = Board.create_new()
fp = Footprint()

print(f"Board has 'modules': {hasattr(b, 'modules')}")
print(f"Board has 'footprints': {hasattr(b, 'footprints')}")

# Add to both if they exist, to see which ones get saved
if hasattr(b, 'modules'):
    b.modules.append(fp)
if hasattr(b, 'footprints'):
    b.footprints.append(fp)

print(f"Board version: {getattr(b, 'version', 'N/A')}")
print(f"Board has {len(getattr(b, 'graphicItems', []))} graphic items.")
print(f"Board has {len(getattr(b, 'footprints', []))} footprints.")
print(f"Board has {len(getattr(b, 'modules', []))} modules.")

# To see content, we must use a temp file or just trust to_file exists
if hasattr(b, 'to_file'):
    print("Found 'to_file' method ✓")
else:
    print("NO 'to_file' method ✗")
