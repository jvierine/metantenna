"""Independent cost-down assembly variant; never writes baseline hardware.
Source and supplier references live in metadata, not visible scientific figures.
"""
from pathlib import Path
import json,shutil,hashlib,sys,html,math
from collections import defaultdict
import sexpdata as sx
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
APV='https://www.apvind.com/public/upload/20250320/4fc1cd2e99a682c5cde5d3172fbe53ae.pdf'
SUB={
 '0805HP-101XGRC':('AHW2012C-R10JTF','C6808047',.04,.08),
 '0805HP-121XGRC':('AHW2012C-R12JTF','C6364714',.04,.08),
 '0805HP-221XGRC':('AHW2012C-R22JTF','C6808051',.0436,.0458),
 '1008CS-102XJRC':('AHW2520C-1R0JTF','C6364738',.0655,.10),
}
for code in ['161','360','330','750','200','430','102']:
 old='C0805C'+code+('J' if code=='102' else 'F')+'5GACTU'
 cc={'330':'C107115','750':'C113832','430':'C519921'}.get(code,'')
 SUB[old]=('CC0805JRNPO9BN'+code,cc,.01,.13)
CODES={'GALI-74+':'C879860','ADT1-1+':'C2683432','TPS7A4901DGNR':'C16430','SMA-KE-347A-H13.5-P':'C5723187','SMA-KWE-323C-H13X23-LW':'C5723201','ACM4520-901-2P-T000':'C41519','ACM7060-701-2PL-TL01':'C78246','BLM21PG601SN1D':'C41556732'}
for d in ['hardware','manufacturing','simulation','docs']:(O/d).mkdir(exist_ok=True)
for p in (R/'vhf/hardware').iterdir():
 if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym'] or p.name.endswith('lib-table')):shutil.copy2(p,O/'hardware'/p.name)
shutil.copytree(R/'vhf/hardware/metantenna.pretty',O/'hardware/metantenna.pretty',dirs_exist_ok=True)
def tag(x,k):return isinstance(x,list) and x and str(x[0])==k
def walk(x):
 if not isinstance(x,list):return
 props={str(q[1]):q for q in x if tag(q,'property')}
 if 'MPN' in props and props['MPN'][2] in SUB:
  old=props['MPN'][2];new=SUB[old][0];props['MPN'][2]=new
  if new.startswith('AHW'):
   pkg='APV2012' if new.startswith('AHW2012') else 'APV2520'
   if 'Footprint' in props:props['Footprint'][2]='metantenna:'+pkg
   if tag(x,'footprint'):
    x[1]='metantenna:'+pkg
    pitch,height=(.89,1.78) if pkg=='APV2012' else (1.145,2.54)
    for pad in x:
     if not tag(pad,'pad'):continue
     at=next(q for q in pad if tag(q,'at'));at[1]=-pitch if pad[1]=='1' else pitch
     size=next(q for q in pad if tag(q,'size'));size[1:]=[1.02,height]
  metadata={'Datasheet':APV if new.startswith('AHW') else 'https://yageogroup.com/download/specsheet/'+new,'Description':'Cost-down candidate; '+new+'; +/-5%; RF characterization required'}
  for key,value in metadata.items():
   if key in props:props[key][2]=value
   else:
    extra='(layer "F.Fab") (hide yes)' if tag(x,'footprint') else ''
    effect='(effects (font (size 1 1)))' if tag(x,'footprint') else '(effects (font (size 1 1)) (hide yes))'
    x.append(sx.loads('(property '+json.dumps(key)+' '+json.dumps(value)+(' (at 0 0) ' if tag(x,'footprint') else ' (at 0 0 0) ')+extra+' '+effect+')'))

 for q in x:walk(q)
for p in (O/'hardware').iterdir():
 if p.suffix not in ['.kicad_pcb','.kicad_sch']:continue
 tree=sx.load(open(p));walk(tree);p.write_text('('+str(tree[0])+'\n'+'\n'.join(sx.dumps(q) for q in tree[1:])+'\n)\n')
for pkg,pitch,height in [('APV2012',.89,1.78),('APV2520',1.145,2.54)]:
 text=f'(footprint "{pkg}" (version 20221018) (generator pcbnew) (layer "F.Cu") (attr smd)'
 for pin,x in [('1',-pitch),('2',pitch)]:text+=f'(pad "{pin}" smd rect (at {x} 0) (size 1.02 {height}) (layers "F.Cu" "F.Paste" "F.Mask"))'
 (O/'hardware/metantenna.pretty'/f'{pkg}.kicad_mod').write_text(text+')\n')
# Every row is included; budget intervals are explicit, never represented as quotes.
def budget(p):
 m=p['mpn']
 if m in SUB:return SUB[m][2:]
 if m=='GALI-74+':return 3.35,4.0
 if m=='ADT1-1+':return 5.,8.
 if m=='TPS7A4901DGNR':return 1.357,1.5389
 if m=='SMA-KE-347A-H13.5-P':return .3881,.46
 if m=='SMA-KWE-323C-H13X23-LW':return 1.2773,1.55
 if m.startswith('ACM4520'):return .8,1.3
 if m.startswith('ACM7060'):return 1.0,2.5
 if m=='1729128':return .5,1.5
 if m.startswith('RC0805'):return .005,.03
 if m.startswith('CRCW'):return .1,.4
 if m.startswith('GRM'):return .03,.25
 if m.startswith('C0805'):return .05,.3
 if m.startswith('1206L'):return .2,.6
 return .05,.4
allrows=[];cost={};changes=[]
for name in ['preamp','biastee']:
 d=json.loads((R/'vhf/hardware'/f'{name}_layout.json').read_text());rows=[]
 for p in d['parts']:
  old=p['mpn'];lo,hi=budget(p)
  if old in SUB:
   p['mpn'],code,*_=SUB[old]
   if p['mpn'].startswith('AHW'):
    p['package']='APV2012' if p['mpn'].startswith('AHW2012') else 'APV2520'
    pitch,height=(.89,1.78) if p['package']=='APV2012' else (1.145,2.54)
    a=math.radians(p['rotation'])
    for pad in d['pads']:
     if pad['ref']!=p['ref']:continue
     dx=-pitch if pad['pin']=='1' else pitch
     pad.update(x=p['x']+math.cos(a)*dx,y=p['y']-math.sin(a)*dx,w=height if p['rotation']%180 else 1.02,h=1.02 if p['rotation']%180 else height)
   changes.append({'board':name,'ref':p['ref'],'old_mpn':old,'new_mpn':p['mpn']})
  else:code=CODES.get(old,'')
  if p['package']=='ANT_M3' or p['value'].startswith('DNP'):continue
  row={'board':name,'ref':p['ref'],'value':p['value'],'package':p['package'],'mpn':p['mpn'],'lcsc':code,'qty_per_board':1,'qty_five_sets':5,'unit_budget_low_usd':lo,'unit_budget_high_usd':hi,'price_status':'Planning allowance, not verified checkout quote','assembly':'Factory assembly including all connectors'}
  rows.append(row);allrows.append(row)
 (O/'hardware'/f'{name}_layout.json').write_text(json.dumps(d,indent=2)+'\n')
 cost[name]={'low':sum(p['unit_budget_low_usd'] for p in rows),'high':sum(p['unit_budget_high_usd'] for p in rows)}
 data={'status':'Development assembly variant; sourcing and RF qualification incomplete','batch_sets':5,'rows':allrows,'parts_per_set':cost,'changes':changes,'sources':{'inductor_datasheet':APV,'inductor_price_example':'https://www.lcsc.com/product-detail/C6808051.html','regulator_price':'https://www.lcsc.com/product-detail/C16430.html','connector_prices':'https://www.lcsc.com/brand/739-11687.html'},'excluded':['PCB fabrication','factory assembly and setup/loading fees','attrition/minimum purchase quantities','shipping and tax','coax, enclosure, antenna wire and mast','testing and engineering'],'note':'No promise of $20 assembled. Blank LCSC codes require sourcing; populated codes are catalogue identifiers, not reserved stock.'}
(O/'manufacturing/bom.json').write_text(json.dumps(data,indent=2)+'\n')
groups=defaultdict(list)
for p in allrows:groups[(p['board'],p['value'],p['mpn'],p['lcsc'])].append(p)
s=['<!doctype html><meta charset="utf-8"><title>Low-cost VHF BOM</title><style>body{font:16px system-ui;max-width:1250px;margin:32px auto}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccd;text-align:left}th{background:#eef3f5}</style><h1>Low-cost VHF candidate — five sets</h1><p>One set: one X/Y antenna head plus one indoor bias tee. All prices below are planning allowances in USD, not a manufacturer quote. PCB and assembly costs are excluded.</p><table><tr><th>Board</th><th>Component</th><th>Part</th><th>Qty/set</th><th>Budget/set</th></tr>']
for (board,value,mpn,code),pp in groups.items():
 lo=sum(p['unit_budget_low_usd'] for p in pp);hi=sum(p['unit_budget_high_usd'] for p in pp)
 s.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [board,value,mpn,len(pp),f'${lo:.2f}–{hi:.2f}'])+'</tr>')
lo=sum(v['low'] for v in cost.values());hi=sum(v['high'] for v in cost.values());s.append(f'</table><p><b>Components/set: ${lo:.2f}–{hi:.2f}. Five sets: ${5*lo:.2f}–{5*hi:.2f}.</b></p>')
(O/'manufacturing/bom.html').write_text('\n'.join(s))
manifest={'baseline_commit':'5e540a6','source_hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'vhf/hardware').glob('*') if p.is_file()},'replaced':changes,'layout':'Four-layer stackup and connector positions retained; manufacturer APV lands and four locally rerouted nets; baseline design untouched','sensitivity':'No measured Q in 30–55 MHz or new full-system RF qualification'}
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(cost,indent=2));print('Only variant directory written')

# Repair only the routes affected by manufacturer-recommended solder lands.
import subprocess
subprocess.run([sys.executable,str(O/"route.py")],check=True)
