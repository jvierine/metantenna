"""Prepare a traceable five-set turnkey quotation bundle, not a paid-order release."""
from pathlib import Path
import sys,json,hashlib,zipfile,subprocess,shutil,collections
from openpyxl import Workbook,load_workbook
import sexpdata as sx
O=Path(__file__).resolve().parent;R=O.parents[1];D=O/'manufacturing/quote';D.mkdir(exist_ok=True)
def book(p,headers,rows):
 w=Workbook();s=w.active;s.title='Assembly';s.append(headers)
 for row in rows:s.append(row)
 s.freeze_panes='A2';s.auto_filter.ref=s.dimensions
 for col in s.columns:s.column_dimensions[col[0].column_letter].width=min(70,max(15,max(len(str(c.value or '')) for c in col)+2))
 w.save(p)
 assert list(load_workbook(p,data_only=True).active.values)==[tuple(headers)]+[tuple(r) for r in rows]
# JLC library-zero corrections, established from its placement preview.
# KiCad coordinates and rotations remain the source for footprint checks.
jlc_rotation_offsets = {
 'preamp': dict.fromkeys(('T101','T201','U101','U201','U102','U202'), -90),
 'biastee': dict.fromkeys(('J10','J11','J20','J21'), 90) | dict.fromkeys(('CM10','CM20'), -90),
}
bom=json.loads((O/'manufacturing/bom.json').read_text());records=[]
for name in ['preamp','biastee']:
 d=json.loads((O/'hardware'/f'{name}_layout.json').read_text());parts={p['ref']:p for p in d['parts']};rows=[p for p in bom['rows'] if p['board']==name];assert {p['ref'] for p in rows}=={p['ref'] for p in parts.values() if p['package']!='ANT_M3' and not p['value'].startswith('DNP')}
 # Verify centroid source against the actual native board, not merely cached JSON.
 tree=sx.loads((O/'hardware'/f'{name}.kicad_pcb').read_text())
 for fp in tree:
  if not isinstance(fp,list) or not fp or str(fp[0])!='footprint':continue
  props={str(v[1]):str(v[2]) for v in fp if isinstance(v,list) and v and str(v[0])=='property'}
  ref=props.get('Reference') or next(str(v[2]) for v in fp if isinstance(v,list) and v and str(v[0])=='fp_text' and str(v[1])=='reference');a=next(v for v in fp if isinstance(v,list) and v and str(v[0])=='at');layer=next(v[1] for v in fp if isinstance(v,list) and v and str(v[0])=='layer')
  if ref not in parts:
   assert ref.startswith('H') and 'MountingHole' in str(fp[1]),(name,ref,'unexpected footprint');continue
  part=parts[ref];assert abs(float(a[1])-part['x'])<1e-6 and abs(float(a[2])-part['y'])<1e-6,(name,ref,'centroid')
  assert (float(a[3]) if len(a)>3 else 0)%360==part['rotation']%360,(name,ref,'rotation')
  assert str(layer)==('F.Cu' if part['side']=='F' else 'B.Cu'),(name,ref,'side')
  assert props['MPN']==part['mpn'],(name,ref,'MPN')
 groups=collections.defaultdict(list)
 for p in rows:
  assert p['mpn']==parts[p['ref']]['mpn'];groups[(p['value'],p['package'],p['mpn'],p['lcsc'])].append(p['ref'])
 dest=D/name;dest.mkdir(exist_ok=True)
 br=[[v,','.join(refs),pkg,mpn,code or 'SOURCE BY EXACT MPN',len(refs)] for (v,pkg,mpn,code),refs in sorted(groups.items())]
 book(dest/'BOM.xlsx',['Comment','Designator','Footprint','Manufacturer Part Number','LCSC Part Number','Quantity per board'],br)
 cr=[[p['ref'],p['x'],-p['y'],(p['rotation']+jlc_rotation_offsets[name].get(p['ref'],0))%360,'Top' if p['side']=='F' else 'Bottom'] for p in parts.values() if p['ref'] in {r['ref'] for r in rows}]
 book(dest/'CPL.xlsx',['Designator','Mid X (mm)','Mid Y (mm)','Rotation (deg)','Layer'],cr)
 book(dest/'DNP.xlsx',['Designator','Comment'],[[p['ref'],p['value']] for p in parts.values() if p['value'].startswith('DNP')])
 with zipfile.ZipFile(dest/'Gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((O/'validation'/name/'gerbers').iterdir()):z.write(p,p.name)
 shutil.copy2(O/'validation'/name/'schematic.pdf',dest/'Schematic.pdf')
 records.append({'board':name,'quantity_fabricated_and_fully_assembled':5,'populated_parts_per_board':len(rows),'unresolved_LCSC_identifiers':sum(not p['lcsc'] for p in rows),'all_connectors_factory_assembled':True,'placement_preview':'Supplier must confirm rotation, component-side antenna SMA orientation, and horizontal bias SMA orientation before release'})
report={'source_tree_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'hardware').rglob('*') if p.is_file() and p.suffix != '.kicad_prl'},'source_base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'boards':records,'status':'QUOTATION / ENGINEERING REVIEW ONLY. Not approved for payment.','scope':'Original VHF with sourcing substitutions head and indoor bias tee; five of each; four layers. Housings and HF boards excluded.','checks':'Connected pins match baseline. R108/R208 are intentionally 43 ohm. Native electrical DRC and parity clean. ','remaining':['Supplier exact-MPN sourcing, prices and lead time','Supplier BOM/CPL orientation preview and CAM acceptance','Courtyard/component-envelope and return-path review not established by ignored-check DRC','Physical gain/noise/linearity/oscillation and -50 C cold-start testing not performed'],'electrical_model':'Behavioral matched MMIC; Q assumptions and lumped choke/cable models. No nonlinear or board-EM validation.'}
(D/'order_scope.json').write_text(json.dumps(report,indent=2)+'\n')

shutil.copy2(O/'manufacturing/bom.html',D/'BOM.html')

shutil.copytree(O/'hardware',D/'Native_KiCad',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.kicad_prl'))
(D/'sha256.json').write_text(json.dumps({str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*') if p.is_file() and p.name!='sha256.json'},indent=2)+'\n')
with zipfile.ZipFile(O/'manufacturing/vhf_jlc_sourcing_QUOTATION.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(D)))
print(json.dumps(report,indent=2))
