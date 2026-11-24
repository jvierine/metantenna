"""HF high-Z prototype: pairedJFET/emitter followers then existing MMIC chain.
Balanced input is high impedance; matched50ohm architecture starts AFTER
voltage buffering. No vendor-qualified whole-system noise/IP3 claim.
"""
from design import Part,preamp,biastee
from copy import deepcopy

def hf_preamp():
 original,size=preamp();p=[]
 # Reuse power, output amplifier and connector design; replace input network.
 for a in deepcopy(original):
  keep=a.ref.startswith(('J','U')) or a.ref in {f'{c}{n+k}' for n in [100,200] for c,k in [('R',3),('R',4),('R',5),('R',6),('R',7),('R',8),('C',8),('C',9),('C',10),('C',11),('C',12),('C',13),('C',14),('L',5)]} or a.ref in ['D103','D104','L104']
  if not keep:continue
  if a.ref.startswith('U') and a.value=='GALI-74+':a.nets['1']='XY'[int(a.ref[1])-1]+'_AMP_IN'
  if a.ref in ['R106','R206']:a.value='40.2k';a.mpn='RC0805FR-0740K2L'
  if a.ref in ['R108','R208']:a.value='15 1W';a.mpn='CRCW251215R0FKEG'
  if a.ref in ['C108','C109','C208','C209']:a.value='220n 50V';a.mpn='GRM21BR71H224KA01L'
  if a.ref in ['L105','L205']:a.value='100u';a.package='SRN6045';a.mpn='SRN6045-101M';a.x=66;a.y=28 if a.ref=='L105' else 76;a.rotation=0
  if a.ref=='R205':a.x,a.y=80,72
  if a.ref=='L104':a.nets['2']='HF_PWR1'
  p.append(a)
 def add(r,v,pkg,n,x,y,rot=0,mpn='',note=''):
  p.append(Part(r,v,pkg,{str(k):v for k,v in n.items()},x,y,rot,mpn,note))
 def two(r,v,a,b,x,y,rot=0,pkg='0805',mpn=''):
  add(r,v,pkg,{1:a,2:b},x,y,rot,mpn)
 for j,s in enumerate('XY'):
  n=(j+1)*100;y=16+50*j;rail=s+'_V8'
  add(f'T{n+1}','ADT1-6T+','CD542',{1:s+'_BAL_N',2:'',3:s+'_BAL_P',4:s+'_RF_IN',5:'',6:'GND'},48 if j==0 else 32,32 if j==0 else 48,90 if j==0 else 0,mpn='ADT1-6T+',note='JLC C3304884;30kHz-125MHz; transformer AFTER high-Z voltage buffers')
  positions=[(12,43),(84,52)] if s=='X' else [(45,9),(45,84)]
  for k,(x,yy) in enumerate(positions):
   v=-1 if yy>75 else 1
   m=n+30+10*k;sg='N' if k==0 else 'P';g=s+'_ANT_'+sg;source=s+'_SF_'+sg;em=s+'_EF_'+sg;coupled=s+'_AC_'+sg;dr=s+'_D_'+sg
   add(f'Q{m}','MMBFJ310LT1G','SOT23',{1:dr,2:source,3:g},x,yy,mpn='MMBFJ310LT1G',note='Onsemi JLC C33416;pin1D2S3G;self-biased common-drain voltage buffer')
   add(f'Q{m+1}','BC850C,235','SOT23',{1:source,2:em,3:rail},x,yy+v*7,mpn='BC850C,235',note='Nexperia JLC C549507;pin1B2E3C;low-output-impedance emitter follower')
   direction=1 if x<48 else -1
   two(f'R{m}','1M',g,'GND',x+direction*6,yy,90,mpn='RC0805FR-071ML')
   two(f'R{m+1}','180',source,'GND',x+direction*6,yy+v*5,90,mpn='RC0805FR-07180RL')
   two(f'R{m+2}','220',em,'GND',x+direction*6,yy+v*10,90,mpn='RC0805FR-07220RL')
   two(f'C{m}','220n 50V',em,coupled,x,yy+v*12,mpn='GRM21BR71H224KA01L')
   two(f'R{m+3}','2.2',coupled,s+'_BAL_'+sg,x+direction*6,yy+v*15,mpn='RC0805FR-072R2L')
   two(f'R{m+4}','10',rail,dr,x+direction*4,yy-v*4,mpn='RC0805FR-0710RL')
   two(f'C{m+1}','100n',dr,'GND',x+direction*8,yy-v*4,90,mpn='GRM21BR71H104KA01L')
  # Source damping +100kHz high-pass +30MHz7-pole low-pass before GALI.
  two(f'R{n+60}','39',s+'_RF_IN',s+'_HP0',14,y,mpn='RC0805FR-0739RL')
  two(f'C{n+60}','33n',s+'_HP0',s+'_HP1',20,y,mpn='C0805C333J5GACTU')
  two(f'L{n+60}','39u',s+'_HP1','GND',24,y+4,90,pkg='1008',mpn='1008CS-393XJLC')
  two(f'C{n+61}','33n',s+'_HP1',s+'_LP0',28,y,mpn='C0805C333J5GACTU')
  nodes=[s+'_LP'+str(i) for i in range(4)]+[s+'_AMP_IN']
  for k,(val,xx) in enumerate([('120n',34),('470n',42),('470n',50),('120n',56)]):
   two(f'L{n+61+k}',val,nodes[k],nodes[k+1],xx,y,90 if k%2 else 0,mpn='0805HP-'+('121' if val=='120n' else '471')+'XGRC')
  for k,(val,xx) in enumerate([('130p',37),('220p',46),('130p',53)]):
   two(f'C{n+62+k}',val,nodes[k+1],'GND',xx,y+4,90,mpn='C0805C'+('131' if val=='130p' else '221')+'J5GACTU')
 # Broadband power extraction:1uH followed by two100uH power chokes.
 add('L106','100u','SRN6045',{1:'HF_PWR1',2:'HF_PWR2'},79,33,mpn='SRN6045-101M')
 add('L107','100u','SRN6045',{1:'HF_PWR2',2:'X_RAW'},82,25,mpn='SRN6045-101M')
 for a in p:
  if a.ref=='C140':a.x,a.y=85,61
  if a.ref=='R143':a.x,a.y=73,58
  if a.ref=='R234':a.x,a.y=38,7
  if a.ref=='R231':a.x,a.y=58,10
  if a.ref=='C230':a.x,a.y=40,26
  if a.ref=='C240':a.x,a.y=40,74
  if a.ref=='R243':a.x,a.y=30,74
 return p,size
def hf_biastee():
 p,size=biastee();p=deepcopy(p)
 for a in p:
  if a.ref in ['CM10','CM20']:
   s='X' if a.ref=='CM10' else 'Y'
   a.ref+='L';a.package='SRF0905';a.value='2mH CM';a.mpn='SRF0905-202Y';a.x=16.5
   a.nets['3']=s+'_LF_RETURN';a.nets['4']=s+'_LF_CENTER'
   a.note='Bourns JLC C2651160;both signal and shield windings;older250nH leakage bound requires confirmation'
  if a.ref in ['C10','C20','C21']:a.value='220n 50V';a.mpn='GRM21BR71H224KA01L'
  if a.ref=='C21':a.x,a.y=35,56
  if a.ref=='C10':a.x=51
  if a.ref=='C20':a.x=51
  if a.ref=='L10':a.x,a.y=29,20
  if a.ref=='F10':a.x,a.y=30,10
  if a.ref=='C11':a.x,a.y=27,15
 for j,y in enumerate([27,50]):
  s='XY'[j];n=10*(j+1)
  p.append(Part(f'CM{n}H','900R CM @100MHz','ACM4520',{'1':s+'_LF_CENTER','2':s+'_LF_RETURN','3':'GND' if j==0 else 'Y_RETURN_BLOCKED','4':s+'_COAX'},28,y,mpn='ACM4520-901-2P-T000',note='Reused VHF upper-band stage; isolated return between stages'))
 # Expand the LF bias injection impedance, without changing connector positions.
 old=next(a for a in p if a.ref=='L10');old.nets['2']='HF_DC1'
 p.append(Part('L12','100u','SRN6045',{'1':'HF_DC1','2':'HF_DC2'},34,22,90,mpn='SRN6045-101M'))
 p.append(Part('L13','100u','SRN6045',{'1':'HF_DC2','2':'X_DC'},42,26,mpn='SRN6045-101M',note='JLC C780214;0.7A, two100uH stages'))
 return p,size
