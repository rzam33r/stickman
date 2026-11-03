from PIL import Image,ImageDraw,ImageFilter,ImageFont,ImageChops
import math,pathlib,subprocess,json,numpy as np
from engine import *
W,H=1280,720;S=2;
ASSETS=P/'assets'
HAND=Image.open(ASSETS/'hand_thumb.png').convert('RGBA')
REST=Image.open(ASSETS/'hand-rest.png').convert('RGBA')
SHOES={s:Image.open(ASSETS/('shoe_left.png' if s=='L' else 'shoe_right.png')).convert('RGBA') for s in ['L','R']}
ASSET_CACHE={}
def appearance_assets(c):
 a=c['appearance'];key=json.dumps(a,sort_keys=True)
 if key not in ASSET_CACHE:
  ASSET_CACHE[key]=(Image.open(P/a['rest_hand']).convert('RGBA'),Image.open(P/a['thumb_hand']).convert('RGBA'),{side:Image.open(P/a['shoes'][side]).convert('RGBA') for side in ['L','R']})
 return ASSET_CACHE[key]
INK=(27,28,32);WHITE=(254,253,255);SHADE=(221,221,232)
def line(d,p,fill,width):d.line(p,fill=fill,width=max(1,round(width)),joint='curve')
def bez(a,b,c,n=24):return [((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],(1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1]) for t in np.linspace(0,1,n)]
def limb(d,a,b,c,width,fill):
 pts=bez(a,b,c,32);# smooth outline union without joint rings
 d.line(pts,fill=INK,width=round(width+5),joint='curve')
 for pt in [pts[0],pts[-1]]:d.ellipse((pt[0]-(width+5)/2,pt[1]-(width+5)/2,pt[0]+(width+5)/2,pt[1]+(width+5)/2),fill=INK)
 d.line(pts,fill=fill,width=round(width),joint='curve')
 for pt in [pts[0],pts[-1]]:d.ellipse((pt[0]-width/2,pt[1]-width/2,pt[0]+width/2,pt[1]+width/2),fill=fill)
def actor(out,c,t,origin,scale=.78):
 assert c['rig_family']=='humanoid','This renderer supports humanoids only'
 INK=tuple(c['outline']);WHITE=tuple(c['skin'])
 REST,HAND,SHOES=appearance_assets(c)
 p=sample(c,t);yaw=p['yaw'];j=p['joints'];sc=scale*S
 def project(v):return ((origin[0]+(j['root'][0]+(v[0]-j['root'][0])*math.sin(yaw)+v[2]*math.cos(yaw))*scale)*S,(origin[1]-v[1]*scale)*S)
 q={n:project(v) for n,v in j.items() if isinstance(v,tuple)};d=ImageDraw.Draw(out)
 for side in ['L','R']:
  xx,yy=q['ankle.'+side];q['leg_end.'+side]=(xx,yy-12*sc)
 def limb3(a,b,cc,width,col=WHITE):
  # Quadratic only through rounded elbow/knee, preserve silhouette bend.
  aa,bb,ccc=q[a],q[b],q[cc];pts=[aa,((aa[0]+bb[0])/2,(aa[1]+bb[1])/2),bb,((bb[0]+ccc[0])/2,(bb[1]+ccc[1])/2),ccc]
  d.line(pts,fill=INK,width=round((width+5)*sc),joint='curve')
  for x,y in pts:d.ellipse((x-(width+5)*sc/2,y-(width+5)*sc/2,x+(width+5)*sc/2,y+(width+5)*sc/2),fill=INK)
  d.line(pts,fill=col,width=round(width*sc),joint='curve')
  for x,y in pts:d.ellipse((x-width*sc/2,y-width*sc/2,x+width*sc/2,y+width*sc/2),fill=col)
 def shoe(side):
  x,y=q['ankle.'+side];angle=j['foot_angle.'+side];sag=math.sin(yaw);front=math.cos(yaw)
  # Keep the source sheet's laces, sole and shading. Direction adapts to the supported turn.
  shoe=SHOES[side].copy()
  if side=='L' and sag>.5:shoe=shoe.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
  width=int((52*sag+58*front)*sc);height=int(38*sc);shoe=shoe.resize((width,height),Image.Resampling.LANCZOS)
  shoe=shoe.rotate(angle*sag,resample=Image.Resampling.BICUBIC,expand=True)
  # Asset ankle is at 32% width when facing right; compensate around its center.
  cx=x+7*sc*sag;cy=y-6*sc
  out.paste(shoe,(int(cx-shoe.width/2),int(cy-shoe.height/2)),shoe)
 def mitt(side):
  # The reference character has no fingers. Its hands are rounded mitts with
  # a thumb that appears only when it means something, which is exactly why
  # its thumbs-up reads at small size and a modelled five-fingered hand does
  # not: at this scale a hand is a silhouette, not anatomy.
  x,y=q['wrist.'+side];ex,ey=q['elbow.'+side];th=p['thumb'] if side=='L' else 0
  ang=math.atan2(x-ex,y-ey)
  r=15.5*sc;lw=round(3.2*sc)
  if th>.04:
   # Thumb points along the forearm, away from the elbow.
   tl=r*(.55+1.05*th);tx,ty=x+math.sin(ang)*r*.55,y-math.cos(ang)*r*.55
   ux,uy=math.sin(ang)*tl,-math.cos(ang)*tl
   d.line([(tx,ty),(tx+ux,ty+uy)],fill=INK,width=round(r*.86+lw*2),joint='curve')
   d.ellipse((tx+ux-(r*.43+lw),ty+uy-(r*.43+lw),tx+ux+(r*.43+lw),ty+uy+(r*.43+lw)),fill=INK)
   d.line([(tx,ty),(tx+ux,ty+uy)],fill=WHITE,width=round(r*.86),joint='curve')
   d.ellipse((tx+ux-r*.43,ty+uy-r*.43,tx+ux+r*.43,ty+uy+r*.43),fill=WHITE)
  d.ellipse((x-r,y-r*1.06,x+r,y+r*1.06),fill=WHITE,outline=INK,width=lw)
 def hand(side):
  if c.get('appearance',{}).get('hands')=='mitt':return mitt(side)
  x,y=q['wrist.'+side];th=p['thumb'] if side=='L' else 0
  ex,ey=q['elbow.'+side]
  if side=='R':
   hi=REST.transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((int(29*sc),int(39*sc)),Image.Resampling.LANCZOS)
   ang=-math.degrees(math.atan2(x-ex,y-ey));hi=hi.rotate(ang,resample=Image.Resampling.BICUBIC,expand=True)
   out.paste(hi,(int(x-hi.width*.5),int(y-hi.height*.36)),hi)
   return
  # One source hand for the whole action: curled thumb, then extension.
  # Vertical remapping compresses only the thumb area, not the palm or fingers.
  hi=HAND.resize((int(39*sc),int(43*sc)),Image.Resampling.LANCZOS)
  arr=np.array(hi);hh,ww=arr.shape[:2];grid=np.zeros_like(arr)
  top=mix(.31,0,th)*hh;boundary=.34*hh
  for row in range(hh):
   src=(row-top)/(boundary-top)*boundary if row<boundary and boundary>top else row
   if row<top:continue
   lo=min(hh-1,max(0,int(src)));up=min(hh-1,lo+1);f=src-lo
   grid[row]=(arr[lo]*(1-f)+arr[up]*f).astype(np.uint8)
  hi=Image.fromarray(grid)
  baseang=-math.degrees(math.atan2(x-ex,y-ey))-180
  while baseang>180:baseang-=360
  while baseang<-180:baseang+=360
  ang=mix(baseang,0,th)
  # Anchor after rotation via an explicit transparent canvas.
  canvas=Image.new('RGBA',(int(110*sc),int(110*sc)))
  center=(canvas.width//2,canvas.height//2)
  canvas.paste(hi,(int(center[0]-hi.width*.23),int(center[1]-hi.height*.80)),hi)
  canvas=canvas.rotate(ang,resample=Image.Resampling.BICUBIC,center=center)
  out.paste(canvas,(round(x-center[0]),round(y-center[1])),canvas)
 # Far side silhouette first, then torso then near side, maintaining occlusion.
 limb3('shoulder.R','elbow.R','wrist.R',23,(239,239,245));hand('R')
 limb3('hip.R','knee.R','leg_end.R',35,(239,239,245));shoe('R')
 limb3('hip.L','knee.L','leg_end.L',35);shoe('L')
 nx,ny=q['neck'];px,py=q['pelvis'];bw=(c['body_width']*.5*math.cos(yaw)+25*math.sin(yaw))*sc;sw=(c['shoulder_width']*.5*math.cos(yaw)+27*math.sin(yaw))*sc
 # Build the torso and near arm as one filled silhouette to hide shoulder socket seams.
 mask=Image.new('L',out.size);md=ImageDraw.Draw(mask)
 def cubic(a,b,c,d,n=24):
  return [((1-z)**3*a[0]+3*(1-z)**2*z*b[0]+3*(1-z)*z*z*c[0]+z**3*d[0],(1-z)**3*a[1]+3*(1-z)**2*z*b[1]+3*(1-z)*z*z*c[1]+z**3*d[1]) for z in np.linspace(0,1,n)]
 hipw=(c['hip_width']/2*math.cos(yaw)+11*math.sin(yaw)+17.5)*sc
 left=cubic((nx-18*sc,ny-2*sc),(nx-sw,ny-2*sc),(nx-sw-9*sc,ny+18*sc),(nx-sw-5*sc,ny+45*sc))
 left+=cubic(left[-1],(nx-sw+2*sc,ny+80*sc),(px-hipw,py-20*sc),(px-hipw,py+12*sc))
 right=cubic((nx+18*sc,ny-2*sc),(nx+sw,ny-2*sc),(nx+sw+9*sc,ny+18*sc),(nx+sw+5*sc,ny+45*sc))
 right+=cubic(right[-1],(nx+sw-2*sc,ny+80*sc),(px+hipw,py-20*sc),(px+hipw,py+12*sc))
 # Continue the hips into the thigh edges, rather than leaving a shirt-like hem.
 thighpoints=[]
 for side in ['R','L']:
  hx,hy=q['hip.'+side];kx,ky=q['knee.'+side]
  thighpoints.append((mix(hx,kx,.36),mix(hy,ky,.36)))
 lth=min(thighpoints,key=lambda v:v[0]);rth=max(thighpoints,key=lambda v:v[0])
 left+=cubic(left[-1],(left[-1][0],py+20*sc),(lth[0]-17.5*sc,lth[1]-8*sc),(lth[0]-17.5*sc,lth[1]))
 right+=cubic(right[-1],(right[-1][0],py+20*sc),(rth[0]+17.5*sc,rth[1]-8*sc),(rth[0]+17.5*sc,rth[1]))
 pts=left+[(px,py+23*sc)]+right[::-1];md.polygon(pts,fill=255)
 # Rounded hip union blends the hidden far limb into the torso.
 hx,hy=q['hip.R'];md.ellipse((hx-18*sc,hy-12*sc,hx+18*sc,hy+24*sc),fill=255)
 # Merge near leg into the torso. The far leg keeps a single overlap contour.
 for side in ['R','L']:
  lp=[q['hip.'+side],q['knee.'+side],q['leg_end.'+side]]
  md.line(lp,fill=255,width=round(35*sc),joint='curve')
  for xx,yy in lp:md.ellipse((xx-17.5*sc,yy-17.5*sc,xx+17.5*sc,yy+17.5*sc),fill=255)
 for side in ['R','L']:
  ap=[q['shoulder.'+side],q['elbow.'+side],q['wrist.'+side]]
  md.line(ap,fill=255,width=round(23*sc),joint='curve')
  for xx,yy in ap:md.ellipse((xx-11.5*sc,yy-11.5*sc,xx+11.5*sc,yy+11.5*sc),fill=255)
 outline=mask.filter(ImageFilter.MaxFilter(2*int(round(1.5*sc))+1));layer=Image.new('RGB',out.size,INK);out.paste(layer,(0,0),outline);layer=Image.new('RGB',out.size,WHITE);out.paste(layer,(0,0),mask)
 # ---- clothing ---------------------------------------------------------
 # Not decoration. In the reference the shirt and trousers are what separate
 # arm from torso and leg from leg: every edge that reads as an edge is a
 # colour change, not a line. Drawn as flat blocks clipped to the silhouette
 # that already exists, so the outline, the limbs and the motion are
 # untouched -- this only says which parts of the same shape are cloth.
 SHIRT=tuple(c.get('shirt',WHITE));TROUSERS=tuple(c.get('trousers',WHITE))
 if 'shirt' in c or 'trousers' in c:
  hem=py+c.get('hem',20)*sc
  below=Image.new('L',out.size);ImageDraw.Draw(below).rectangle((0,hem,out.width,out.height),fill=255)
  above=ImageChops.invert(below)
  legs=Image.new('L',out.size);ld=ImageDraw.Draw(legs)
  for side in ['R','L']:
   lp=[q['hip.'+side],q['knee.'+side],q['leg_end.'+side]]
   ld.line(lp,fill=255,width=round(35*sc),joint='curve')
   for xx,yy in lp:ld.ellipse((xx-17.5*sc,yy-17.5*sc,xx+17.5*sc,yy+17.5*sc),fill=255)
  # Sleeves stop part way down the upper arm, which is what makes the arm
  # read as an arm against the body rather than merging into it.
  sleeves=Image.new('L',out.size);sd=ImageDraw.Draw(sleeves)
  for side in ['R','L']:
   ax,ay=q['shoulder.'+side];bx,by=q['elbow.'+side];f=c.get('sleeve',.46)
   ep=(mix(ax,bx,f),mix(ay,by,f))
   sd.line([(ax,ay),ep],fill=255,width=round(27*sc),joint='curve')
   for xx,yy in [(ax,ay),ep]:sd.ellipse((xx-13.5*sc,yy-13.5*sc,xx+13.5*sc,yy+13.5*sc),fill=255)
  # The arms live inside the body mask too, so the shirt has to be the body
  # minus the arms, or the sleeve runs all the way to the wrist and the whole
  # point -- a white forearm reading against a coloured torso -- is lost.
  arms=Image.new('L',out.size);ad=ImageDraw.Draw(arms)
  for side in ['R','L']:
   ap=[q['shoulder.'+side],q['elbow.'+side],q['wrist.'+side]]
   ad.line(ap,fill=255,width=round(23*sc),joint='curve')
   for xx,yy in ap:ad.ellipse((xx-11.5*sc,yy-11.5*sc,xx+11.5*sc,yy+11.5*sc),fill=255)
  body=ImageChops.subtract(ImageChops.subtract(mask,legs),arms)
  trouser=ImageChops.multiply(ImageChops.lighter(legs,ImageChops.multiply(mask,below)),mask)
  shirt=ImageChops.multiply(ImageChops.lighter(ImageChops.multiply(body,above),sleeves),mask)
  out.paste(TROUSERS,(0,0,out.width,out.height),trouser)
  out.paste(SHIRT,(0,0,out.width,out.height),shirt)
 # A narrow shaded contour supplies volume without changing the joint system.
 inset=ImageChops.offset(mask,-max(1,round(5*sc)), -max(1,round(1*sc)))
 rim=ImageChops.subtract(mask,inset)
 rim=ImageChops.multiply(rim,Image.new('L',out.size,150))
 out.paste(SHADE,(0,0,out.width,out.height),rim)
 # Draw the near leg's actual overlap boundary where it covers the far leg.
 # This follows the vector silhouette instead of an invented centerline.
 near=Image.new('L',out.size);nd=ImageDraw.Draw(near)
 lp=[q['hip.L'],q['knee.L'],q['leg_end.L']]
 nd.line(lp,fill=255,width=round(35*sc),joint='curve')
 for xx,yy in lp:nd.ellipse((xx-17.5*sc,yy-17.5*sc,xx+17.5*sc,yy+17.5*sc),fill=255)
 far=Image.new('L',out.size);fd=ImageDraw.Draw(far)
 lp=[q['hip.R'],q['knee.R'],q['leg_end.R']]
 fd.line(lp,fill=255,width=round(35*sc),joint='curve')
 for xx,yy in lp:fd.ellipse((xx-17.5*sc,yy-17.5*sc,xx+17.5*sc,yy+17.5*sc),fill=255)
 edge=ImageChops.subtract(near.filter(ImageFilter.MaxFilter(2*max(1,round(1.2*sc))+1)),near)
 edge=ImageChops.multiply(edge,far)
 cutoff=Image.new('L',out.size);cd=ImageDraw.Draw(cutoff);cd.rectangle((0,py+27*sc,out.width,out.height),fill=255)
 edge=ImageChops.multiply(edge,cutoff)
 out.paste(INK,(0,0,out.width,out.height),edge)
 # Inner edge lies on the arm boundary, never through the arm's center.
 for side in ['R','L']:
  if side=='R' and yaw>.85:continue
  aa,bb,cc=q['shoulder.'+side],q['elbow.'+side],q['wrist.'+side]
  pts=[];sgn=1 if side=='L' else -1
  # Choose the normal facing inward at the shoulder.
  ux,uy=bb[0]-aa[0],bb[1]-aa[1];n=math.hypot(ux,uy);nx2,ny2=-uy/n,ux/n
  if nx2*sgn<0:nx2,ny2=-nx2,-ny2
  vx,vy=cc[0]-bb[0],cc[1]-bb[1];n=math.hypot(vx,vy);nx3,ny3=-vy/n,vx/n
  if nx3*nx2+ny3*ny2<0:nx3,ny3=-nx3,-ny3
  # Miter the bend to keep the inner edge continuous without a crossing spike.
  mxn,myn=nx2+nx3,ny2+ny3;norm=math.hypot(mxn,myn);mxn,myn=mxn/norm,myn/norm
  offset=10.5*sc/max(.55,mxn*nx2+myn*ny2)
  start=(mix(aa[0],bb[0],.23)+nx2*10.5*sc,mix(aa[1],bb[1],.23)+ny2*10.5*sc)
  corner=(bb[0]+mxn*offset,bb[1]+myn*offset)
  end=(mix(bb[0],cc[0],.83)+nx3*10.5*sc,mix(bb[1],cc[1],.83)+ny3*10.5*sc)
  strength=1-ease((yaw-.20)/.65) if side=='R' else 1
  contour=tuple(round(mix(WHITE[k],INK[k],strength)) for k in range(3))
  d.line([start,corner,end],fill=contour,width=max(1,round(2.2*sc)),joint='curve')
 hand('R')
 shoe('R');shoe('L');hand('L')
 # Head is an invariant silhouette. Facial features turn continuously on it.
 x,y=q['head'];r=c['head_radius']*sc;d.ellipse((x-r,y-r,x+r,y+r),fill=WHITE,outline=INK,width=round(3*sc))
 # Lower-rim shaded crescent, clipped inside head.
 d.arc((x-r+3*sc,y-r+3*sc,x+r-3*sc,y+r-3*sc),15,165,fill=SHADE,width=round(11*sc))
 hy=p['head_yaw'];shift=math.sin(hy)*r*.40;sep=r*.31*math.cos(hy*.72);ey=y-r*.09;opening=max(.08,1-p['blink']);sur=p['surprise'];sm=p['smile']
 for s in [-1,1]:
  ex=x+shift+s*sep;visibility=1 if s==1 else 1;rx=r*.078*(.75+.25*math.cos(hy));ry=r*.13*opening*(1+.17*sur)*visibility
  if opening<.2:d.line((ex-rx,ey,ex+rx,ey),fill=INK,width=round(2.5*sc))
  else:
   d.ellipse((ex-rx,ey-ry,ex+rx,ey+ry),fill=INK);d.ellipse((ex-rx*.3,ey-ry*.7,ex+rx*.1,ey-ry*.3),fill=WHITE)
  brow=ey-r*.29-sur*r*.10;bp=bez((ex-r*.13,brow+3*sc),(ex,brow-6*sc),(ex+r*.13,brow+2*sc));d.line(bp,fill=INK,width=round(2.3*sc))
 mx=x+shift;my=y+r*.32
 # One deforming mouth curve, from open surprise to the smile.
 mouthw=r*mix(.25,.065,sur);bend=r*(.12+.1*sm)*(1-sur);opening=r*.14*sur
 top=bez((mx-mouthw,my),(mx,my+bend-opening),(mx+mouthw,my-1*sc))
 bottom=bez((mx-mouthw,my),(mx,my+bend+opening),(mx+mouthw,my-1*sc))
 if sur>.03:d.polygon(top+bottom[::-1],fill=INK)
 d.line(bottom,fill=INK,width=round(2.3*sc))
 return p

def frame(t,both=False):
 im=Image.new('RGB',(W*S,H*S),(250,249,246));d=ImageDraw.Draw(im)
 # Uncluttered stage: ground contact stays visible. No graphics disguise a gait fault.
 d.line((80*S,602*S,1200*S,602*S),fill=(212,211,207),width=2*S)
 if both:
  for c,x in zip(C,[330,950]):
   # Center each walking path independently so neither retarget is cropped.
   root=sample(c,t)['joints']['root'][0]
   actor(im,c,t,(x-root*.74,602),.74)
 else:actor(im,C[0],t,(650,602),.92)
 return im.resize((W,H),Image.Resampling.LANCZOS)
if __name__=='__main__':
 import sys
 for i,t in enumerate([0,.12,.24,.36,.48,.60,.72,.84,3.40,3.8,4.3,4.8,5.4,6.3,8.6]):frame(t).save(P/f'qa-{i:02d}.png')
 sheet=Image.new('RGB',(1280,720*3));
 for i,t in enumerate([.12,.36,.72,3.8,4.8,6.3]):sheet.paste(frame(t).resize((640,360)),((i%2)*640,(i//2)*360))
 sheet=sheet.crop((0,0,1280,1080));sheet.save(P/'contact.jpg')
 if '--video' in sys.argv:
  out=P/'movement-v4-local.mp4';pr=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
  for i in range(270):pr.stdin.write(frame(i/30).tobytes())
  pr.stdin.close();assert pr.wait()==0
