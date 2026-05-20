import kiutils.items.common as common
from inspect import isclass, ismodule

def inspect_module(mod, indent=0):
    for name in dir(mod):
        if name.startswith("_"): continue
        obj = getattr(mod, name)
        prefix = "  " * indent
        if isclass(obj):
            print(f"{prefix}[CLASS] {name}")
            # print first 5 attributes
            attrs = [a for a in dir(obj) if not a.startswith("_")][:5]
            if attrs: print(f"{prefix}    Attrs: {', '.join(attrs)}...")
        elif ismodule(obj):
            print(f"{prefix}[MODULE] {name}")

if __name__ == "__main__":
    print(f"--- Inspecting {common.__name__} ---")
    inspect_module(common)
