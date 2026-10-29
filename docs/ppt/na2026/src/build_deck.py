"""Build Volcano's template-independent presentation.
SVG is the editable diagram source; PNGs freeze diagram geometry in PowerPoint.
Dependencies: python-pptx, cairosvg, Pillow. Fonts: Liberation Sans / Mono.
"""
from pathlib import Path
from html import escape
from copy import deepcopy
import base64,json,re,sys
from lxml import etree
import cairosvg
from PIL import ImageFont
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

ROOT=Path(__file__).resolve().parents[1]; PPT=ROOT.parent; REPO=PPT.parents[1]
ASSETS=ROOT/'assets'; SVG=ROOT/'svg'; PNG=ROOT/'png'
REUSE_SVG='--reuse-svg' in sys.argv
for d in [ASSETS,SVG,PNG]:d.mkdir(exist_ok=True)
C={'ink':'#202d3c','muted':'#647282','line':'#8ea8cb','light':'#d4deea','pale':'#f5f8fc','blue':'#356696','prefill':'#e9f1fb','decode':'#edf1f5','green':'#3d705d','mint':'#edf5f0','purple':'#765399','lav':'#f3eef8','orange':'#e94c25','amber':'#8b621c','sand':'#fff5e2','white':'#ffffff'}
FONT='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
BOLD='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
MONO='/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf'
def col(c):return C.get(c,c)
def wrap(text,width,size,bold=False):
 f=ImageFont.truetype(BOLD if bold else FONT,size*2)
 result=[]
 for para in text.split('\n'):
  line=''
  for word in para.split():
   new=(line+' '+word).strip()
   if line and f.getlength(new)>width*2:result.append(line);line=word
   else:line=new
  result.append(line)
 return result

class Art:
 def __init__(self,name,w=1480,h=560):self.name=name;self.w=w;self.h=h;self.bg=[];self.edges=[];self.front=[];self.nodes={};self.textboxes=[]
 def rect(self,x,y,w,h,fill='white',stroke='light',rx=8,layer='front',dash=False):
  el=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{col(fill)}" stroke="{col(stroke) if stroke else "none"}" stroke-width="1.6"'+(' stroke-dasharray="7 5"' if dash else '')+'/>'
  getattr(self,layer).append(el)
 def text(self,x,y,text,size=30,c='ink',bold=False,width=1400,anchor='start',mono=False):
  lines=wrap(text,width,size,bold);lh=size*1.28
  # Explicit line positions make SVG/PNG layout deterministic.
  self.front.append(f'<text x="{x}" y="{y}" font-family="{ "Liberation Mono" if mono else "Liberation Sans"}, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col(c)}" text-anchor="{anchor}">'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else lh}">{escape(t)}</tspan>' for i,t in enumerate(lines))+'</text>')
  self.textboxes.append((x,y,width,len(lines)*lh,text));return len(lines)*lh
 def panel(self,x,y,w,h,title=None,fill='pale',stroke='light'):
  self.rect(x,y,w,h,fill,stroke,layer='bg')
  if title:self.text(x+22,y+36,title,23,'muted',True,width=w-44)
 def box(self,id,x,y,w,h,text,fill='white',size=27,bold=False,c='ink',stroke='line'):
  self.rect(x,y,w,h,fill,stroke);self.nodes[id]=(x,y,w,h)
  lines=wrap(text,w-30,size,bold);start=y+h/2-(len(lines)-1)*size*.64+size*.33
  self.text(x+w/2,start,'\n'.join(lines),size,c,bold,w-30,'middle');return id
 def anchor(self,id,side):
  x,y,w,h=self.nodes[id];return {'top':(x+w/2,y),'bottom':(x+w/2,y+h),'left':(x,y+h/2),'right':(x+w,y+h/2)}[side]
 def path(self,points,arrow=True,c='line',dash=False):
  d='M'+' L'.join(f'{x},{y}' for x,y in points)
  self.edges.append(f'<path d="{d}" fill="none" stroke="{col(c)}" stroke-width="2.2" stroke-linejoin="round"'+(' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="7 5"' if dash else '')+'/>')
 def connect(self,a,aside,b,bside,via=None,arrow=True,dash=False):
  p=self.anchor(a,aside);q=self.anchor(b,bside)
  # Leave a small gap at the target border; arrow tip points at the target.
  ox,oy={'top':(0,-4),'bottom':(0,4),'left':(-4,0),'right':(4,0)}[bside];end=(q[0]+ox,q[1]+oy)
  if via is None:
   if p[0]==q[0] or p[1]==q[1]:points=[p,end]
   elif aside in ['top','bottom']:
    mid=(p[1]+q[1])/2;points=[p,(p[0],mid),(q[0],mid),end]
   else:
    mid=(p[0]+q[0])/2;points=[p,(mid,p[1]),(mid,q[1]),end]
  else:points=[p]+via+[end]
  self.path(points,arrow,dash=dash)
 def badge(self,x,y,text,fill='mint',c='green',w=210):
  self.rect(x,y,w,35,fill,None,4);self.text(x+12,y+24,text,18,c,True,width=w-24)
 def image(self,x,y,w,h,path,opacity=1):
  p=Path(path);mime='image/svg+xml' if p.suffix=='.svg' else 'image/png';uri='data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
  self.front.append(f'<g opacity="{opacity}"><image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="{uri}"/></g>')
 def save(self):
  content=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><title>{escape(self.name)}</title><defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="{C["line"]}"/></marker></defs>'+''.join(self.bg+self.edges+self.front)+'</svg>'
  p=SVG/(self.name+'.svg')
  if REUSE_SVG and p.exists():content=p.read_text()
  else:p.write_text(content)
  cairosvg.svg2png(bytestring=content.encode(),write_to=str(PNG/(self.name+'.png')),output_width=self.w*2,output_height=self.h*2)
  return PNG/(self.name+'.png')

def replica(a,id,x,y,label,role='prefill',w=280):
 a.panel(x,y,w,132,fill='white',stroke='line');a.text(x+16,y+30,label,22,'ink',True,width=w-32)
 a.box(id+'-p0',x+16,y+58,(w-48)/2,50,'Pod 0',role,21);a.box(id+'-p1',x+32+(w-48)/2,y+58,(w-48)/2,50,'Pod 1',role,21)

def node(a,id,x,y,label,fill='white',w=110):a.box(id,x,y,w,48,label,fill,22)

# Brand assets: preserve original geometry; only opacity changes for watermark.
r=etree.parse(str(REPO/'docs/images/volcano-logo-svg.svg')).getroot();ns={'s':'http://www.w3.org/2000/svg'}
for e in r.xpath('.//s:foreignObject',namespaces=ns):e.getparent().remove(e)
r.set('width','1197');r.set('height','200');(ASSETS/'volcano-logo.svg').write_text('\n'.join(line.rstrip() for line in etree.tostring(r).decode().splitlines())+'\n')
cairosvg.svg2png(bytestring=etree.tostring(r),write_to=str(ASSETS/'volcano-logo.png'),output_width=1200)
# The official icon is the colored path from the horizontal logo.
icon=etree.Element('{http://www.w3.org/2000/svg}svg',nsmap={None:'http://www.w3.org/2000/svg'});icon.set('viewBox','0 0 82 40')
for e in r.xpath('.//s:linearGradient',namespaces=ns):icon.append(deepcopy(e))
for e in r.xpath('.//s:path[@class="st0"]',namespaces=ns):
 e=deepcopy(e);e.set('fill','url(#SVGID_1_)');icon.append(e)
(ASSETS/'volcano-icon.svg').write_text('\n'.join(line.rstrip() for line in etree.tostring(icon).decode().splitlines())+'\n')
for name,large in [('background',False),('cover-background',True)]:
 b=Art(name,1600,900);b.rect(0,0,1600,900,'white',None,0,'bg')
 if large:b.image(1000,225,560,340,ASSETS/'volcano-icon.svg',.085)
 else:b.image(1170,660,365,178,ASSETS/'volcano-icon.svg',.035)
 b.save()

arts={}
def art(n,name):a=Art(f'{n:02d}-{name}');arts[n]=a;return a

# 02 — work mix, not a universal per-agent Pod path.
a=art(2,'workloads');a.panel(0,0,410,460,fill='white')
a.text(28,55,'Different demands',32,bold=True,width=350)
for y,h,t in [(125,'Training & RL','Coordinated, resource-intensive compute'),(245,'Inference','Long-running services with distinct roles'),(365,'Agent applications','Bursty requests and latency-sensitive interactions')]:
 a.text(28,y,h,28,bold=True,width=350);a.text(28,y+42,t,25,'muted',width=345)
a.box('agent',1000,20,390,76,'Agent applications','prefill',30)
a.box('train',500,188,380,94,'Training / RL workloads','white',28)
a.box('infer',1000,188,390,94,'Inference services','white',30)
a.connect('agent','bottom','infer','top')
a.box('infra',500,375,890,85,'Shared Kubernetes infrastructure','pale',31,True)
a.connect('train','bottom','infra','top',[(690,330),(945,330)])
a.connect('infer','bottom','infra','top',[(1195,330),(945,330)])
a.text(500,522,'Different scheduling requirements, one shared cluster.',28,'blue',True,width=920)

# 03 — clear separation between local worker coordination and NodeShard.
a=art(3,'unified-framework')
a.panel(0,0,580,360,'GROUP-ORIENTED PATH');a.panel(620,0,610,360,'POD-ORIENTED PATH')
a.box('vc',30,75,520,82,'Volcano Scheduler','white',32,True)
a.box('session',30,212,238,80,'Session / actions','white',24);a.box('plugins',312,212,238,80,'Scheduling plugins','white',24)
a.connect('vc','bottom','session','top',[(290,182),(149,182)]);a.connect('vc','bottom','plugins','top',[(290,182),(431,182)])
a.box('as',650,75,550,82,'Agent Scheduler','white',32,True)
a.box('workers',650,212,242,80,'Parallel workers','white',25);a.box('binder',958,212,242,80,'Binder','white',27)
a.connect('as','bottom','workers','top',[(925,183),(771,183)]);a.connect('workers','right','binder','left')
a.text(1260,98,'Distinct paths',26,'blue',True,width=215);a.text(1260,157,'Workload-specific scheduling behavior',24,'muted',width=205)
a.text(1260,277,'Local conflict handling',24,'muted',width=205)
a.box('coord',250,420,730,85,'NodeShard + scheduler coordinators','white',31,True)
a.connect('session','bottom','coord','top',[(149,390),(615,390)])
a.connect('workers','bottom','coord','top',[(771,390),(615,390)])
a.text(250,550,'Coordinate candidate-node access across scheduling paths.',28,'blue',width=1100)

# 04 — one illustrated handoff, anchored arrows between three explicit stages.
a=art(4,'nodeshard-handoff')
for x,num,title in [(0,'01','Current use'),(505,'02','Desired change'),(1010,'03','Next eligible cycle')]:
 a.panel(x,0,470,395,fill='pale');a.text(x+24,44,num,24,'blue',True);a.text(x+24,94,title,30,bold=True,width=425)
 a.text(x+24,130,{'01':'In-use membership','02':'Controller updates desired nodes','03':'Coordinators confirm handoff'}[num],19,'muted',width=425)
 a.text(x+24,164,'Scheduler A',24,'muted');a.text(x+24,286,'Scheduler B',24,'muted')
for j,x in enumerate([0,505,1010]):
 node(a,f'a{j}',x+24,187,'N1');node(a,f'b{j}',x+24,307,'N3')
 if j==0:node(a,'n-current',x+154,187,'N2','prefill')
 if j==1:
  node(a,'n-desired',x+154,187,'N2','sand');a.text(x+156,258,'release pending',20,'amber',width=280)
  a.text(x+156,340,'B requests N2',22,'muted',width=280)
 if j==2:node(a,'n-next',x+154,307,'N2','prefill')
a.path([(472,210),(500,210)]);a.path([(977,210),(1005,210)])
a.text(24,455,'NodeShard changes coordinate future placement.',31,'blue',True,width=1400)
a.text(24,506,'none: no sharding     soft: prefer shard nodes     hard: restrict candidate nodes',26,'muted',width=1430)

# 05 — illustrate resource count vs replica identity without a fake measurement.
a=art(5,'complete-groups')
a.text(0,48,'Four Pods can still be the wrong four Pods.',37,bold=True,width=1440)
a.panel(0,105,705,305,'TOTAL COUNT ONLY',fill='pale');a.panel(755,105,725,305,'COMPLETE REPLICAS',fill='pale')
for x,lab,fill in [(30,'R0 / Pod 0','prefill'),(355,'R0 / Pod 1','prefill'),(30,'R2 / Pod 0','prefill'),(355,'R1 / Pod 0','decode')]:
 idx=[(30,'R0 / Pod 0'),(355,'R0 / Pod 1'),(30,'R2 / Pod 0'),(355,'R1 / Pod 0')].index((x,lab));a.box(lab,x,190+(idx//2)*93,300,61,lab,fill,25)
replica(a,'r0',785,195,'Replica 0','prefill',310);replica(a,'r1',1135,195,'Replica 1','decode',310)
a.text(28,453,'One required replica is incomplete.',28,'muted',width=680)
a.text(783,453,'Two complete two-Pod replicas.',28,'blue',True,width=670)
a.text(0,535,'Next: preserve group structure, then choose the right topology.',29,'blue',True,width=1470)

# 06 — policies are not actual subgroups.
a=art(6,'podgroup-subgroup');a.panel(0,0,440,490,'KTHENA WORKLOAD MODEL',fill='white')
a.box('model',28,80,384,75,'ModelServing','pale',29);a.box('sg',28,214,384,75,'ServingGroup','pale',29);a.connect('model','bottom','sg','top')
a.text(28,359,'Role + replica identity',28,bold=True,width=380);a.text(28,405,'Preserve complete Prefill and Decode replicas.',25,'muted',width=370)
a.panel(500,0,980,490,'PODGROUP · OVERALL GANG REQUIREMENTS',fill='pale')
a.box('pol',530,72,920,62,'SubGroup policies: select roles and partition replicas','white',26)
a.panel(530,175,440,275,'PREFILL',fill='white');a.panel(1010,175,440,275,'DECODE',fill='white')
replica(a,'p0',550,255,'Replica P0 → SubGroup','prefill',400);replica(a,'d0',1030,255,'Replica D0 → SubGroup','decode',400)
a.connect('sg','right','pol','left',[(468,251),(468,103)])
a.text(500,542,'One policy can generate multiple actual SubGroups.',29,'blue',True,width=960)

# 07 — topology hierarchy.
a=art(7,'hypernode-hierarchy');a.panel(0,0,440,490,fill='white')
a.text(28,55,'A hierarchy of domains',31,bold=True,width=380)
a.text(28,135,'HyperNode models network topology across nodes.',28,'muted',width=380)
a.text(28,272,'Hard constraint',28,'blue',True,width=380);a.text(28,315,'Require a valid topology domain.',25,'muted',width=370)
a.text(28,400,'Soft constraint',28,'blue',True,width=380);a.text(28,443,'Prefer locality when feasible.',25,'muted',width=370)
a.box('super',830,20,340,75,'Supernode','prefill',31,True)
for x,l in [(560,'A'),(1110,'B')]:
 a.box('rack'+l,x,205,300,70,'Rack '+l,'white',28);a.connect('super','bottom','rack'+l,'top')
 for i,nx in enumerate([x-15,x+165]):
  a.box('node'+l+str(i),nx,405,150,65,'Node '+str(i+1),'white',25);a.connect('rack'+l,'bottom','node'+l+str(i),'top')
a.text(525,540,'A topology domain describes locality, not scheduler ownership.',26,'blue',width=945)

# 08 — persistent domain layout shared with slide 9.
a=art(8,'multilevel-topology')
a.panel(0,0,440,490,fill='white');a.text(28,58,'Two placement levels',32,bold=True,width=380)
a.text(28,154,'PodGroup',30,'blue',True,width=380);a.text(28,201,'Keep one serving instance inside a larger domain.',27,'muted',width=370)
a.text(28,341,'SubGroup',30,'blue',True,width=380);a.text(28,388,'Keep each complete replica inside a smaller domain.',27,'muted',width=370)
a.panel(505,0,975,490,'SUPERNODE A · PODGROUP SCOPE',fill='pale')
for x,r,role,fill in [(535,'Rack A1','Prefill P0','prefill'),(1015,'Rack A2','Decode D0','decode')]:
 a.panel(x,110,435,320,r,fill='white',stroke='line');replica(a,r,x+20,222,role+' / SubGroup',fill,395)
a.text(505,542,'Capacity must fit within the selected topology domains.',28,'blue',True,width=975)

# 09 — concrete present capability + small pending/preferred caption.
a=art(9,'podgroup-anti-affinity');a.badge(0,0,'AVAILABLE IN v1.16',w=220)
for x,domain,pg in [(0,'Supernode A','Instance A / PodGroup A'),(790,'Supernode B','Instance B / PodGroup B')]:
 a.panel(x,70,690,325,domain,fill='pale',stroke='line');a.panel(x+24,140,642,222,pg,fill='white')
 a.box(pg+'p',x+45,230,265,80,'Prefill replicas','prefill',26);a.box(pg+'d',x+380,230,265,80,'Decode replicas','decode',26)
a.text(0,450,'Within each instance: network topology',28,'blue',True,width=720)
a.text(790,450,'Between instances: anti-affinity',28,'blue',True,width=690)
a.text(0,525,'Required: wait if no legal domain exists.     Preferred: allow a feasible fallback.',27,'muted',width=1460)

# 10 — logos reused from the official architecture source; factual matrix.
a=art(10,'ecosystem-matrix');xs=[0,315,880];ws=[315,565,600]
for x,w,t in zip(xs,ws,['ECOSYSTEM','AVAILABLE / MERGED','EXPANDING']):a.rect(x,0,w,57,'pale',None,0);a.text(x+18,38,t,22,'muted',True,width=w-36)
rows=[('Kthena','kthena.svg','Role / replica gang + topology','Reference scenarios for group relations'),('KubeRay','kuberay.png','SubGroup support merged','Replica topology PR in progress'),('Grove','dynamo-grove.svg','Gang / SubGroup backend merged','Topology mapping remains open'),('Kubeflow Trainer','kubeflow-trainer.svg','Existing Volcano integration','Finer TrainJob groups + topology'),('LeaderWorkerSet','leaderworkerset.svg','Existing gang / Volcano integration','Explore roles, slices, and group relations')]
for i,(name,logo,left,right) in enumerate(rows):
 y=65+i*84;a.rect(0,y,1480,82,'white' if i%2 else 'pale',None,0)
 a.image(17,y+18,64,45,ASSETS/logo);a.text(98,y+48,name,24,bold=True,width=205)
 a.text(333,y+48,left,25,width=535);a.text(898,y+48,right,25,'muted',width=555)
a.text(0,544,'Integration depth differs: gang support does not automatically include topology.',26,'blue',width=1460)

# 11 — map Ray logical replicas exactly.
a=art(11,'kuberay-replicas');a.panel(0,0,440,490,fill='white')
a.text(28,55,'One worker group',31,bold=True,width=380)
a.text(28,145,'minReplicas: 2\nnumOfHosts: 2',28,'blue',True,width=380,mono=True)
a.text(28,300,'Two complete replicas, each spanning two Pods.',30,bold=True,width=380)
a.text(28,426,'Head group omitted here.',24,'muted',width=380)
a.panel(500,0,980,350,'SUBGROUP POLICY PRESERVES LOGICAL REPLICA IDENTITY',fill='pale')
replica(a,'ray0',530,145,'Replica 0 → SubGroup','prefill',440);replica(a,'ray1',1010,145,'Replica 1 → SubGroup','decode',440)
a.badge(530,404,'GANG: MERGED',w=250);a.badge(1010,404,'TOPOLOGY: IN PROGRESS','sand','amber',350)
a.text(500,536,'A WorkerGroup can produce multiple actual SubGroups.',29,'blue',True,width=980)

# 12 — status-specific future; explicit inside same PG.
a=art(12,'ecosystem-next')
a.panel(0,0,450,485,'AVAILABLE',fill='pale');a.text(26,125,'Standalone HyperNode',31,bold=True,width=395);a.text(26,198,'Discovery + controller\nReusable topology API',27,'muted',width=395);a.text(26,375,'Scheduler adapters are separate integration work.',25,'muted',width=395)
a.panel(490,0,450,485,'EXPANDING',fill='pale');a.text(516,125,'Controller mappings',31,bold=True,width=395);a.text(516,198,'KubeRay / Grove\nKubeflow / LWS',28,'muted',width=395);a.text(516,375,'Carry role, replica, and topology intent through.',25,'muted',width=395)
a.panel(980,0,500,485,'PROPOSED',fill='lav');a.text(1006,125,'SubGroup relationships',31,bold=True,width=445);a.text(1006,198,'Affinity / anti-affinity\nWithin one PodGroup',27,'muted',width=445)
a.box('near1',1006,315,192,60,'SubGroup A','white',22);a.box('near2',1258,315,192,60,'SubGroup B','white',22)
a.text(1006,438,'Express “near” or “apart”.',26,'purple',True,width=445)
a.text(0,546,'More workload shapes call for repeatable performance evaluation.',29,'blue',True,width=1470)

# 13 — pipeline and orthogonal feeds.
a=art(13,'benchmark-framework')
a.panel(0,0,1480,135,'ENVIRONMENT',fill='pale')
a.box('kind',25,55,570,58,'Kind + KWOK','white',28);a.box('real',885,55,570,58,'Existing Kubernetes cluster','white',28)
a.box('prof',0,215,405,120,'Gang / Pod profiles\nOptional topology','white',29)
a.box('sched',535,215,405,120,'Volcano schedulers\nPinned configuration','white',29)
a.box('collect',1075,215,405,120,'Audit + metrics\nObservation pipeline','white',29)
a.connect('prof','right','sched','left');a.connect('sched','right','collect','left')
a.connect('kind','bottom','sched','top',[(310,172),(737,172)]);a.connect('real','bottom','sched','top',[(1170,172),(737,172)])
a.box('reports',1075,420,405,80,'Dashboards + reports','pale',28);a.connect('collect','bottom','reports','top')
a.text(0,451,'Configure → run → observe → compare',33,'blue',True,width=1000)
a.text(0,519,'KWOK measures scheduling behavior, not GPU or network execution.',27,'muted',width=1030)

# 14 — actual collection coverage, no fabricated outcomes.
a=art(14,'benchmark-progress')
a.panel(0,0,710,490,'FRAMEWORK IN PLACE',fill='pale');a.panel(770,0,710,490,'ONGOING VALIDATION',fill='pale')
for x,items in [(28,[('Workload profiles','Gang jobs, bare Pods, and topology configurations'),('Observability','Audit-based latency, scheduler metrics, and dashboards'),('Automation','Setup scripts, test execution, and report collection')]),(798,[('Workload scale and shape','Vary job size, Pod count, and placement constraints'),('Optimization comparisons','Keep configuration and measurement windows comparable'),('Repeatability','Re-run observations and check where bottlenecks move')])]:
 for i,(h,b) in enumerate(items):
  y=116+i*133;a.text(x,y,h,30,bold=True,width=652);a.text(x,y+47,b,26,'muted',width=650)
a.text(0,545,'Testing and optimization continue across workload scenarios.',29,'blue',True,width=1470)

# 15 — measured event boundaries instead of the unselected results placeholder.
a=art(15,'benchmark-measurement')
a.text(0,48,'Measure the scheduling path before attributing the result.',34,bold=True,width=1470)
a.box('created',0,130,350,90,'Pod created','white',31,True);a.box('scheduled',560,130,350,90,'Pod scheduled','white',31,True);a.box('ready',1120,130,350,90,'Application ready','pale',29)
a.connect('created','right','scheduled','left');a.connect('scheduled','right','ready','left',dash=True)
a.text(382,113,'audit observation',22,'muted',width=250);a.text(940,113,'runtime / application',22,'muted',width=280)
a.panel(0,285,705,200,'CURRENT MEASUREMENT',fill='pale');a.text(25,370,'Created → scheduled latency',30,bold=True,width=650);a.text(25,426,'Scheduling throughput and stage metrics',25,'muted',width=655)
a.panel(765,285,715,200,'COMPARISON CONTEXT',fill='pale');a.text(790,370,'Version · resources · workload · rules',28,bold=True,width=655);a.text(790,426,'Repeat runs; retain raw observations.',26,'muted',width=655)
a.text(0,546,'Current focus: reproducible comparisons and continued testing.',29,'blue',True,width=1470)

# 16 — four outcomes, no marketing filler.
a=art(16,'takeaways')
for y,num,head,sub in [(0,'01','Unified scheduling','Different paths coordinate access to shared infrastructure.'),(132,'02','Workload-aware placement','Complete groups, network locality, and instance separation.'),(264,'03','Ecosystem integration','Controllers bring role and replica identity into scheduling.'),(396,'04','Benchmark and improve','Repeatable measurements guide ongoing validation.')]:
 a.text(0,y+42,num,32,'blue',True);a.text(105,y+42,head,33,bold=True,width=1340);a.text(105,y+95,sub,28,'muted',width=1330)

# 17 — maintainers' invitation.
a=art(17,'questions');a.text(0,65,'What does your workload need to keep together—or place apart?',37,bold=True,width=1390)
a.text(0,215,'Bring us your workload shapes, topology constraints,\nand reproducible scheduling observations.',32,'muted',width=1260)
a.text(0,400,'github.com/volcano-sh/volcano',35,'blue',True,width=1300)
a.text(0,470,'Roadmap and feedback: issue #6166',27,'muted',width=1100)

for a in arts.values():a.save()

# Native PPT text for titles, summaries and speaker names; PNG for each complete diagram.
prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(7.5)
def ptext(sl,x,y,w,h,text,size=26,bold=False,c='ink',align=None):
 sh=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.clear();tf.word_wrap=True
 tf.margin_left=tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
 for i,line in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Liberation Sans';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(col(c).lstrip('#'));p.space_after=Pt(5)
  if align:p.alignment=align
 return sh
chapter=['01  UNIFIED SCHEDULING']*5+['02  MULTI-LEVEL GANG & NETWORK TOPOLOGY']*4+['03  ECOSYSTEM']*3+['04  BENCHMARK FRAMEWORK & PROGRESS']*4+['DISCUSSION']
titles={1:'Volcano for the Agentic AI Era:',2:'Different Workloads, Shared Infrastructure',3:'A Coordinated Scheduling Framework',4:'NodeShard: Coordinating Node Access',5:'Available Nodes Are Only the Beginning',6:'PodGroup and SubGroup: Complete Replicas',7:'HyperNode: Expressing Topology Domains',8:'Place Groups at Different Topology Levels',9:'Keep Each Instance Together, Place Instances Apart',10:'Controllers Bring Workload Structure to Scheduling',11:'KubeRay: A Replica Can Span Multiple Pods',12:'Extending the Ecosystem and Placement Model',13:'A Repeatable Scheduling Benchmark Framework',14:'Benchmark Progress and Ongoing Validation',15:'From Measurements to Reliable Comparisons',16:'Framework, Workloads, Ecosystem, Evidence',17:'Questions & Discussion'}
subtitles={2:'The infrastructure must support different arrival patterns and coordination needs.',3:'Separate workload paths, coordinated node access, and local worker conflict handling.',4:'A shard change affects future placement; running Pods do not move with the shard.',5:'Replica identity and topology matter alongside resource quantity.',6:'Use role and replica identity to describe what must be scheduled together.',7:'Topology boundaries express where a group can—or should—fit.',8:'Keep the service instance local while preserving each complete replica.',9:'Combine group-local topology with PodGroup anti-affinity.',10:'Adoption and integration depth are different questions.',11:'Two complete two-Pod replicas are more specific than a count of four.',12:'Reuse topology components and extend the workload semantics carried by controllers.',13:'A common workflow for scenario setup, execution, observation, and comparison.',14:'The framework is available; scenario coverage and performance validation continue.',15:'Keep scheduling metrics distinct from end-to-end application readiness.',16:'Coordinate placement, carry workload intent, and validate behavior.',17:'Help shape the next set of scheduling and integration scenarios.'}
# Carry detailed source references and Chinese notes forward from the researched draft.
draft=Presentation(str(PPT/'Volcano_KubeCon_NA_2026_draft.pptx'))
for n in range(1,18):
 sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.shapes.add_picture(str(PNG/('cover-background.png' if n==1 else 'background.png')),0,0,width=prs.slide_width,height=prs.slide_height)
 sl.shapes.add_picture(str(ASSETS/'volcano-logo.png'),Inches(10.85),Inches(.32),width=Inches(1.9))
 ptext(sl,.50,.32,10,.28,'MAINTAINER TRACK' if n==1 else chapter[n-1],11,True,'blue')
 if n==1:
  ptext(sl,.62,1.35,11.55,1.52,'Volcano for the\nAgentic AI Era:',43,True)
  ptext(sl,.66,3.10,10.80,1.30,'Unified Scheduling Across Training,\nInference, and Agents',31,False,'blue')
  ptext(sl,.68,5.02,11.6,.45,'Kevin Wang  ·  Ricardo Aravena  ·  Chen Zicong',23,True)
  ptext(sl,.68,5.69,11.8,.65,'KubeCon + CloudNativeCon North America 2026\nSalt Lake City · November 9–12',18,False,'muted')
 else:
  ptext(sl,.50,.88,12.30,.70,titles[n],31 if len(titles[n])<52 else 28.5,True)
  ptext(sl,.52,1.57,12.25,.47,subtitles[n],17,False,'muted')
  sl.shapes.add_picture(str(PNG/(arts[n].name+'.png')),Inches(.50),Inches(2.12),width=Inches(12.333333),height=Inches(4.666667))
 ptext(sl,.52,7.13,11.5,.22,'Volcano  |  KubeCon + CloudNativeCon North America 2026',9,False,'muted')
 ptext(sl,12.05,7.09,.75,.28,f'{n:02d} / 17',11,False,'muted',PP_ALIGN.RIGHT)
 old=draft.slides[n-1].notes_slide.notes_text_frame.text
 old=old.replace('讲者备注 / Draft notes','讲者备注').replace('1:30。等待讲者选定当前测试成果。','1:30。正式视觉版此页先讲测量口径，不展示待选的性能结果。')
 if n==1:old+='\n讲者姓名采用官方议程顺序；暂不填写未确认的单位。'
 if n==4:old+='\n图示是候选节点使用范围的交接，不表示 Pod 迁移。desired change 阶段 N2 仍在 A 的当前周期中使用；实际交接依赖 coordinator 状态同步。'
 if n==15:old+='\n本页明确以测量方法代替结果占位。收到选定结果后再用一张图替换；目前没有对外宣称速度提升。'
 old+='\n\nVisual source: na2026/svg/'+(arts[n].name+'.svg' if n>1 else 'cover-background.svg')+'\nDiagram geometry is frozen in PNG; edit SVG and re-export to refine.'
 sl.notes_slide.notes_text_frame.text=old
prs.core_properties.title='Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents'
prs.core_properties.subject='KubeCon + CloudNativeCon North America 2026 — template-independent presentation'
prs.core_properties.author='Volcano maintainers';prs.core_properties.comments='2026-10-29. Native titles; editable SVG diagram sources rendered to PNG. Benchmark results not yet selected.'
out=PPT/'Volcano_KubeCon_NA_2026.pptx';prs.save(out)
manifest={'deck':out.name,'slides':[{ 'page':n,'title':titles[n],'chapter':chapter[n-1],'svg':f'svg/{arts[n].name}.svg' if n>1 else 'svg/cover-background.svg','png':f'png/{arts[n].name}.png' if n>1 else 'png/cover-background.png'} for n in range(1,18)],'style_reference':'docs/images/volcano-new-architecture.svg','benchmark':'Framework and ongoing validation; no invented results.'}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(out);print('17 slides; 16 diagram SVG/PNG pairs; brand backgrounds generated.')
