from kiutils.board import Board
from kiutils.footprint import Footprint
from kiutils.items.common import Position
import os

b = Board.create_new()
fp = Footprint()
fp.position = Position(40, 30)
fp.reference.value = "U1"

if hasattr(b, 'footprints'):
    b.footprints.append(fp)
    print("Added to board.footprints")

out_file = "test_serialization.kicad_pcb"
b.to_file(out_file)

if os.path.exists(out_file):
    content = open(out_file).read()
    print(f"File size: {len(content)} bytes")
    if "fp_text reference \"U1\"" in content or "(footprint" in content or "(module" in content:
        print("Footprint found in serialized file ✓")
        # Print a snippet around the footprint
        idx = content.find("(footprint") or content.find("(module")
        if idx != -1:
            print("Snippet: " + content[idx:idx+200])
    else:
        print("Footprint NOT found in serialized file ✗")
        print("Full Content:")
        print(content)
else:
    print("Failed to create file ✗")
