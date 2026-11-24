"""Check delivered hierarchical schematic against the canonical pin/net definition.
Also checks retained indoor common-mode topology against the pre-review board.
"""
from pathlib import Path
import xml.etree.ElementTree as E
import sys,json,subprocess,hashlib
from dataclasses import asdict
from design import preamp,biastee
r=Path(__file__).resolve().parents[1]
p=Path(sys.argv[1]) if len(sys.argv)>1 else r/'simulation/nico_review/after_netlist.xml'
x=E.parse(p).getroot();got={(z.get('ref'),z.get('pin')):n.get('name') for n in x.findall('nets/net') for z in n.findall('node')}
expected={(a.ref,k):v for a in preamp()[0] for k,v in a.nets.items() if v}
assert all(got.get(k)==v for k,v in expected.items()),[(k,v,got.get(k)) for k,v in expected.items() if got.get(k)!=v]
actual={c.get('ref'):c.findtext('value') for c in x.findall('components/comp') if not c.get('ref').startswith('#')}
assert actual=={a.ref:a.value for a in preamp()[0]}
# This fixed pre-review revision includes the user's CM filters and Y shield DC block.
old=json.loads(subprocess.check_output(['git','show','f8b7d8e:vhf/hardware/biastee_layout.json'],cwd=r,text=True))
now={a.ref:asdict(a) for a in biastee()[0]};before={a['ref']:a for a in old['parts']}
for ref in before:
 for key in ['value','nets','mpn','x','y','rotation','side']:
  if key=='mpn' and before[ref]['package']=='SMA_RA':
   assert now[ref][key]=='SMA-KWE-323C-H13X23-LW';continue
  assert now[ref][key]==before[ref][key],(ref,key)
assert set(now)==set(before)
for ref in ['CM1','CM10','CM20','FB1','C21']:assert ref in now
print('All',len(expected),'connected schematic pins and',len(actual),'components agree; bias-board topology and filters retained; authorized low-cost SMA substitution')
