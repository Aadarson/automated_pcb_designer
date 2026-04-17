from kiutils.footprint import Footprint
import json

fp = Footprint()
attrs = [a for a in dir(fp) if not a.startswith("__")]
print(f"Attributes: {attrs}")

# Check for specific items
for attr in ["reference", "value", "graphicItems", "at", "position"]:
    print(f"{attr}: {hasattr(fp, attr)}")

# If graphicItems exist, see what's in there
if hasattr(fp, "graphicItems"):
    print(f"graphicItems type: {type(fp.graphicItems)}")
