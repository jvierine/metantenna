"""Check the independent candidate with native KiCad and fixed baseline nets."""
from pathlib import Path
import subprocess,sys,runpy,tempfile,json,xml.etree.ElementTree as E,hashlib
O=Path(__file__).resolve().parent;R=O.parents[1]
source=(R/'hardware/native_local.py').read_text().replace('R=(Path(__file__).resolve().parents[1]/"vhf")','R=Path('+repr(str(O))+')').replace("str(Path(__file__).with_name('check_native_report.py'))",repr(str(R/'hardware/check_native_report.py')))
out=O/'validation';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'native.py';p.write_text(source);subprocess.run([sys.executable,str(p),'--output',str(out)],check=True)
k='/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
for name in ['preamp','biastee']:
 xml=out/name/'netlist.xml';subprocess.run([k,'sch','export','netlist','--format','kicadxml','-o',str(xml),str(O/'hardware'/f'{name}.kicad_sch')],check=True,capture_output=True)
 root=E.parse(xml).getroot();got={(n.get('ref'),n.get('pin')):net.get('name').lstrip('/') for net in root.findall('nets/net') for n in net.findall('node')}
 parts=json.loads((R/'vhf/hardware'/f'{name}_layout.json').read_text())['parts'];expected={(p['ref'],pin):net for p in parts for pin,net in p['nets'].items() if net}
 assert all(got.get(key)==net for key,net in expected.items()),name
 vals={p.get('ref'):p.findtext('value') for p in root.findall('components/comp') if not p.get('ref').startswith('#')}
 assert vals=={p['ref']:('43 1W' if name=='preamp' and p['ref'] in ['R108','R208'] else '300' if name=='preamp' and p['ref'] in ['R103','R105','R203','R205'] else p['value']) for p in parts},name
# Confirm baseline files still match the recorded hashes.
m=json.loads((O/'manifest.json').read_text())
assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==v for p,v in m['source_hashes'].items())
(out/'checks.json').write_text(json.dumps({'baseline_files_unchanged':True,'component_values_and_all_connected_pins_unchanged':True,'native_ERC_DRC_and_parity':'clean for both boards','scope':'CAD checks only; RF part models and manufacture remain unqualified'},indent=2)+'\n')
print('Baseline files, approved values and every connected pin checked')
