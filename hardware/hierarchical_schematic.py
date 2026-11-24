"""Maintain Nico's functional schematic layout with canonical board connectivity.
Templates from pfeffer-review 478666c. Their instances, pin orientation and
hierarchy-local labels are reconciled to design.py; no change to his branch.
"""
from pathlib import Path
from copy import deepcopy as cp
import math,uuid,json
import sexpdata as sx
from sexpdata import Symbol as S
from design import preamp
R=Path(__file__).resolve().parents[1];O=R/'vhf/hardware';T=R/'hardware/schematic_templates/nico'
def node(s):return sx.loads(s)
def tag(x,t):return isinstance(x,list) and len(x)>0 and str(x[0])==t
def allof(x,t):return [a for a in x if tag(a,t)]
def one(x,t):return next(a for a in x if tag(a,t))
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'openantenna/hierarchy/'+s))
def prop(x,k):return next(a for a in allof(x,'property') if a[1]==k)
def xy(x):return tuple(round(float(v),5) for v in one(x,'at')[1:3])
def label(net,pt,kind='global_label'):
 x,y=pt
 if kind=='global_label':return node(f'(global_label "{net}" (shape bidirectional) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid(kind+net+str(pt))}"))')
 return node(f'(hierarchical_label "{net}" (shape bidirectional) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid(kind+net+str(pt))}"))')
def write(p,x):
 # Keep native editable s-expressions with top-level blocks on separate lines.
 p.write_text('('+str(x[0])+'\n'+'\n'.join(sx.dumps(a) for a in x[1:])+'\n)\n')
def pincords(sym,lib):
 a=one(sym,'at');ang=math.radians(float(a[3]));out={}
 for unit in allof(lib,'symbol'):
  for p in allof(unit,'pin'):
   v=one(p,'at');xx=float(v[1]);yy=-float(v[2]);mir=next(iter(allof(sym,'mirror')),None)
   dx=xx*math.cos(ang)+yy*math.sin(ang);dy=-xx*math.sin(ang)+yy*math.cos(ang)
   if mir:
    if str(mir[1])=='x':dy=-dy
    else:dx=-dx
   out[str(one(p,'number')[1])]=(round(float(a[1])+dx,5),round(float(a[2])+dy,5))
 return out
M={
'balun_matching':{'R109':('R101',True),'R110':('R102',True),'TR102':('T101',False)},
'chebyshev_high_pass':{'C116':('C101',True),'C117':('C102',True),'L106':('L101',True)},
'elliptic_low_pass':{'C118':('C103',True),'C119':('C104',True),'C120':('C105',True),'C121':('C106',True),'C122':('C107',True),'L107':('L102',True),'L108':('L103',True)},
'lna':{'C123':('C115',True),'C124':('C114',True),'C125':('C108',True),'U103':('U101',False),'R111':('R108',True),'L109':('L105',False),'D105':('D101',False),'D106':('D102',False)},
'attenuator':{'R112':('R103',True),'R113':('R104',True),'R114':('R105',True)},
'raw_bias_tee':{'C126':('C109',True),'L110':('L104',True),'D107':('D103',False),'D108':('D104',False)},
'dc_supply':{'C114':('C110',True),'C115':('C111',True),'C137':('C113',True),'C138':('C112',True),'R108':('R106',True),'R121':('R107',True),'U105':('U102',False)}}
PORTS={'balun_matching':{'RF_IN_N':'ANT_N','RF_IN_P':'ANT_P','RF_OUT':'RF_IN'},'chebyshev_high_pass':{'RF_IN':'RF_IN','RF_OUT':'LP1'},'elliptic_low_pass':{'RF_IN':'LP1','RF_OUT':'AMP_IN'},'lna':{'RF_IN':'AMP_IN','RF_OUT':'PAD_IN','DC_IN':'V8'},'attenuator':{'RF_IN':'PAD_IN','RF_OUT':'PAD_OUT'},'raw_bias_tee':{'RF_IN':'PAD_OUT','RF_OUT_DC_IN':'COAX','DC_OUT':'V12'},'dc_supply':{'DC_IN':'V12','DC_OUT':'V8'}}
def build():
 collected={}
 parts,size=preamp();P={p.ref:p for p in parts};rootid=uid('preamp');root=node(f'(kicad_sch (version 20260306) (generator "eeschema") (uuid "{rootid}") (paper "A2") (lib_symbols))');rootlibs=one(root,'lib_symbols');sheets=[]
 # Preserve the actual two-pin antenna footprint and connector symbols.
 old=sx.load(open(R/'hardware/schematic_templates/preamp_original.kicad_sch'));ol=one(old,'lib_symbols')
 for ref in ['J101','J201','J102','J202']:
  inst=cp(next(s for s in allof(old,'symbol') if prop(s,'Reference')[2]==ref));lib=cp(next(l for l in allof(ol,'symbol') if l[1]==one(inst,'lib_id')[1]));rootlibs.append(lib);collected[str(lib[1])]=cp(lib)
  row=0 if ref in ['J101','J102'] else 1;x=30.48 if ref in ['J101','J201'] else 421.64;y=71.12+row*129.54
  oldx,oldy=xy(inst);a=one(inst,'at');a[1:3]=[x,y]
  for pr in allof(inst,'property'):
   ap=one(pr,'at');ap[1]=float(ap[1])+x-oldx;ap[2]=float(ap[2])+y-oldy
  one(inst,'uuid')[1]=uid(ref)
  inst[:]=[q for q in inst if not tag(q,'instances')]+[node(f'(instances (project "preamp" (path "/{rootid}" (reference "{ref}") (unit 1))))')];root.append(inst)
  for pin,pt in pincords(inst,lib).items():root.append(label(P[ref].nets[pin],pt))
 for row,ch in enumerate('XY'):
  for idx,typ in enumerate(M):
   if ch=='Y' and typ=='raw_bias_tee':mapping={'C126':('C209',True)}
   else:mapping={k:((v[0][0]+str(int(v[0][1:])+100)) if ch=='Y' else v[0],v[1]) for k,v in M[typ].items()}
   filename=f'{ch.lower()}_{typ}.kicad_sch';sid=uid(ch+typ);sheetid=uid(filename);src=sx.load(open(T/(typ+'.kicad_sch')));libs=one(src,'lib_symbols');dst=node(f'(kicad_sch (version 20260306) (generator "eeschema") (uuid "{sid}") (paper "A4") (lib_symbols))');dl=one(dst,'lib_symbols');pins={};netpts={};directions={}
   for orig in allof(src,'symbol'):
    ref=prop(orig,'Reference')[2]
    if ref not in mapping:continue
    nr,flip=mapping[ref];p=P[nr];s=cp(orig);lib=cp(next(l for l in allof(libs,'symbol') if l[1]==one(s,'lib_id')[1]));newid='review:'+nr;oldid=lib[1];lib[1]=newid
    for u in allof(lib,'symbol'):u[1]=str(u[1]).replace(str(oldid).split(':')[-1],nr)
    if flip:
     for u in allof(lib,'symbol'):
      for pin in allof(u,'pin'):
       n=one(pin,'number');n[1]={'1':'2','2':'1'}.get(str(n[1]),str(n[1]))
    if p.package=='CD542':
     u=allof(lib,'symbol')[-1]
     for n,yy in [('2',10.16),('5',-10.16)]:u.append(node(f'(pin passive line (at 0 {yy} 0) (length 0) (hide yes) (name "~" (effects (font (size 1 1)))) (number "{n}" (effects (font (size 1 1)))))'))
    dl.append(lib);collected[newid]=cp(lib);one(s,'lib_id')[1]=newid;prop(s,'Reference')[2]=nr;prop(s,'Value')[2]=p.value;prop(s,'Footprint')[2]='metantenna:'+p.package
    s[:]=[q for q in s if not tag(q,'instances') and not tag(q,'pin')]
    one(s,'uuid')[1]=uid(nr);s.append(node(f'(instances (project "preamp" (path "/{rootid}/{sheetid}" (reference "{nr}") (unit 1))))'))
    s[:]=[q for q in s if not (tag(q,'property') and q[1]=='MPN')];s.append(node(f'(property "MPN" {json.dumps(p.mpn)} (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'));dst.append(s)
    for pr in allof(s,'property'):
     if pr[1]=='Description':
      ef=one(pr,'effects');ef[:]=[a for a in ef if not tag(a,'hide')];ef.append([S('hide'),S('yes')])
    for pin,pt in pincords(s,lib).items():
     cx,cy=xy(s);dx=pt[0]-cx;dy=pt[1]-cy
     directions[pt]=(0 if abs(dx)<1e-5 else (1 if dx>0 else -1),0 if abs(dy)<1e-5 else (1 if dy>0 else -1))
     if pin not in p.nets:raise ValueError((nr,pin))
     net=p.nets[pin]
     if net:pins[pt]=net;netpts.setdefault(net,[]).append(pt)
     else:dst.append(node(f'(no_connect (at {pt[0]} {pt[1]}) (uuid "{uid(nr+pin)}"))'))
   wires=cp(allof(src,'wire'));pts=set(pins)
   for w in wires:
    for point in one(w,'pts')[1:]:pts.add(tuple(map(float,point[1:3])))
   parent={a:a for a in pts}
   def find(a):
    if parent[a]!=a:parent[a]=find(parent[a])
    return parent[a]
   def union(a,b):parent[find(a)]=find(b)
   groups=[]
   for w in wires:
    a,b=[tuple(map(float,q[1:3])) for q in one(w,'pts')[1:]]
    for q in pts:
     cross=(q[0]-a[0])*(b[1]-a[1])-(q[1]-a[1])*(b[0]-a[0])
     if abs(cross)<1e-5 and min(a[0],b[0])-1e-5<=q[0]<=max(a[0],b[0])+1e-5 and min(a[1],b[1])-1e-5<=q[1]<=max(a[1],b[1])+1e-5:union(a,q)
    union(a,b);groups.append(a)
   gn={}
   for pt,n in pins.items():gn.setdefault(find(pt),set()).add(n)
   # Retain Nico's actual wires where they join the intended canonical net.
   for w,g in zip(wires,groups):
    if len(gn.get(find(g),set()))==1:dst.append(w)
   for j in allof(src,'junction'):
    pt=xy(j)
    if pt in parent and len(gn.get(find(pt),set()))==1:dst.append(cp(j))
   oldanchors=[]
   for kind in ['hierarchical_label','label','global_label']:
    oldanchors += [xy(q) for q in allof(src,kind)]
   oldanchors += [xy(q) for q in allof(src,'symbol') if str(one(q,'lib_id')[1]).startswith('power:')]
   chosen={}
   for gr in gn:
    options=[pt for pt in oldanchors if pt in parent and find(pt)==gr]
    if options:chosen[gr]=options[0]
   done=set()
   for pt,n in pins.items():
    gr=find(pt)
    if len(gn[gr])==1:
     if gr in done:continue
     done.add(gr)
    lp=chosen.get(gr,pt)
    if gr not in chosen:
     dx,dy=directions[pt];lp=(round(pt[0]+5.08*dx,5),round(pt[1]+5.08*dy,5))
     dst.append(node(f'(wire (pts (xy {pt[0]} {pt[1]}) (xy {lp[0]} {lp[1]})) (stroke (width 0) (type default)) (uuid "{uid(n+str(lp))}"))'))
    lab=label(n,lp)
    if gr not in chosen and directions[pt][0]<0:one(one(lab,'effects'),'justify')[1]=S('right')
    dst.append(lab)
   portnets={k:(v if v=='V12' else ch+'_'+v) for k,v in PORTS[typ].items()}
   if ch=='Y' and typ=='raw_bias_tee':portnets={'RF_IN':'Y_PAD_OUT','RF_OUT_DC_IN':'Y_COAX'}
   for port,net in portnets.items():
    endpoint=next(xy(q) for q in allof(dst,'global_label') if q[1]==net)
    dst.append(label(net,endpoint,'hierarchical_label'))
   # Prune old wire stubs whose old labels/power symbols were removed.
   anchors=set(pins)|{xy(q) for q in allof(dst,'global_label')+allof(dst,'hierarchical_label')}
   def touching(pt,w):
    a,z=[tuple(map(float,q[1:3])) for q in one(w,'pts')[1:]]
    return abs((pt[0]-a[0])*(z[1]-a[1])-(pt[1]-a[1])*(z[0]-a[0]))<1e-5 and min(a[0],z[0])-1e-5<=pt[0]<=max(a[0],z[0])+1e-5 and min(a[1],z[1])-1e-5<=pt[1]<=max(a[1],z[1])+1e-5
   ws=allof(dst,'wire');redundant=[]
   for i,w in enumerate(ws):
    ends=[tuple(map(float,q[1:3])) for q in one(w,'pts')[1:]]
    length=math.dist(*ends)
    for j,v in enumerate(ws):
     if i==j:continue
     vv=[tuple(map(float,q[1:3])) for q in one(v,'pts')[1:]]
     if all(touching(pt,v) for pt in ends) and (length<math.dist(*vv)-1e-6 or (abs(length-math.dist(*vv))<1e-6 and j<i)):
      redundant.append(w);break
   dst[:]=[q for q in dst if not any(q is v for v in redundant)]
   while True:
    ws=allof(dst,'wire');remove=[]
    for w in ws:
     ends=[tuple(map(float,q[1:3])) for q in one(w,'pts')[1:]]
     if any(pt not in anchors and not any(v is not w and touching(pt,v) for v in ws) for pt in ends):remove.append(w)
    if not remove:break
    dst[:]=[q for q in dst if not any(q is v for v in remove)]
   # No dangling junction markers remain after removing label-only stubs.
   dst[:]=[q for q in dst if not tag(q,'junction') or sum(touching(xy(q),w) for w in allof(dst,'wire'))>=2]
   # Explicit T-junctions are required when a new label stub spans an old end.
   ws=allof(dst,'wire');existing={xy(q) for q in allof(dst,'junction')}
   for w in ws:
    for point in one(w,'pts')[1:]:
     pt=tuple(map(float,point[1:3]))
     for v in ws:
      ends=[tuple(map(float,z[1:3])) for z in one(v,'pts')[1:]]
      if v is not w and pt not in ends and touching(pt,v) and pt not in existing:
       dst.append(node(f'(junction (at {pt[0]} {pt[1]}) (diameter 0) (color 0 0 0 0) (uuid "{uid(str(pt))}"))'));existing.add(pt)
   def unique_ids(x):
    if not isinstance(x,list):return
    if tag(x,'uuid'):x[1]=uid(ch+typ+'/'+str(x[1]));return
    for z in x:unique_ids(z)
   unique_ids(dst)
   write(O/filename,dst)
   # Root signal paths are functional blocks; globals retain canonical net names.
   if typ=='dc_supply':xx=228.6;yy=109.22+row*129.54
   else:xx=60.96+idx*55.88;yy=60.96+row*129.54
   ports=[];h=25.4;ww=45.72
   sheet=node(f'(sheet (at {xx} {yy}) (size {ww} {h}) (stroke (width 0.15) (type default)) (fill (color 255 255 210 1)) (uuid "{sheetid}") (property "Sheetname" "{ch} {typ.replace("_"," ")}" (at {xx} {yy-1} 0) (effects (font (size 1.2 1.2)) (justify left bottom))) (property "Sheetfile" "{filename}" (at {xx} {yy+h+1} 0) (effects (font (size 1 1)) (justify left top))))')
   for j,(port,net) in enumerate(portnets.items()):
    isout=port.startswith('RF_OUT') or port=='DC_OUT';px=xx+ww if isout else xx;py=yy+15.24 if port.startswith("RF_") else yy+22.86
    if port=="RF_IN_N":py=yy+17.78
    if port=="RF_IN_P":py=yy+12.7
    sheet.append(node(f'(pin "{net}" bidirectional (at {px} {py} {0 if isout else 180}) (effects (font (size 1 1)) (justify {"right" if isout else "left"})) (uuid "{uid(ch+typ+port)}"))'));root.append(label(net,(px,py)))
   
   if ch=='Y' and typ=='raw_bias_tee':prop(sheet,'Sheetname')[2]='Y output DC block'
   sheet.append(node(f'(instances (project "preamp" (path "/{rootid}" (page "{2+row*7+idx}"))))'))
   root.append(sheet)
 # Draw the signal-chain connections on the top sheet, not only net aliases.
 groups={}
 for g in allof(root,'global_label'):
  net=g[1]
  if any(k in net for k in ['ANT_','RF_IN','LP1','AMP_IN','PAD_IN','PAD_OUT','COAX']):groups.setdefault(net,[]).append(xy(g))
 for net,pp in groups.items():
  if len(pp)!=2:continue
  a,z=sorted(pp);via=(a[0],z[1]);points=[a,z] if a[1]==z[1] else [a,via,z]
  for j,(aa,bb) in enumerate(zip(points,points[1:])):
   root.append(node(f'(wire (pts (xy {aa[0]} {aa[1]}) (xy {bb[0]} {bb[1]})) (stroke (width 0) (type default)) (uuid "{uid(net+str(j))}"))'))
 # Child global nets and the visible hierarchy pins already identify RF wires.
 powerlabels=[q for q in allof(root,'global_label') if q[1] in ['GND','V12'] or q[1].endswith('_V8')]
 root[:]=[q for q in root if not tag(q,'global_label')]
 for q in powerlabels:
  pt=xy(q);end=(pt[0],round(pt[1]+7.62,5));root.append(node(f'(wire (pts (xy {pt[0]} {pt[1]}) (xy {end[0]} {end[1]})) (stroke (width 0) (type default)) (uuid "{uid(str(pt))}"))'));one(q,'at')[1:3]=list(end);root.append(q)
 # Power enters via passive SMA contacts; these are external-source flags.
 pl=sx.load(open(R/'hardware/schematic_templates/power_flag.kicad_sym'))
 flag=cp(next(z for z in allof(pl,'symbol') if z[1]=='PWR_FLAG'));flag[1]='review:PWR_FLAG';rootlibs.append(flag);collected['review:PWR_FLAG']=cp(flag)
 for i,net in enumerate(['GND','V12']):
  xx=60.96+i*25.4;yy=340.36;rf='#FLG0'+str(i)
  root.append(node(f'(symbol (lib_id "review:PWR_FLAG") (at {xx} {yy} 0) (unit 1) (in_bom no) (on_board yes) (uuid "{uid(rf)}") (property "Reference" "{rf}" (at {xx} {yy-5.08} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "PWR_FLAG" (at {xx} {yy-2.54} 0) (effects (font (size 1 1)))) (instances (project "preamp" (path "/{rootid}" (reference "{rf}") (unit 1)))))'))
  root.append(label(net,(xx,yy)))
 for libname in ['review','metantenna']:
  ll=node('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor"))')
  for k,v in collected.items():
   if k.startswith(libname+':'):
    z=cp(v);z[1]=k.split(':')[1];ll.append(z)
  write(O/(libname+'.kicad_sym'),ll)
 (O/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "review") (type "KiCad") (uri "${KIPRJMOD}/review.kicad_sym") (options "") (descr "Reviewed functional symbols")) (lib (name "metantenna") (type "KiCad") (uri "${KIPRJMOD}/metantenna.kicad_sym") (options "") (descr "Board connectors")))\n')
 write(O/'preamp.kicad_sch',root)
 print('Generated maintained Nico-style hierarchy: 15 sheets including independent Y output DC block')
if __name__=='__main__':build()
