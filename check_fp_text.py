from kiutils.footprint import Footprint
from kiutils.items.fpitems import FpText

fp = Footprint()
print(f"graphicItems initially has {len(fp.graphicItems)} items.")

# In some versions, footprints have FpText items for ref and val added automatically by the parser
# but maybe not by Footprint() constructor.
# Let's try to add them manually if they are missing.

ref_text = FpText(type='reference', text='REF**')
val_text = FpText(type='value', text='VAL**')
fp.graphicItems.extend([ref_text, val_text])

print(f"graphicItems now has {len(fp.graphicItems)} items.")
for item in fp.graphicItems:
    if isinstance(item, FpText):
        print(f"FpText type: {item.type}, text: {item.text}")

# Check if 'at' and 'position' are aliases
from kiutils.items.common import Position
fp.position = Position(1, 2)
print(f"fp.position: {fp.position}, fp.at: {getattr(fp, 'at', 'N/A')}")
