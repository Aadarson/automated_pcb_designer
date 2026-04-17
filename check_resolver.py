from backend.kicad_bridge.footprint_resolver import resolver
import os

print(f"Library binary path: {resolver.lib_path}")
print(f"Index size: {len(resolver.index)}")
if len(resolver.index) == 0:
    print("WARNING: Footprint index is EMPTY!")
    # Check if we can find any .pretty dirs manually
    if os.path.exists(resolver.lib_path):
        import glob
        pretties = glob.glob(os.path.join(resolver.lib_path, "*.pretty"))
        print(f"Found {len(pretties)} .pretty directories manually via glob.")
        if len(pretties) > 0:
            print(f"First 3: {pretties[:3]}")
    else:
        print(f"ERROR: Library path {resolver.lib_path} does not exist!")
else:
    print(f"First 5 keys in index: {list(resolver.index.keys())[:5]}")
