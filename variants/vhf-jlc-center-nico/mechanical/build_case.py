"""Build the shallow, straight-through mast enclosure."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'mechanical'))
import build_enclosure as enclosure

enclosure.ROOT = HERE
enclosure.P.update(centered_cable_entry=True, straight_cable_entry=True, pipe_center_x_mm=0)
enclosure.main()
