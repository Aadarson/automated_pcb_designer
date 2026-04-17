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

s = b.to_string()
if "(module" in s or "(footprint" in s:
    print("Footprint serialized ✓")
    if "(module" in s: print("Format: (module ...)")
    if "(footprint" in s: print("Format: (footprint ...)")
else:
    print("Footprint NOT serialized ✗")
