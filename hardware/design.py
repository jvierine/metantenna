"""Electrical source of truth for both prototype boards.

Pin numbering follows manufacturer datasheets. Never derive connectivity from
visual proximity. Empty pin nets are intentionally not connected.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class Part:
    ref:str; value:str; package:str; nets:dict; x:float; y:float
    rotation:int=0; mpn:str=''; note:str=''; side:str='F'

def preamp():
    p=[]
    def add(ref,value,pkg,nets,x,y,rot=0,mpn='',note='',side='F'):
        p.append(Part(ref,value,pkg,{str(k):v for k,v in nets.items()},x,y,rot,mpn,note,side))
    for j,y in enumerate([16,66]):
        n=100*(j+1); s='XY'[j]
        def net(a): return 'V12' if a=='V12' else (s+'_'+a if a!='GND' else 'GND')
        def two(prefix,k,val,pkg,a,b,x,yy,rot=0,mpn='',note=''):
            add(f'{prefix}{n+k}',val,pkg,{1:net(a),2:net(b)},x,yy,rot,mpn,note)
        add(f'J{n+1}',f'{s} dipole','ANT_M3',{1:net('ANT_N'),2:net('ANT_P')},48,48,rot=90 if j==0 else 0,mpn='',note='Opposite-edge solder terminals, 43 mm from board centre; housing provides wire strain relief')
        add(f'T{n+1}','ADT1-1+','CD542',{1:net('ANT_N'),2:'',3:net('ANT_P'),4:net('RF_IN'),5:'',6:'GND'},48 if j==0 else 32,32 if j==0 else 48,rot=90 if j==0 else 0,mpn='ADT1-1+')
        two('R',1,'1M','0805','ANT_P','GND',50.54 if j==0 else 25.5,40 if j==0 else 50.54,270 if j==0 else 180,mpn='RC0805FR-071ML')
        two('R',2,'1M','0805','ANT_N','GND',45.46 if j==0 else 25.5,40 if j==0 else 45.46,270 if j==0 else 180,mpn='RC0805FR-071ML')
        two('C',1,'160p','0805','RF_IN','HP',22,y,mpn='C0805C161F5GACTU')
        two('L',1,'220n','0805','HP','GND',26,y+3,90,'0805HP-221XGRC','2% RF inductor; do not substitute power inductor')
        two('C',2,'160p','0805','HP','LP1',30,y,mpn='C0805C161F5GACTU')
        two('C',3,'36p','0805','LP1','GND',33,y+3,90,'C0805C360F5GACTU')
        two('L',2,'100n','0805','LP1','LP2',38,y-1,mpn='0805HP-101XGRC')
        two('C',4,'33p','0805','LP1','LP2',38,y+2,mpn='C0805C330F5GACTU')
        two('C',5,'75p','0805','LP2','GND',43,y+3,90,'C0805C750F5GACTU')
        two('L',3,'120n','0805','LP2','AMP_IN',48,y-1,90,mpn='0805HP-121XGRC')
        two('C',6,'20p','0805','LP2','AMP_IN',48,y+2,mpn='C0805C200F5GACTU')
        two('C',7,'43p','0805','AMP_IN','GND',53,y+3,90,'C0805C430F5GACTU')
        # Optional low-capacitance anti-parallel input clamps; bench compare IMD
        # with/without populated diodes before selecting the production option.
        two('D',1,'DNP BAT15-03W','SOD323','AMP_IN','GND',55,y-4,90,'BAT15-03W','DNP; optional input clamp, not lightning protection')
        two('D',2,'DNP BAT15-03W','SOD323','GND','AMP_IN',58,y-4,90,'BAT15-03W','DNP; optional input clamp')
        add(f'U{n+1}','GALI-74+','SOT89',{1:net('AMP_IN'),2:'GND',3:net('AMP_OUT')},61,y-1.65,mpn='GALI-74+')
        two('C',8,'1n','0805','AMP_OUT','PAD_IN',66,y,mpn='C0805C102J5GACTU')
        two('R',3,'294','0805','PAD_IN','GND',70,y+3,90,'RC0805FR-07294RL')
        two('R',4,'18','0805','PAD_IN','PAD_OUT',74,y,mpn='RC0805FR-0718RL')
        two('R',5,'294','0805','PAD_OUT','GND',78,y+3,90,'RC0805FR-07294RL')
        two('C',9,'1n','0805','PAD_OUT','COAX',83,y,mpn='C0805C102J5GACTU')
        add(f'J{n+2}',s+(' RF +12V' if j==0 else ' RF, DC blocked'),'SMA',{1:net('COAX'),2:'GND'},90,26 if j==0 else y,mpn='132134',side='B',note='SMA female, standard polarity; assemble on underside')
        if j==0:
            two('L',4,'1u','1008','COAX','RAW',90,34,90,'1008CS-102XJRC')
            # Cathode pin 1 towards protected supply; anode pin 2 towards coax.
            two('D',3,'SS14','SMA_DIODE','V12','RAW',84,39,mpn='SS14')
            two('D',4,'SMAJ15A','SMA_DIODE','V12','GND',90,41,90,'SMAJ15A')
        two('C',10,'10u 25V','1206','V12','GND',75.8,(26 if j==0 else y)+17.5,90,'GRM31CR61E106KA12L')
        two('C',11,'100n 50V','0805','V12','GND',73.5,(26 if j==0 else y)+14,90,'GRM21BR71H104KA01L')
        add(f'U{n+2}','TPS7A4901DGNR','MSOP8EP',{1:net('V8'),2:net('FB'),3:'',4:'GND',5:net('V12'),6:net('NR'),7:'',8:net('V12'),9:'GND'},68,(26 if j==0 else y)+17,mpn='TPS7A4901DGNR')
        two('R',6,'57.6k','0805','V8','FB',59,(26 if j==0 else y)+16,90,'RC0805FR-0757K6L')
        two('R',7,'10k','0805','FB','GND',59,(26 if j==0 else y)+20,90,'RC0805FR-0710KL')
        two('C',12,'10u 25V','1206','V8','GND',62.5,(26 if j==0 else y)+17,90,'GRM31CR61E106KA12L')
        two('C',13,'10n 50V','0805','NR','GND',73,(26 if j==0 else y)+21,90,'GRM21BR71H103KA01L')
        two('C',14,'100n 50V','0805','V8','GND',55.5,y+9.5,90,'GRM21BR71H104KA01L')
        two('R',8,'41.2 1W','2512','V8','BIAS',61,y+10,mpn='CRCW251241R2FKEG',note='1 W; about 0.26 W normal dissipation')
        two('L',5,'1u','1008','BIAS','AMP_OUT',64,y+5,90,'1008CS-102XJRC')
    return p,(96,96)

def biastee():
    p=[]
    def add(ref,value,pkg,nets,x,y,rot=0,mpn='',note=''):
        p.append(Part(ref,value,pkg,{str(k):v for k,v in nets.items()},x,y,rot,mpn,note))
    add('J1','12 V input','TERM2',{1:'VIN',2:'SUPPLY_RETURN'},40,8,mpn='1729128',note='Phoenix 2-way 5.08 mm terminal block; + pin 1')
    add('F1','500mA PTC','1206',{1:'VIN',2:'VIN_FUSED'},40,14,mpn='1206L050/24YR')
    # TDK pins 1->4 and 2->3 are coupled windings; BOTH input wires pass
    # through CM1. Input return must not touch RF ground before pin 3.
    add('CM1','700R CM @100MHz','ACM7060',{1:'VIN_FUSED',2:'SUPPLY_RETURN',3:'GND',4:'CM_POS'},50,10,mpn='ACM7060-701-2PL-TL01',note='TDK 4A, 15mohm max per winding; LCSC C78246; 1-4 positive, 2-3 return')
    add('D1','SS14','SMA_DIODE',{1:'PROTECTED',2:'CM_POS'},60,10,mpn='SS14')
    add('FB1','600R @100MHz','0805',{1:'PROTECTED',2:'FILTERED'},60,17,mpn='BLM21PG601SN1D',note='Murata 1.4A, DCR <=0.14ohm; power-path bead, not RF signal path')
    add('C2','1n','0805',{1:'FILTERED',2:'GND'},50,20,90,mpn='C0805C102J5GACTU')
    add('C3','100n 50V','0805',{1:'FILTERED',2:'GND'},55,20,90,mpn='GRM21BR71H104KA01L')
    # RC shunt damps low-frequency resonances without a series DC voltage drop.
    add('R1','1R','0805',{1:'FILTERED',2:'DAMP'},65,17,90,mpn='RC0805FR-071RL')
    add('C4','10u 25V','1206',{1:'DAMP',2:'GND'},65,22,90,mpn='GRM31CR61E106KA12L')
    add('D2','SMAJ15A','SMA_DIODE',{1:'PROTECTED',2:'GND'},23,12,90,'SMAJ15A')
    add('C1','10u 25V','1206',{1:'PROTECTED',2:'GND'},18,12,90,'GRM31CR61E106KA12L')
    for j,y in enumerate([27,50]):
        n=10*(j+1);s='XY'[j]
        add(f'J{n}',s+(' ANT +DC' if j==0 else ' ANT RF only'),'SMA_RA',{1:s+'_COAX',2:'GND'},5,y,mpn='132203',note='Right-angle bulkhead SMA; barrel points toward left board edge; horizontal sidewall exit')
        add(f'J{n+1}',s+' RX DC BLOCK','SMA_RA',{1:s+'_RX',2:'GND'},71,y,180,mpn='132203',note='Right-angle bulkhead SMA; barrel points toward right board edge; horizontal sidewall exit')
        add(f'C{n}','1n','0805',{1:s+'_COAX',2:s+'_RX'},40,y,mpn='C0805C102J5GACTU')
        if j==0:
            add(f'L{n}','1u','1008',{1:s+'_COAX',2:s+'_DC'},20,y-6,90,'1008CS-102XJRC')
            add(f'C{n+1}','100n 50V','0805',{1:s+'_DC',2:'GND'},26,y-9,90,'GRM21BR71H104KA01L')
            add(f'F{n}','500mA PTC','1206',{1:'FILTERED',2:s+'_DC'},34,y-9,mpn='1206L050/24YR',note='500mA hold at 20C; supplies both channels; current-limited 12V supply required; verify ambient derating')
    return p,(76,64)

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    for name,fn in [('preamp',preamp),('biastee',biastee)]:
        p,size=fn()
        (root/(name+'.json')).write_text(json.dumps({'board_mm':size,'parts':[asdict(a) for a in p]},indent=2)+'\n')
