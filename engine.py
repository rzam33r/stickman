"""Retargetable motion evaluation. Units are proportions, not source-image pixels.
Pose is deterministic for any timestamp. Projection is separate from motion.
"""
import math,json,pathlib
P=pathlib.Path(__file__).parent
M=json.load(open(P/'motions.json'))
C=json.load(open(P/'characters.json'))
def clamp(v):return max(0,min(1,v))
def ease(v):v=clamp(v);return v*v*(3-2*v)
def mix(a,b,z):return a+(b-a)*z
def keys(table,t,index=1):
 # Shape-preserving Hermite interpolation. Zero tangents only at true extrema,
 # not at every authored key, so the swing does not stop in mid-air.
 x=[k[0] for k in table];y=[k[index] for k in table]
 if t<=x[0]:return y[0]
 if t>=x[-1]:return y[-1]
 slopes=[(y[k+1]-y[k])/(x[k+1]-x[k]) for k in range(len(x)-1)]
 tangents=[0.0]*len(x)
 for k in range(1,len(x)-1):
  if slopes[k-1]*slopes[k]>0:
   h0=x[k]-x[k-1];h1=x[k+1]-x[k];a=2*h1+h0;b=h1+2*h0
   tangents[k]=(a+b)/(a/slopes[k-1]+b/slopes[k])
 for k in range(len(x)-1):
  if x[k]<=t<=x[k+1]:
   h=x[k+1]-x[k];z=(t-x[k])/h
   return (2*z**3-3*z*z+1)*y[k]+(z**3-2*z*z+z)*h*tangents[k]+(-2*z**3+3*z*z)*y[k+1]+(z**3-z*z)*h*tangents[k+1]

def ik(a,b,l1,l2,sign=-1):
 delta=[b[i]-a[i] for i in range(3)];dist=math.sqrt(sum(x*x for x in delta))
 if dist>l1+l2:raise ValueError(('unreachable',dist,l1+l2))
 direction=[x/dist for x in delta];along=(l1*l1+dist*dist-l2*l2)/(2*dist);height=math.sqrt(max(0,l1*l1-along*along))
 # The knee bends forward in character space, independent of screen orientation.
 forward=[1-direction[0]**2,-direction[0]*direction[1],-direction[0]*direction[2]];norm=math.sqrt(sum(x*x for x in forward));forward=[x/norm for x in forward]
 return tuple(a[i]+direction[i]*along+forward[i]*height for i in range(3))
def softmin(a,b,radius):
 h=max(radius-abs(a-b),0)/radius
 return min(a,b)-h*h*radius*.25
def pose(c,t):
 w=M['walk'];turn=M['turn'];g=M['gesture'];L=c['thigh']+c['shin'];cycle=w['cycle'];D=w['deceleration'];a=w['full_speed_until'];v=clamp((t-a)/D);mt=min(t,a)+D*(v-v*v/2);u=mt/cycle
 moving=1-ease((t-a)/D);root=(mt-1.44)*L*w['stride']/cycle
 turnz=ease((t-turn['start'])/(turn['end']-turn['start']));yaw=math.radians(turn['initial_yaw_degrees'])*(1-turnz)
 bob=keys(w['body_height_keys'],u%1);h=mix(bob,.982,1-moving);sway=math.sin(u*math.tau)*L*.015*moving
 lean=.045*moving+math.sin(math.pi*clamp((t-5)/.4))*.016
 feet={}
 for side,offset,sgn in [('L',0,-1),('R',.5,1)]:
  phase=(u+offset)%1;k=math.floor(u+offset);anchor=(k-offset+.27)*L*w['stride']-1.44*L*w['stride']/cycle
  fx=anchor+keys(w['foot_keys'],phase,1)*L*w['stride'];fy=keys(w['foot_keys'],phase,2)*L
  angle=keys(w['foot_keys'],phase,3)*moving;rad=math.radians(angle);pivot=-20 if angle>0 else 33
  fx+=pivot*(1-math.cos(rad));fy+=12*math.cos(rad)-pivot*math.sin(rad)
  step=clamp((t-turn['start']-(0 if side=='R' else .46))/.50);z=ease(step)
  fz=sgn*c['hip_width']/2
  if t>=turn['start']:
   # Stance feet remain fixed in world space while the torso turns.
   initial=math.radians(turn['initial_yaw_degrees']);dx=fx-root
   wx=dx*math.sin(initial)+fz*math.cos(initial)
   wz=dx*math.cos(initial)-fz*math.sin(initial)
   wx=mix(wx,sgn*c['hip_width']*.74,z);wz=mix(wz,0,z)
   fx=root+wx*math.sin(yaw)+wz*math.cos(yaw)
   fz=wx*math.cos(yaw)-wz*math.sin(yaw)
  fy=mix(fy,12,z)+math.sin(math.pi*step)**2*turn['foot_step_height']*L
  feet[side]=((fx,fy,fz),angle)
 # Transfer the pelvis toward the support foot before each turning step.
 if t>=turn['start']-.16:
  first=math.sin(math.pi*clamp((t-turn['start']+.16)/.66))
  second=math.sin(math.pi*clamp((t-turn['start']-.30)/.66))
  sway+=c['hip_width']*.25*(-first+second)
 # Reach-aware pelvis solver. Never stretch or pop a knee at full extension.
 pelvisY=L*h+12
 for side,sgn in [('L',-1),('R',1)]:
  f=feet[side][0];dz=f[2]-(sway+sgn*c['hip_width']/2);dx=f[0]-root
  pelvisY=softmin(pelvisY,f[1]+math.sqrt(max(0,(L*.997)**2-dx*dx-dz*dz)),L*.025)
 roll=math.sin(u*math.tau)*.025*moving
 acting=ease((t-g['raise'])/(g['arrive']-g['raise']))*(1-ease((t-g['hold_end'])/(g['lower_end']-g['hold_end'])))
 torso_shift=-L*.018*acting+L*.003*math.sin(t*math.tau*.33)*(1-moving)
 j={'root':(root,0,0),'pelvis':(root,pelvisY,sway),'neck':(root+L*lean,pelvisY+c['torso'],sway*.5+torso_shift)}
 j['head']=(j['neck'][0]+math.sin(u*math.tau*2+.3)*1.7*moving,j['neck'][1]+c['head_radius']-2+math.sin(t*math.tau*.33)*1.2*(1-moving),j['neck'][2])
 for side,offset,sgn in [('L',0,-1),('R',.5,1)]:
  foot,angle=feet[side];hip=(root,pelvisY,sway+sgn*c['hip_width']/2)
  j['hip.'+side]=hip;j['ankle.'+side]=foot;j['knee.'+side]=ik(hip,foot,c['thigh'],c['shin'])
  sh=(j['neck'][0]+sgn*math.sin(u*math.tau)*L*.035*moving,j['neck'][1]-23+sgn*roll*L*.20,sgn*c['shoulder_width']/2+torso_shift)
  swing=-math.cos(u*math.tau+offset*math.tau)*.40*moving
  ant=math.sin(math.pi*clamp((t-g['anticipate'])/(g['raise']-g['anticipate'])))
  lift=ease((t-g['raise'])/(g['arrive']-g['raise']))*(1-ease((t-g['hold_end'])/(g['lower_end']-g['hold_end']))) if side=='L' else 0
  upper=swing-.12-ant*.05 if side=='L' else swing+.10
  # Front-view gesture comes from lateral lift, then forearm lead and wrist follow.
  elbow=(sh[0]+math.sin(upper)*c['upper_arm']*math.cos(.12),sh[1]-math.cos(upper)*c['upper_arm']*math.cos(.12),sh[2]+sgn*math.sin(.12)*c['upper_arm'])
  # Projected gesture in frontal plane, with fixed bone lengths in 3D.
  if side=='L':
   theta=mix(.12,.88,lift);elbow=(sh[0]+math.sin(upper)*c['upper_arm']*math.cos(theta),sh[1]-math.cos(upper)*c['upper_arm']*math.cos(theta),sh[2]-math.sin(theta)*c['upper_arm'])
  fa=upper+.16+math.sin(u*math.tau+offset*math.tau-.35)*.11*moving;wa=mix(.12,2.55,lift)
  wrist=(elbow[0]+math.sin(fa)*c['forearm']*math.cos(wa),elbow[1]-math.cos(fa)*c['forearm']*math.cos(wa),elbow[2]-math.sin(wa)*c['forearm']) if side=='L' else (elbow[0]+math.sin(fa)*c['forearm']*math.cos(.12),elbow[1]-math.cos(fa)*c['forearm']*math.cos(.12),elbow[2]+math.sin(.12)*c['forearm'])
  j['shoulder.'+side]=sh;j['elbow.'+side]=elbow;j['wrist.'+side]=wrist
  j['foot_angle.'+side]=angle
 smile=ease((t-M['face']['smile'])/.55);surprise=ease((t-M['face']['surprise'])/.2)*(1-smile)
 blink=max([max(0,1-abs(t-b)/.075) for b in M['face']['blink_times']])
 return {'joints':j,'yaw':yaw,'head_yaw':math.radians(turn['initial_yaw_degrees'])*(1-ease((t-turn['start']+.16)/(turn['end']-turn['start']))),'smile':smile,'surprise':surprise,'blink':blink,'thumb':ease((t-5.65)/.25)*(1-ease((t-7.7)/.4)),'moving':moving}

# The public registry dispatches by topology. Future families are not predeclared
# as implemented or silently coerced into a humanoid skeleton.
from rig_api import RigFamily,MotionSystem
SYSTEM=MotionSystem()
SKELETON=json.load(open(P/'skeleton.json'))
SYSTEM.register(RigFamily('humanoid',pose,tuple(SKELETON['required_joints']),('walk_turn_thumb',)))
def sample(character,time):return SYSTEM.sample(character,time)
