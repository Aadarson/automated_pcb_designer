import kiutils
from kiutils.board import Board
from kiutils.items.common import Net, Position
from kiutils.items.brditems import Segment

def diag():
    print(f"kiutils version: {getattr(kiutils, '__version__', 'unknown')}")
    b = Board.create_new()
    print(f"Board attributes: {[a for a in dir(b) if not a.startswith('__')]}")
    
    n = Net(number=1, name="GND")
    print(f"Net attributes: {[a for a in dir(n) if not a.startswith('__')]}")
    
    s = Segment()
    print(f"Segment attributes: {[a for a in dir(s) if not a.startswith('__')]}")
    
    # Try to serialize a board with one net and one segment
    b.nets = [Net(number=0, name=""), n]
    s.start = Position(0,0)
    s.end = Position(10,10)
    s.net = n.number
    
    if hasattr(b, "tracks"):
        b.tracks.append(s)
        print("Added track to b.tracks")
    elif hasattr(b, "traceItems"):
        b.traceItems.append(s)
        print("Added track to b.traceItems")
    
    out = b.to_kicad()
    print("--- Serialization Start ---")
    print(out[:500])
    print("--- Serialization End ---")

if __name__ == "__main__":
    diag()
