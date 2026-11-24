"""Run local KiCad checks and CAM export without rewriting editable sources."""
from pathlib import Path
import subprocess,shutil,argparse
R=(Path(__file__).resolve().parents[1]/"vhf")
a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);opt=a.parse_args();out=opt.output.resolve();out.mkdir(parents=True,exist_ok=True)
candidates=[Path('/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'),Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')]
k=shutil.which('kicad-cli') or next((str(p) for p in candidates if p.exists()),None)
assert k,'KiCad CLI not found'
version=subprocess.check_output([k,'version'],text=True).strip();(out/'version.txt').write_text(version+'\n')
def run(*args):
 q=subprocess.run([k,*map(str,args)],capture_output=True,text=True)
 if q.returncode:raise RuntimeError(q.stdout+q.stderr)
 return q.stdout
for name in ['preamp','biastee']:
 d=out/name;d.mkdir(exist_ok=True);src=d/'source';src.mkdir(exist_ok=True)
 for ext in ['kicad_pcb','kicad_sch','kicad_pro']:shutil.copy2(R/'hardware'/f'{name}.{ext}',src/f'{name}.{ext}')
 shutil.copytree(R/'hardware/metantenna.pretty',src/'metantenna.pretty',dirs_exist_ok=True)
 shutil.copy2(R/'hardware/fp-lib-table',src/'fp-lib-table')
 b=src/f'{name}.kicad_pcb';s=src/f'{name}.kicad_sch'
 print(run('pcb','drc','--refill-zones','--save-board','--schematic-parity','-o',d/'drc.txt',b),flush=True)
 print(run('sch','erc','--severity-error','-o',d/'erc.txt',s),flush=True)
 run('sch','export','pdf','-o',d/'schematic.pdf',s)
 run('pcb','export','svg','-l','F.Cu,F.SilkS,Edge.Cuts','-o',d/'board.svg',b)
 run('pcb','export','gerbers','-l','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,Edge.Cuts','-o',str(d/'gerbers')+'/',b)
 run('pcb','export','drill','--excellon-separate-th','-o',str(d/'gerbers')+'/',b)
 shutil.copy2(b,d/f'{name}.kicad_pcb')
subprocess.run(['conda','run','-n','base','python',str(Path(__file__).with_name('check_native_report.py')),str(out)],check=True)
print('KiCad',version,'native checks complete')
