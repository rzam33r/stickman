from engine import *
import math,hashlib
from render import frame

def world(joint,yaw):
 x,y,z=joint
 return (x*math.sin(yaw)+z*math.cos(yaw),y,x*math.cos(yaw)-z*math.sin(yaw))
results=[]
for c in C:
 maxerr=0;lowest=1e9
 for i in range(900):
  p=sample(c,i/100);j=p['joints']
  for side in ['L','R']:
   for a,b,key in [('hip','knee','thigh'),('knee','ankle','shin'),('shoulder','elbow','upper_arm'),('elbow','wrist','forearm')]:maxerr=max(maxerr,abs(math.dist(j[a+'.'+side],j[b+'.'+side])-c[key]))
   lowest=min(lowest,j['ankle.'+side][1])
 assert maxerr<1e-8
 # The flat section of each stance must remain fixed, not slide with root.
 stance_drift=0
 for side,offset in [('L',0),('R',.5)]:
  for k in range(3):
   ts=[(k-offset+phase)*M['walk']['cycle'] for phase in [.12,.2,.3,.4]]
   if min(ts)<0 or max(ts)>2.4:continue
   positions=[sample(c,t)['joints']['ankle.'+side] for t in ts]
   stance_drift=max(stance_drift,max(math.dist(positions[0],v) for v in positions))
 assert stance_drift<1e-7
 # In a turn, verify world coordinates while that foot is the support.
 turn_drift=0
 for side,times in [('L',[3.48,3.6,3.7,3.85,3.93]),('R',[4.02,4.15,4.3,4.45])]:
  positions=[]
  for t in times:
   p=sample(c,t);j=p['joints'];a=j['ankle.'+side];root=j['root'][0]
   v=world((a[0]-root,a[1],a[2]),p['yaw']);positions.append((v[0]+root,v[1],v[2]))
  turn_drift=max(turn_drift,max(math.dist(positions[0],v) for v in positions))
 assert turn_drift<1e-7
 # Dense time sampling detects positional discontinuities and reports velocity.
 names=['head','pelvis','knee.L','knee.R','wrist.L','wrist.R','ankle.L','ankle.R']
 previous=sample(c,0)['joints'];maxstep=0;at=0;which=''
 for i in range(1,9001):
  j=sample(c,i/1000)['joints']
  for n in names:
   ds=math.dist(previous[n],j[n])
   if ds>maxstep:maxstep=ds;at=i/1000;which=n
  previous=j
 assert maxstep<2.5,'Unexpected positional jump in 1ms'
 results.append({'character':c['id'],'poses':900,'max_segment_length_error_px':maxerr,'minimum_ankle_height':lowest,'flat_stance_drift_px':stance_drift,'turn_support_drift_px':turn_drift,'largest_joint_step_per_1ms_px':maxstep,'largest_step_at_s':at,'largest_step_joint':which})
a=hashlib.sha256(frame(6.3).tobytes()).hexdigest();frame(1.3);b=hashlib.sha256(frame(6.3).tobytes()).hexdigest();assert a==b
(P/'checks.json').write_text(json.dumps({'motion_checks':results,'timestamp_deterministic':a==b,'visual_quality_pass':False,'note':'Numerical continuity, joint lengths and contact checks do not establish animation quality or rendered shoe contact.'},indent=2))
print((P/'checks.json').read_text())
