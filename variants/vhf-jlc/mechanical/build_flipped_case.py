"""Build the enclosure for the component-side-down, single-side VHF head."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'mechanical'))
import build_enclosure as enclosure

enclosure.ROOT = HERE
config = enclosure.P
config['sma_centers_mm'] = [(x, -y) for x, y in config['sma_centers_mm']]
enclosure.main()
