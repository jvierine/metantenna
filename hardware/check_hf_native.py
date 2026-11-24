"""Run native KiCad checks on HF copies, retaining raw editable sources."""
from pathlib import Path
import subprocess,shutil
R=Path(__file__).resolve().parents[1];src=R/'hardware/hf/hardware';out=Path('/tmp/metantenna-hf-native');out.mkdir(exist_ok=True)
k=shutil.which('kicad-cli') or '/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
for name in ['preamp','biastee']:
 d=out/name;d.mkdir(exist_ok=True)
 for ext in ['kicad_pcb','kicad_sch','kicad_pro']:shutil.copy2(src/f'{name}.{ext}',d/f'{name}.{ext}')
 shutil.copytree(src/'metantenna.pretty',d/'metantenna.pretty',dirs_exist_ok=True);shutil.copy2(src/'fp-lib-table',d/'fp-lib-table')
 sch=d/f'{name}.kicad_sch';s=sch.read_text().replace('(paper "A2")','(paper "A1")');sch.write_text(s)
 for args in [('pcb','drc','--refill-zones','--save-board','--schematic-parity','-o',str(d/'drc.txt'),str(d/f'{name}.kicad_pcb')),('sch','erc','--severity-error','-o',str(d/'erc.txt'),str(sch)),('sch','export','pdf','-o',str(d/'schematic.pdf'),str(sch)),('pcb','export','svg','--page-size-mode','2','--exclude-drawing-sheet','-l','F.Cu,F.SilkS,Edge.Cuts','-o',str(d/'board.svg'),str(d/f'{name}.kicad_pcb'))]:
  p=subprocess.run([k,*args],capture_output=True,text=True);print(name,p.stdout,p.stderr[-300:],flush=True)
  if p.returncode:raise RuntimeError(args)
 print((d/'drc.txt').read_text()[:1600],flush=True)

subprocess.run(['conda','run','-n','base','python',str(R/'hardware/check_native_report.py'),str(out)],check=True)
