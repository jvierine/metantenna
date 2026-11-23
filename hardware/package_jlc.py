"""Package reviewed native KiCad CAM and Excel BOM/CPL for prototype assembly.

Requires the matching commit's GitHub Actions native-cad-checks directory.
Preserves DRC reports; does not treat a CI green check as a clean DRC report.
"""
from pathlib import Path
import argparse,json,hashlib,shutil,zipfile,re,subprocess
from collections import defaultdict
from openpyxl import Workbook
from design import preamp,biastee
R=Path(__file__).resolve().parents[1]
LCSC={'ACM4520-901-2P-T000':'C41519','ACM7060-701-2PL-TL01':'C78246','BLM21PG601SN1D':'C41556732','132203':'C6784103'}

def book(path,headers,rows):
 w=Workbook();s=w.active;s.title='Data';s.append(headers)
 for row in rows:s.append(row)
 s.freeze_panes='A2';s.auto_filter.ref=s.dimensions
 for col in s.columns:s.column_dimensions[col[0].column_letter].width=min(75,max(14,max(len(str(c.value or '')) for c in col)+2))
 w.save(path)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('native',type=Path);ap.add_argument('--commit',required=True);a=ap.parse_args()
 out=R/'manufacturing/jlc_rev_b';out.mkdir(exist_ok=True)
 status={}
 for name,fn in [('preamp',preamp),('biastee',biastee)]:
  parts,size=fn();dest=out/name;dest.mkdir(exist_ok=True);src=a.native/name
  report=(src/'drc.txt').read_text();erc=(src/'erc.txt').read_text()
  issues=re.findall(r'^\[([^]]+)\]',report,re.M)
  # Library metadata warnings are recorded, never silently suppressed.
  dangerous=issues
  if dangerous or not re.search(r'Found 0 unconnected pads',report):raise RuntimeError((name,'native DRC or parity not clean',dangerous))
  if 'Errors 0' not in erc:raise RuntimeError((name,'ERC not clean'))
  status[name]={'native_issues':issues,'dimensions_mm':size,'quantity':5,'electrical_DRC_ERC_and_parity':'pass','assembly_sides':'Full factory assembly, including through-hole connectors and bottom-side preamp SMA'}
  assert any('NPTH' in p.name for p in (src/'gerbers').glob('*.drl')), 'Need separate native NPTH drill file'
  assert any('PTH' in p.name and 'NPTH' not in p.name for p in (src/'gerbers').glob('*.drl')), 'Need separate native PTH drill file'
  with zipfile.ZipFile(dest/'Gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted((src/'gerbers').iterdir()):
    if p.suffix.lower() in ['.gtl','.gbl','.g1','.g2','.gts','.gbs','.gtp','.gbp','.gto','.gbo','.gm1','.drl']:z.write(p,p.name)
  for p in ['drc.txt','erc.txt','schematic.pdf']:shutil.copy2(src/p,dest/p)
  shutil.copy2(R/'docs'/f'{name}_assembly.pdf',dest/'Assembly.pdf')
  groups=defaultdict(list);cpl=[];manual=[];dnp=[];allgroups=defaultdict(list);allcpl=[]
  for p in parts:
   if p.package=='ANT_M3':continue
   if p.value.startswith('DNP'):
    dnp.append([p.ref,p.value,p.mpn,'DO NOT POPULATE']);continue
   allgroups[(p.value,p.package,p.mpn)].append(p.ref)
   allcpl.append([p.ref,p.x,-p.y,p.rotation,'Top' if p.side=='F' else 'Bottom'])
   if p.package in ['SMA','SMA_RA','TERM2']:
    manual.append([p.ref,p.value,p.package,p.mpn,p.side,'Factory install after SMT; see assembly drawing']);continue
   assert p.mpn,(p.ref,'missing MPN')
   groups[(p.value,p.package,p.mpn)].append(p.ref)
   cpl.append([p.ref,p.x,-p.y,p.rotation,'Top' if p.side=='F' else 'Bottom'])
  bom=[[v,','.join(refs),pkg,mpn,LCSC.get(mpn,''),len(refs)] for (v,pkg,mpn),refs in sorted(groups.items())]
  book(dest/'BOM.xlsx',['Comment','Designator','Footprint','Manufacturer Part Number','LCSC Part Number','Quantity'],bom)
  book(dest/'CPL.xlsx',['Designator','Mid X','Mid Y','Rotation','Layer'],cpl)
  book(dest/'BOM_full_assembly.xlsx',['Comment','Designator','Footprint','Manufacturer Part Number','LCSC Part Number','Quantity'],[[v,','.join(refs),pkg,mpn,LCSC.get(mpn,''),len(refs)] for (v,pkg,mpn),refs in sorted(allgroups.items())])
  book(dest/'CPL_full_assembly.xlsx',['Designator','Mid X','Mid Y','Rotation','Layer'],allcpl)
  book(dest/'Connector_assembly.xlsx',['Designator','Comment','Footprint','Manufacturer Part Number','Side','Instructions'],manual)
  book(dest/'Do_not_populate.xlsx',['Designator','Comment','Manufacturer Part Number','Instructions'],dnp)
  # Full assembly is the order default: the user will not solder connectors.
  shutil.copy2(dest/'BOM.xlsx',dest/'BOM_SMT_only.xlsx')
  shutil.copy2(dest/'CPL.xlsx',dest/'CPL_SMT_only.xlsx')
  shutil.copy2(dest/'BOM_full_assembly.xlsx',dest/'BOM.xlsx')
  shutil.copy2(dest/'CPL_full_assembly.xlsx',dest/'CPL.xlsx')
  (dest/'Hand_assembly.xlsx').unlink(missing_ok=True)
  status[name]['SMT_parts_per_board']=len(cpl);status[name]['factory_connector_parts_per_board']=len(manual)
 # A release manifest binds the checked source, native reports and actual archives.
 shutil.copy2(R/'manufacturing/JLC_ORDER.md',out/'ORDER_INSTRUCTIONS.md')
 shutil.copy2(R/'simulation/END_TO_END.md',out/'SIMULATION_SUMMARY.md')
 for p in ['end_to_end_comparison.pdf','preamp_rev_b_annotated.png','wire_exit_plan.png','biastee_case_exploded.png']:
  shutil.copy2(R/'docs'/p,out/p)
 manifest={'source_commit':a.commit,'native_CAD':('KiCad '+(a.native/'version.txt').read_text().strip()+' local CLI' if (a.native/'version.txt').exists() else 'KiCad 9.0.9 via GitHub Actions'),'boards':status,
 'order_status':'Prototype package prepared; JLC part matching, placement/rotation preview and CAM acceptance remain required before payment.',
 'model_limits':'Linear behavioral MMIC; no PCB EM or measured RF qualification.'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='sha256.json'}
 (out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
 with zipfile.ZipFile(R/'manufacturing/metantenna_rev_b_jlc_package.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(out)))
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
