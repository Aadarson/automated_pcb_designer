import logging
import uuid
from pathlib import Path
from kiutils.board import Board
from kiutils.items.gritems import GrLine
from kiutils.items.common import Position, Net as KiNet
from kiutils.footprint import Footprint
from kiutils.items.brditems import Segment

def check_kiutils():
    board = Board.create_new()
    # Add a net
    gnd = KiNet(number=1, name="GND")
    vcc = KiNet(number=2, name="VCC")
    board.nets = [KiNet(number=0, name=""), gnd, vcc]
    
    # Check if we can assign nets to pads on a dummy segment
    seg = Segment()
    seg.start = Position(0,0)
    seg.end = Position(10,10)
    seg.net = gnd.number
    board.tracks.append(seg)
    
    # Save to dummy file
    board.to_file("test_connectivity.kicad_pcb")
    print("Saved test_connectivity.kicad_pcb. Check if 'nets' count is correct in a text editor.")

if __name__ == "__main__":
    try:
        check_kiutils()
    except Exception as e:
        print(f"Error: {e}")
