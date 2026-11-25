"""Fresh strict native reports, immutable evidence, and mechanical insertion check."""
from pathlib import Path
import subprocess,json,collections,sys,inspect,textwrap,hashlib
O=Path(__file__).resolve().parent;R=O.parents[1];D=O/'validation/release';D.mkdir(exist_ok=True)
k='/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def run(args):
 r=subprocess.run([k]+list(map(str,args)),capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
for b in ['preamp','biastee']:
 run(['sch','erc','--severity-all','--format','json','--output',D/(b+'_erc.json'),O/'hardware'/f'{b}.kicad_sch'])
 run(['pcb','drc','--severity-all','--all-track-errors','--schematic-parity','--format','json','--output',D/(b+'_drc.json'),O/'validation'/b/'source'/f'{b}.kicad_pcb'])
report={}
for b in ['preamp','biastee']:
 e=json.loads((D/(b+'_erc.json')).read_text());d=json.loads((D/(b+'_drc.json')).read_text());ev=[v for sh in e['sheets'] for v in sh['violations']];dv=d['violations']+d['unconnected_items']+d['schematic_parity'];assert not ev and not dv,(b,ev,dv)
 report[b]={'all_reported_findings':0,'ignored_ERC_checks':e['ignored_checks'],'ignored_DRC_checks':d['ignored_checks'],'qualification':'No reported findings; ignored checks are not validated by this result. Courtyard/footprint envelope and RF return-path review remain separate.'}
# Bias connector positions, board dimensions and component bodies are unchanged.
sys.path.insert(0,str(R/'mechanical'));import build_biastee_case as case
old=json.loads((R/'vhf/hardware/biastee_layout.json').read_text());new=json.loads((O/'hardware/biastee_layout.json').read_text());assert old['size_mm']==new['size_mm']
for a,b in zip(old['parts'],new['parts']):
 assert all(a[q]==b[q] for q in ['ref','package','x','y','rotation','side']) or a['mpn']=='1008CS-102XJRC'
# Reuse actual existing solid geometry and complete populated-board insertion sweep.
body=textwrap.dedent(inspect.getsource(case.main)).split('    stats=')[0].split('\n',1)[1];body=textwrap.dedent(body)
ns=dict(vars(case));exec(body,ns)
report['mechanical']={'biastee_insertion_sweep_mm':40,'interference_mm3':ns['interference'],'watertight_and_single_solid':all(case.mesh(s).is_watertight and len(case.mesh(s).split())==1 for s in ns['solids'].values()),'scope':'Existing case geometry with identical PCB/connector locations; component envelopes approximate; print a fit sample.'}
report['source_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'hardware').glob('*') if p.is_file()}
report['order_release']='Not granted: vendor sourcing/orientation/CAM and physical qualification remain open.'
(D/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
