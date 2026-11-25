"""Independent cost-down assembly variant; never writes baseline hardware.
Source and supplier references live in metadata, not visible scientific figures.
"""
from pathlib import Path
import json,shutil,hashlib,sys,html,math
from collections import defaultdict
import sexpdata as sx
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
APV='https://www.apvind.com/public/upload/20250320/4fc1cd2e99a682c5cde5d3172fbe53ae.pdf'
VALUES_CHANGED={'CRCW251241R2FKEG':'43 1W','RC0805FR-07294RL':'300'}
SUB={
 'RC0805FR-07294RL':('RC0805FR-07300RL','C114529',.006,.02),
 'C0805C102J5GACTU':('CGA4F3C0G2E102JT0Y0N','C338119',.04,.1),
 'C0805C242J5GACTU':('GRM2165C1H242JA01D','C710933',.05,.3),
 'RC0805FR-071ML':('0805W8F1004T5E','C17514',.005,.03),
 'RC0805FR-0757K6L':('FRC0805F5762TS','C5153977',.005,.03),
 'RC0805FR-0710KL':('0805W8F1002T5E','C17414',.005,.03),
 'RC0805FR-071RL':('0805W8F100KT5E','C25271',.005,.03),

 '1008CS-102XJRC':('AHW2520C-1R0JTF','C6364738',.0655,.10),
 'C0805C330F5GACTU':('CC0805JRNPO9BN330','C107115',.01,.13),
 'CRCW251241R2FKEG':('25121WF430JT4E','C620884',.0386,.05),
 '0805HP-101XGRC':('AHW2012C-R10JTF','C6808047',.04,.08),
 'C0805C161F5GACTU':('0805N161J500CT','C3855642',.01,.13),
 'C0805C360F5GACTU':('TCC0805COG360J500BT','C5375889',.01,.13),
 'C0805C750F5GACTU':('GQM2195C2E750JB12D','C2330911',.01,.13),
 'C0805C200F5GACTU':('CL21C200JBANNNC','C1798',.01,.13),
 'C0805C430F5GACTU':('CC0805JRNPO9BN430','C519921',.01,.13),
}
CODES={'GRM31CR61E106KA12L':'C77090','RC0805FR-0718RL':'C137583','1729128':'C7509570','0805HP-101XGRC':'C49640957','0805HP-121XGRC':'C43831062','0805HP-221XGRC':'C40877572','GALI-74+':'C879860','ADT1-1+':'C2683432','TPS7A4901DGNR':'C16430','SMA-KE-347A-H13.5-P':'C5723187','SMA-KWE-323C-H13X23-LW':'C5723201','ACM4520-901-2P-T000':'C41519','ACM7060-701-2PL-TL01':'C78246','BLM21PG601SN1D':'C41556732'}
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
  if old in VALUES_CHANGED:
   if 'Value' in props:props['Value'][2]=VALUES_CHANGED[old]
   for item in x:
    if tag(item,'fp_text') and str(item[1])=='value':item[2]=VALUES_CHANGED[old]
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
  metadata={'Datasheet':APV if new.startswith('AHW') else 'https://jlcpcb.com/partdetail/'+SUB[old][1],'Description':'JLC sourcing candidate; '+new}
  for key,value in metadata.items():
   if key in props:props[key][2]=value
   else:
    extra='(layer "F.Fab") (hide yes)' if tag(x,'footprint') else ''
    effect='(effects (font (size 1 1)))' if tag(x,'footprint') else '(effects (font (size 1 1)) (hide yes))'
    x.append(sx.loads('(property '+json.dumps(key)+' '+json.dumps(value)+(' (at 0 0) ' if tag(x,'footprint') else ' (at 0 0 0) ')+extra+' '+effect+')'))

 for q in x:walk(q)
for p in (O/'hardware').iterdir():
 if p.suffix not in ['.kicad_pcb','.kicad_sch']:continue
 tree=sx.loads(p.read_text())
 if p.name == 'biastee.kicad_pcb':
  # Place polarity above the installed J1 body, aligned with its two pins.
  for item in tree:
   if tag(item, 'gr_text') and item[1] in ('+12V', 'GND'):
    label, x = ('+12 V', 37.46) if item[1] == '+12V' else ('-', 42.54)
    item[:] = sx.loads(f'(gr_text "{label}" (at {x} 1.55) (layer "F.SilkS") '
                       '(effects (font (size 1.25 1.25) (thickness 0.2))))')
 if p.name == 'preamp.kicad_pcb':
  # The symmetric through-hole SMA pattern uses the same copper on either side.
  for item in tree:
   if tag(item,'footprint') and item[1] == 'metantenna:SMA':
    next(field for field in item if tag(field,'layer'))[1]='F.Cu'
 walk(tree);p.write_text('('+str(tree[0])+'\n'+'\n'.join(sx.dumps(q) for q in tree[1:])+'\n)\n')
for pkg,pitch,height in [('APV2012',.89,1.78),('APV2520',1.145,2.54)]:
 text=f'(footprint "{pkg}" (version 20221018) (generator pcbnew) (layer "F.Cu") (attr smd)'
 for pin,x in [('1',-pitch),('2',pitch)]:text+=f'(pad "{pin}" smd rect (at {x} 0) (size 1.02 {height}) (layers "F.Cu" "F.Paste" "F.Mask"))'
 (O/'hardware/metantenna.pretty'/f'{pkg}.kicad_mod').write_text(text+')\n')
# Every row is included; budget intervals are explicit, never represented as quotes.
def budget(p):
 m=p['mpn']
 if m in SUB:return SUB[m][2:]
 if m=='0805HP-121XGRC':return 1.1381,1.25
 if m=='0805HP-221XGRC':return 1.1696,1.25
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
  if name == 'preamp' and p['ref'] in ('J102','J202'):
   p['side']='F'
   p['note']='Factory assembly on component side. Install PCB component side down in enclosure.'
  old=p['mpn'];lo,hi=budget(p)
  if old in SUB:
   p['mpn'],code,*_=SUB[old]
   if old in VALUES_CHANGED:p['value']=VALUES_CHANGED[old]
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
 data={'status':'Development assembly variant; sourcing and RF qualification incomplete','batch_sets':5,'rows':allrows,'parts_per_set':cost,'changes':changes,'sources':{'inductor_datasheet':APV,'inductor_price_example':'https://www.lcsc.com/product-detail/C6808051.html','regulator_price':'https://www.lcsc.com/product-detail/C16430.html','connector_prices':'https://www.lcsc.com/brand/739-11687.html'},'excluded':['PCB fabrication','factory assembly and setup/loading fees','attrition/minimum purchase quantities','shipping and tax','coax, enclosure, antenna wire and mast','testing and engineering'],'note':'Blank LCSC codes require sourcing; populated codes are catalogue identifiers, not reserved stock.'}
(O/'manufacturing/bom.json').write_text(json.dumps(data,indent=2)+'\n')
groups=defaultdict(list)
for p in allrows:groups[(p['board'],p['value'],p['mpn'],p['lcsc'])].append(p)
s=['<!doctype html><meta charset="utf-8"><title>JLC sourcing VHF BOM</title><style>body{font:16px system-ui;max-width:1250px;margin:32px auto}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccd;text-align:left}th{background:#eef3f5}</style><h1>JLC sourcing VHF candidate — five sets</h1><p>One set: one X/Y antenna head plus one indoor bias tee. All prices below are planning allowances in USD, not a manufacturer quote. PCB and assembly costs are excluded.</p><table><tr><th>Board</th><th>Component</th><th>Part</th><th>Qty/set</th><th>Budget/set</th></tr>']
for (board,value,mpn,code),pp in groups.items():
 lo=sum(p['unit_budget_low_usd'] for p in pp);hi=sum(p['unit_budget_high_usd'] for p in pp)
 s.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [board,value,mpn,len(pp),f'${lo:.2f}–{hi:.2f}'])+'</tr>')
lo=sum(v['low'] for v in cost.values());hi=sum(v['high'] for v in cost.values());s.append(f'</table><p><b>Components/set: ${lo:.2f}–{hi:.2f}. Five sets: ${5*lo:.2f}–{5*hi:.2f}.</b></p>')
(O/'manufacturing/bom.html').write_text('\n'.join(s))
manifest={'baseline_commit':'5e540a6','source_hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'vhf/hardware').glob('*') if p.is_file()},'replaced':changes,'layout':'Four-layer stackup and connector positions retained; manufacturer APV lands and local routing repairs; baseline design untouched','sensitivity':'No measured Q in 30–55 MHz or new full-system RF qualification'}
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(cost,indent=2));print('Only variant directory written')

# Repair only the routes affected by manufacturer-recommended solder lands.
import subprocess
subprocess.run([sys.executable,str(O/"route.py")],check=True)

subprocess.run([sys.executable,str(O/"clean_bias_schematic.py")],check=True)
