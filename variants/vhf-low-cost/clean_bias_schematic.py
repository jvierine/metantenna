"""Preserve bias schematic connectivity while resolving local-library/grid warnings."""
from pathlib import Path
import sexpdata as sx
import copy
O=Path(__file__).resolve().parent/'hardware'
def tag(x,k):return isinstance(x,list) and x and str(x[0])==k
p=O/'biastee.kicad_sch';t=sx.loads(p.read_text())
lib=sx.loads((O/'metantenna.kicad_sym').read_text());names={str(v[1]) for v in lib if tag(v,'symbol')}
for v in next(v for v in t if tag(v,'lib_symbols'))[1:]:
 if not tag(v,'symbol'):continue
 name=str(v[1]).split(':')[-1]
 if name not in names:
  c=copy.deepcopy(v);c[1]=name;lib.append(c);names.add(name)
 v[1]='metantenna:'+name
# Only sheet-level object coordinates. Embedded symbol pin geometry stays unchanged.
def snap(v):
 if not isinstance(v,list):return
 if tag(v,'at') or tag(v,'xy'):
  for i in [1,2]:v[i]=round(round(float(v[i])/1.27)*1.27,4)
 for child in v:snap(child)
for v in t:
 if not tag(v,'lib_symbols'):snap(v)
def save(p,t):p.write_text('('+str(t[0])+'\n'+'\n'.join(sx.dumps(v) for v in t[1:])+'\n)\n')
save(p,t);save(O/'metantenna.kicad_sym',lib)
