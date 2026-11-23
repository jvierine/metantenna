"""Gate all native ERC, DRC, unconnected-pad and schematic-parity findings."""
from pathlib import Path
import sys,re
for name in ['preamp','biastee']:
 p=Path(sys.argv[1])/name
 drc=(p/'drc.txt').read_text();erc=(p/'erc.txt').read_text()
 for category in ['DRC violations','unconnected pads','Footprint errors']:
  assert f'Found 0 {category}' in drc,(name,category)
 assert re.search(r'Errors 0\b',erc),(name,'ERC')
 print(name,'native ERC, DRC and parity: clean')
