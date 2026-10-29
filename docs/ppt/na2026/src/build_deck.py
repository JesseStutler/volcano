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
  p=Path(path);mime='image/svg+xml' if p.suffix=='.svg' else ('image/jpeg' if p.suffix in ['.jpg','.jpeg'] else 'image/png');uri='data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
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
logo_source=REPO/'docs/images/volcano-logo-svg.svg'
if not logo_source.exists():logo_source=ASSETS/'volcano-logo.svg'
r=etree.parse(str(logo_source)).getroot();ns={'s':'http://www.w3.org/2000/svg'}
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

# Technical diagrams: retain original EU / China figures where they carry the
# explanation, then add readable API excerpts as separate SVG text.
arts={};titles={};subtitles={};sources={};oldnotes={};chapters={};examples={}
REUSED=ASSETS/'reused'
def art(n,name,title,sub='',chapter=0,old=None,source=''):
 a=Art(f'{n:02d}-{name}');arts[n]=a;titles[n]=title;subtitles[n]=sub;chapters[n]=chapter;sources[n]=source
 if old:oldnotes[n]=old
 return a

def rule(a,x,y,w):a.path([(x,y),(x+w,y)],False,c='light')
def rawtext(a,x,y,t,size=26,c='ink',bold=False,mono=False):
 a.front.append(f'<text x="{x}" y="{y}" xml:space="preserve" font-family="{"Liberation Mono" if mono else "Liberation Sans"}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col(c)}">{escape(t)}</text>')

def code(a,x,y,w,h,label,body,size=25,highlights=(),filename=None):
 a.rect(x,y,w,h,'#f5f7fa','#d6dfe9',3)
 a.text(x+20,y+31,label,20,'muted',True,width=w-40);rule(a,x+18,y+45,w-36)
 lh=size*1.19
 for i,line in enumerate(body.strip('\n').splitlines()):
  yy=y+75+i*lh
  if ImageFont.truetype(MONO,size*2).getlength(line)/2>w-36:raise ValueError(f'Code line too wide: {a.name}: {line}')
  if yy>y+h-7:raise ValueError(f'Code overflows {a.name}: {label}')
  if any(k in line for k in highlights):a.rect(x+4,yy-size+2,w-8,lh,'#e4edf8',None,0)
  rawtext(a,x+20,yy,line,size,'blue' if ':' in line and not line.lstrip().startswith('#') else 'muted',False,True)
 if filename:
  examples[filename]=body.strip()+'\n';(ROOT/'examples'/filename).write_text(body.strip()+'\n')

def original(a,file,x,y,w,h,crop=None):
 # SVG viewport crops the source image without resampling or rewriting it.
 p=REUSED/file
 if not crop:a.image(x,y,w,h,p);return
 from PIL import Image
 iw,ih=Image.open(p).size
 cx,cy,cw,ch=crop;uri='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
 a.front.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{cx} {cy} {cw} {ch}" preserveAspectRatio="xMidYMid meet"><image width="{iw}" height="{ih}" href="{uri}"/></svg>')

def note(a,x,y,num,head,body,w=400):
 a.text(x,y,num,23,'blue',True);a.text(x+45,y,head,28,bold=True,width=w-45)
 a.text(x+45,y+43,body,25,'muted',width=w-45)

# Four divider slides are composed with native PowerPoint text below.
dividers={3:(1,'Unified scheduling','Different paths. Shared infrastructure.','How do schedulers coordinate node access?'),7:(2,'Multi-level gang\n& network topology','From available nodes to runnable workloads.','What must run together, and where should it fit?'),12:(3,'Ecosystem','Workload controllers carry scheduling intent.','How do roles and replicas reach the scheduler?'),17:(4,'Benchmark\nframework & progress','Measure behavior across workload shapes.','What can we reproduce, compare, and improve?')}

# 04: a compact workload diagram, with the service path explicit.
a=art(4,'workload-demands','Different Workloads, Shared Infrastructure','Training, inference, and agent applications put different demands on the same cluster.',1,2)
a.text(0,40,'Training & RL',33,bold=True);a.text(0,91,'Coordinated compute',26,'muted')
a.text(0,170,'Inference',33,bold=True);a.text(0,221,'Serving roles and replicas',26,'muted')
a.text(0,300,'Agent applications',33,bold=True);a.text(0,351,'Bursty, latency-sensitive work',26,'muted')
a.box('agent',1000,10,430,70,'Agent applications','white',29,True)
a.box('service',1000,170,430,95,'Inference / sandbox services','prefill',28)
a.connect('agent','bottom','service','top');a.text(1040,130,'requests / runtime calls',22,'muted',width=400)
a.box('training',540,170,370,95,'Training / RL jobs','prefill',29)
a.panel(520,350,930,132,'SHARED KUBERNETES INFRASTRUCTURE',fill='white')
for i,lab in enumerate(['CPU / GPU capacity','Network locality','Placement policy']):a.text(544+i*303,442,lab,24,width=294)
a.path([(725,265),(725,345)]);a.path([(1215,265),(1215,345)])
a.text(0,545,'The scheduling unit depends on the runtime and workload model.',29,'blue',True,width=1470)

# 05: retain the original detailed architecture, not a replacement box summary.
a=art(5,'unified-architecture','A Coordinated Scheduling Framework','Specialized scheduling paths coordinate through NodeShard.',1,3,'China 2026 slide 7; same architecture family as EU 2026.')
original(a,'china-07-unified-architecture.png',0,0,970,550,(0,115,3129,2051))
note(a,1020,65,'01','Workload paths','Batch-oriented scheduling and a Pod-oriented fast path.',445)
note(a,1020,245,'02','Local coordination','Parallel workers use Binder conflict checks.',445)
note(a,1020,425,'03','Shared node access','NodeShard coordinates candidate-node pools.',445)

# 06: original controller plus an actual NodeShard excerpt.
a=art(6,'nodeshard','NodeShard: Desired Nodes and Current Use','Changing a shard coordinates future placement; it does not migrate running Pods.',1,4,'China 2026 slide 9; docs/design/agent-scheduler.md; shard API types.')
original(a,'china-09-dynamic-node-sharding.png',0,0,620,545)
code(a,690,0,790,405,'NodeShard · excerpt','''kind: NodeShard
metadata:
  name: volcano
spec:
  nodesDesired: [node1, node2, node3]
status:
  nodesInUse: [node0, node1, node2]
  nodesToRemove: [node0]
  nodesToAdd: [node3]''',28,('nodesDesired','nodesInUse'),filename='nodeshard.yaml')
a.text(710,458,'Desired membership ≠ immediate use',29,'blue',True,width=740)
a.text(710,505,'Coordinators reconcile the handoff at scheduling boundaries.',26,'muted',width=740)

# 08: the original full workload / topology figure is the main explanation.
a=art(8,'group-structure','PodGroup and SubGroup: Preserve Workload Structure','Gang requirements apply to the workload and to its complete subgroups.',2,6,'China 2026 slide 14. Figure reused unchanged.')
original(a,'china-14-podgroup-subgroup.png',0,0,1480,510)
a.text(0,552,'A SubGroup policy selects Pods; replica identity can split them into multiple SubGroups.',25,'blue',True,width=1470)

# 09: retain the physical fabric from the original, make the API precise and readable.
a=art(9,'hypernode-api','HyperNode: From Physical Fabric to Scheduling Domains','A parent HyperNode groups child HyperNodes; a leaf groups Kubernetes Nodes.',2,7,'China 2026 slide 16 (physical fabric); benchmark/scripts/create-hypernodes.sh.')
a.text(8,30,'PHYSICAL FABRIC',21,'muted',True)
original(a,'china-16-hypernode.png',0,55,445,470,(0,55,465,515))
code(a,500,0,460,510,'Parent · HyperNode.spec','''tier: 2
tierName: spine
members:
- type: HyperNode
  selector:
    exactMatch:
      name: rack-a''',26,('type: HyperNode','name: rack-a'),filename='hypernode-parent-spec.yaml')
code(a,995,0,485,510,'Leaf · HyperNode.spec','''tier: 1
tierName: rack
members:
- type: Node
  selector:
    labelMatch:
      matchLabels:
        rack: rack-a''',26,('type: Node','rack: rack-a'),filename='hypernode-leaf-spec.yaml')
a.text(0,553,'The same hierarchy is available through the standalone HyperNode component.',26,'blue',True,width=1470)

# 10: reuse the actual network drawing, with the two topology levels in YAML.
a=art(10,'multilevel-placement','Place Groups at Different Topology Levels','An eight-Pod instance spans a larger domain; Prefill and Decode use different locality constraints.',2,8,'EU 2026 slide 16 / China 2026 slide 17; PodGroup API. Selector and Decode fragment below are explanatory excerpts.')
original(a,'china-17-multilevel-topology.png',0,25,900,510)
code(a,940,0,540,531,'PodGroup.spec · key fields','''minMember: 8
networkTopology:
  mode: hard
  highestTierAllowed: 3
subGroupPolicy:
- name: prefill
  subGroupSize: 4
  networkTopology:
    mode: hard
    highestTierAllowed: 1
- name: decode
  subGroupSize: 4
  networkTopology:
    mode: hard
    highestTierAllowed: 2''',24,('highestTierAllowed',),filename='multilevel-topology-spec.yaml')
a.text(0,554,'Select each role’s Pods in its policy; selectors are omitted here.',24,'muted',width=910)

# 11: a placement example, not merely a pair of generic capability boxes.
a=art(11,'instance-isolation','Keep Each Instance Together, Place Instances Apart','PodGroup anti-affinity separates service instances across HyperNode domains.',2,9,'docs/user-guide/how_to_use_podgroup_anti_affinity.md; group-topology-affinity plugin, v1.16.')
for y,label,prefix in [(45,'SUPERNODE A','instance-a'),(290,'SUPERNODE B','instance-b')]:
 a.rect(0,y,690,210,'#f7faff','line',3)
 a.text(20,y+32,label,21,'muted',True)
 a.rect(20,y+57,650,130,'white','blue',3,dash=True)
 a.text(38,y+91,prefix+' · PodGroup',25,'blue',True,width=600)
 for j,role in enumerate(['Prefill','Decode']):
  a.rect(40+j*320,y+112,290,56,'mint' if j==0 else 'prefill','light',3)
  a.text(55+j*320,y+148,role+'  [P0] [P1]',23,'green' if j==0 else 'blue',width=275)
a.text(0,24,'AVAILABLE · v1.16',20,'green',True)
code(a,740,0,740,500,'PodGroup · same rule on each instance','''metadata:
  labels: {app: model-a}
spec:
  networkTopology:
    mode: hard
    highestTierName: supernode
  topologyAffinity:
    podGroupAntiAffinity:
      required:
      - podGroupSelector:
          matchLabels: {app: model-a}
        topologyTierName: supernode''',25,('podGroupAntiAffinity','topologyTierName'),filename='podgroup-anti-affinity.yaml')
a.text(0,549,'Required rules wait for a legal domain. Preferred rules allow a feasible fallback.',26,'blue',True,width=1470)

# 13: ecosystem as controller-to-API relationships, not a horizontal status table.
a=art(13,'ecosystem','Controllers Bring Workload Structure to Scheduling','Integration depth differs: group support and topology support are separate steps.',3,10,'Kthena docs; KubeRay #5249 / #5369; Grove #516; Kubeflow Trainer Volcano plugin; LWS #498.')
# Each controller connects to the shared API at a named port; status stays beside its owner.
items=[('kt',0,0,'Kthena','kthena.svg','Role / replica gang + topology'),('ray',0,193,'KubeRay','kuberay.png','SubGroup merged; topology in progress'),('grove',0,386,'Grove','dynamo-grove.svg','SubGroup backend; topology mapping open'),('kf',1030,75,'Kubeflow Trainer','kubeflow-trainer.svg','Existing Volcano plugin'),('lws',1030,335,'LeaderWorkerSet','leaderworkerset.svg','Existing gang integration')]
for id,x,y,name,logo,status in items:
 a.image(x,y,65,55,ASSETS/logo);a.text(x+82,y+38,name,29,bold=True,width=365)
 a.text(x,y+90,status,23,'muted',width=425)
 a.nodes[id]=(x,y,435,118)
a.rect(555,145,365,272,'pale','line',3);a.text(585,185,'VOLCANO API',24,'blue',True,width=305)
for y,label in [(245,'PodGroup'),(307,'SubGroup policies'),(369,'Network topology')]:a.text(585,y,label,28,bold=True,width=310)
a.path([(435,59),(495,59),(495,445),(435,445)],False)
a.path([(435,252),(495,252)],False);a.path([(495,280),(550,280)])
a.path([(1030,134),(975,134),(975,394),(1030,394)],False)
a.path([(975,280),(925,280)])
a.text(1030,528,'Next: finer groups and locality',23,'blue',True,width=440)
a.text(0,553,'Controllers preserve role and replica identity; Volcano applies scheduling policy.',26,'blue',True,width=1470)

# 14: strong existing Kthena figure, kept in its original form.
a=art(14,'kthena-mapping','Kthena: From Serving Roles to Scheduling Groups','One ServingGroup maps to one PodGroup; each role replica forms a SubGroup.',3,6,'China 2026 slide 22; Kthena ModelServing gang scheduling guide.')
original(a,'china-22-kthena-gang.png',0,0,970,545)
code(a,1010,0,470,495,'ModelServing.spec · excerpt','''schedulerName: volcano
replicas: 1
template:
  gangPolicy:
    minRoleReplicas:
      prefill: 1
      decode: 3
  roles:
  - name: prefill
    replicas: 1
    workerReplicas: 1
  - name: decode
    replicas: 3
    workerReplicas: 1''',24,('minRoleReplicas','workerReplicas'),filename='kthena-modelserving-spec.yaml')
a.text(1025,540,'Pod templates omitted.',23,'muted',width=440)

# 15: YAML and actual logical replica membership, including a separate head.
a=art(15,'ray-replicas','KubeRay: A Replica Can Span Multiple Pods','The replica label separates complete groups inside one WorkerGroup.',3,11,'KubeRay #5249; #5369 open as of 2026-10-29. Volcano SubGroup API.')
a.text(0,36,'RayCluster workerGroupSpecs · excerpt',22,'muted',True,width=700)
code(a,0,58,690,153,'Multi-host WorkerGroup','''minReplicas: 2
numOfHosts: 2''',28,('minReplicas','numOfHosts'),filename='ray-worker-group.yaml')
for y,r in [(260,'replica-0'),(404,'replica-1')]:
 a.rect(0,y,690,115,'#f7faff','line',3);a.text(18,y+32,r+' → SubGroup',25,'blue',True,width=650)
 for i in range(2):a.box(r+str(i),20+i*340,y+49,310,48,'host '+str(i)+' · Pod','white',24)
code(a,750,0,730,390,'Generated PodGroup.spec · excerpt','''subGroupPolicy:
- name: worker
  labelSelector:
    matchLabels: {ray.io/group: worker}
  matchLabelKeys:
  - ray.io/worker-group-replica-name
  minSubGroups: 2
  subGroupSize: 2''',25,('matchLabelKeys','minSubGroups','subGroupSize'),filename='ray-subgroup-spec.yaml')
a.text(770,445,'Gang: merged  ·  Replica topology: in progress',24,'blue',True,width=700)
a.text(770,495,'The head uses a separate group.\nOne WorkerGroup can create multiple SubGroups.',24,'muted',width=690)

# 16: specific next relationship, drawn within a single PG; no fake API.
a=art(16,'subgroup-next','Next: Relationships Between SubGroups','Extend the placement model as controllers expose richer workload structure.',3,12,'docs/design/group-topology-affinity.md (proposed SubGroup relationships); roadmap #6166.')
a.text(0,40,'PROPOSED · within one PodGroup',23,'purple',True)
a.rect(0,74,925,440,'white','line',3,layer='bg',dash=True);a.text(23,112,'Serving instance · PodGroup',27,'blue',True)
for x,lab,role in [(30,'Rack A','Replica 0'),(480,'Rack B','Replica 1')]:
 a.rect(x,155,415,322,'#f8fafd','light',3,layer='bg');a.text(x+18,188,lab,25,'muted',True)
 for y,t,c in [(225,'Prefill / '+role,'mint'),(345,'Decode / '+role,'prefill')]:a.box(lab+t,x+18,y,379,74,t,c,25)
 a.path([(x+207,300),(x+207,339)],False,c='purple')
 a.text(x+240,329,'near',21,'purple')
a.path([(237,480),(237,495),(687,495),(687,480)],False,c='purple');a.text(395,544,'replicas apart',23,'purple',True,width=260)
note(a,995,85,'01','Affinity','Keep cooperating SubGroups in a shared domain.',475)
note(a,995,265,'02','Anti-affinity','Separate replicas across selected domains.',475)
a.text(1040,455,'Controller mappings and API semantics are still being developed.',25,'muted',width=425)

# 18: a real control/observation architecture with distinct data flows.
a=art(18,'benchmark-architecture','A Repeatable Scheduling Benchmark Framework','Generate scenarios, observe API events, and retain comparable measurements.',4,13,'benchmark/README.md; benchmark/scripts; benchmark/config; benchmark/testcases.')
a.rect(0,0,390,505,'white','light',3,layer='bg');a.text(22,39,'SCENARIO INPUT',22,'muted',True)
a.text(22,105,'Workload profiles',30,bold=True,width=345)
a.text(22,159,'Gang jobs / bare Pods',25,'muted',width=345)
a.text(22,239,'Cluster model',30,bold=True,width=345)
a.text(22,293,'Nodes, resources,\nHyperNode topology',25,'muted',width=345)
a.text(22,407,'Version + scheduler config',24,'blue',True,width=345)
a.rect(465,0,550,505,'pale','line',3,layer='bg');a.text(487,39,'KUBERNETES CLUSTER',22,'muted',True)
a.box('api',510,92,460,74,'API server / audit log','white',28,True)
a.box('scheduler',510,252,460,80,'Volcano scheduler','white',28,True)
a.box('nodes',510,406,460,64,'KWOK nodes / real nodes','white',25)
a.nodes['input']=(0,70,390,118);a.connect('input','right','api','left')
a.path([(655,168),(655,246)]);a.text(674,206,'watch objects',23,'muted',width=270)
a.path([(930,248),(930,210),(990,210),(990,70),(740,70),(740,88)]);a.text(888,192,'bind',21,'muted',width=90)
a.text(775,385,'placement',21,'muted',width=200)
a.connect('scheduler','bottom','nodes','top')
a.box('audit',1110,92,370,74,'audit-exporter','white',28)
a.box('prom',1110,252,370,80,'Prometheus','white',28)
a.box('report',1110,406,370,64,'Grafana / reports','white',26)
a.connect('api','right','audit','left');a.connect('audit','bottom','prom','top');a.connect('scheduler','right','prom','left');a.connect('prom','bottom','report','top')
a.text(1031,281,'metrics',18,'muted',width=90)
a.text(0,551,'KWOK exercises scheduling behavior; real workloads are needed for GPU / network performance.',25,'blue',True,width=1480)

# 19: source-backed commands, not empty progress cards.
a=art(19,'benchmark-progress','Benchmark Progress and Ongoing Validation','The harness is available; testing and optimization continue across workload scenarios.',4,14,'benchmark/README.md; benchmark/Makefile; benchmark/scripts/collect-report.sh.')
code(a,0,0,780,338,'benchmark/ · example workflow','''# Build from local source
make setup

# A gang workload scenario
make test-gang-env \\
  JOBS=10 REPLICAS=100 \\
  MIN_AVAILABLE=100''',27,('make test-gang-env',))
a.text(0,405,'AVAILABLE',21,'green',True)
a.text(0,453,'Kind / existing clusters · Gang / Pod profiles\nTopology setup · Audit / metrics · Reports',27,width=770)
note(a,850,56,'01','Vary the workload','Job size, total Pods, and placement constraints.',620)
note(a,850,230,'02','Compare consistently','Pin versions, resources, and measurement windows.',620)
note(a,850,404,'03','Repeat and investigate','Re-run observations and trace the bottlenecks.',620)

# 20: measurement boundaries and concrete interpretation.
a=art(20,'benchmark-measurement','From Measurements to Reliable Comparisons','Keep scheduling latency distinct from application readiness.',4,15,'benchmark/scripts/collect-report.sh and audit-exporter event definitions. No performance results selected.')
a.box('created',0,90,355,85,'Pod created','white',30,True);a.box('scheduled',565,90,355,85,'Pod scheduled','white',30,True);a.box('ready',1125,90,355,85,'Application ready','pale',27)
a.connect('created','right','scheduled','left');a.connect('scheduled','right','ready','left',dash=True)
a.text(380,68,'scheduling latency',23,'blue',True,width=220)
a.text(955,68,'runtime / application',21,'muted',width=250)
rule(a,0,250,1480)
for x,head,body in [(0,'Latency distribution','P50 / P90 / P99\nInclude the workload and scale.'),(520,'Scheduling throughput','State the observation window.\nKeep the raw events.'),(1040,'Comparison context','Version, configuration, resources\nand repeat runs.')]:
 a.text(x,320,head,29,bold=True,width=430);a.text(x,378,body,26,'muted',width=425)
a.text(0,535,'Current focus: repeatable comparisons and continued validation.',30,'blue',True,width=1470)

# 21,22: concise close.
a=art(21,'takeaways','Framework, Workloads, Ecosystem, Evidence','Four connected pieces of the scheduling story.',4,16)
for y,num,head,sub in [(0,'01','Unified scheduling','Coordinate node access across specialized scheduling paths.'),(132,'02','Workload-aware placement','Preserve complete groups, locality, and instance separation.'),(264,'03','Ecosystem integration','Bring controller roles and replica identity into scheduling.'),(396,'04','Benchmark and improve','Use repeatable measurements to guide ongoing validation.')]:
 a.text(0,y+42,num,30,'blue',True);a.text(100,y+42,head,32,bold=True,width=1350);a.text(100,y+94,sub,27,'muted',width=1350)
a=art(22,'questions','Questions & Discussion','Workload shapes, integration feedback, and reproducible observations are welcome.',0,17)
a.text(0,100,'What must your workload keep together—\nand what should it place apart?',40,bold=True,width=1400)
a.text(0,330,'github.com/volcano-sh/volcano',35,'blue',True,width=1380)
a.text(0,415,'Roadmap and feedback · issue #6166',29,'muted',width=1300)
for a in arts.values():a.save()

# Native PowerPoint title/profile/divider text. Source notes follow the remapped pages.
prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(7.5)
def ptext(sl,x,y,w,h,text,size=26,bold=False,c='ink',align=None):
 sh=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.clear();tf.word_wrap=True
 tf.margin_left=tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
 for i,line in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Liberation Sans';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(col(c).lstrip('#'));p.space_after=Pt(5)
  if align:p.alignment=align
 return sh
chapter_names={0:'MAINTAINER TRACK',1:'UNIFIED SCHEDULING',2:'MULTI-LEVEL GANG & NETWORK TOPOLOGY',3:'ECOSYSTEM',4:'BENCHMARK FRAMEWORK & PROGRESS'}
agenda=['Unified scheduling','Multi-level gang & network topology','Ecosystem','Benchmark framework & progress']
references=json.loads((ROOT/'references.json').read_text())
manifest=[]
for n in range(1,23):
 sl=prs.slides.add_slide(prs.slide_layouts[6]);special=n==1 or n in dividers
 sl.shapes.add_picture(str(PNG/('cover-background.png' if special else 'background.png')),0,0,width=prs.slide_width,height=prs.slide_height)
 sl.shapes.add_picture(str(ASSETS/'volcano-logo.png'),Inches(10.85),Inches(.32),width=Inches(1.9))
 ptext(sl,.50,.32,10,.28,chapter_names.get(dividers[n][0] if n in dividers else chapters.get(n,0)),11,True,'blue')
 notes=''
 if n==1:
  titles[n]='Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents'
  ptext(sl,.62,1.35,11.55,1.52,'Volcano for the\nAgentic AI Era:',43,True)
  ptext(sl,.66,3.10,10.80,1.30,'Unified Scheduling Across Training,\nInference, and Agents',31,False,'blue')
  ptext(sl,.68,5.02,11.6,.45,'Ricardo Aravena  ·  Rainie Li',25,True)
  ptext(sl,.68,5.69,11.8,.65,'KubeCon + CloudNativeCon North America 2026\nSalt Lake City · November 9–12',18,False,'muted')
  notes='0:20。标题保持不变。Agentic AI 作为基础设施背景，不把每次 agent 调用等同于一个 Pod。讲者姓名以用户指示为准。'
 elif n==2:
  titles[n]='Speakers'
  ptext(sl,.50,.95,12,.65,'Speakers',33,True)
  for x,person,photo,role,detail,link in [(.80,'Ricardo Aravena','ricardo.jpeg','Cloud Native & AI Infrastructure','Open-source infrastructure\nKubernetes and AI/ML platforms','serverbooter.com'),(7.05,'Rainie Li','rainie.jpeg','Pinterest','Data processing infrastructure\nApache YuniKorn PMC member','Apache YuniKorn · rainieli')]:
   sl.shapes.add_picture(str(ASSETS/photo),Inches(x),Inches(2.00),width=Inches(1.75),height=Inches(1.75))
   ptext(sl,x,4.02,5.4,.5,person,30,True)
   ptext(sl,x,4.68,5.3,.43,role,22,False,'blue')
   ptext(sl,x,5.27,5.3,.85,detail,20,False,'muted')
   ptext(sl,x,6.35,5.3,.30,link,15,False,'blue')
  notes='0:40。简介暂依据公开资料；Ricardo 当前公司和正式职务不确定，未填公司。收到讲者偏好后更新文字与头像。照片来自 Linux Foundation 公开讲者页。\nhttps://events.linuxfoundation.org/archive/2026/open-source-summit-north-america/program/program-committee/\nhttps://events.linuxfoundation.org/spinnaker-live/program/featured-speakers/\nhttps://yunikorn.apache.org/community/people/\nhttps://www.linkedin.com/in/rainie-li-71b2b146'
 elif n in dividers:
  c,title,bridge,question=dividers[n];titles[n]=title.replace('\n',' ');chapters[n]=c
  ptext(sl,.65,1.42,2,.70,f'{c:02d}',38,True,'blue')
  ptext(sl,.65,2.28,8.6,1.65,title,41,True)
  ptext(sl,.68,4.42,10.9,.60,bridge,24,False,'blue')
  ptext(sl,.68,5.24,11.6,.65,question,21,False,'muted')
  for i,t in enumerate(agenda,1):ptext(sl,9.30,1.7+(i-1)*.76,3.45,.68,f'{i:02d}  {t}',15,i==c,'blue' if i==c else 'muted')
  notes={3:'0:10。从统一调度框架切入，后面落到工作负载、生态和验证。',7:'0:15。转场：拿到可用节点之后，还要保留完整副本以及它们的通信局部性。',12:'0:10。转场：这些分组和拓扑语义，最终要由用户真正使用的 controller 传进来。',17:'0:10。转场：接入的控制器和约束越多，就越需要可重复的 benchmark。'}[n]
 else:
  ptext(sl,.50,.88,12.30,.70,titles[n],31 if len(titles[n])<52 else 28.5,True)
  ptext(sl,.52,1.57,12.25,.47,subtitles[n],17,False,'muted')
  sl.shapes.add_picture(str(PNG/(arts[n].name+'.png')),Inches(.50),Inches(2.12),width=Inches(12.333333),height=Inches(4.666667))
  talks={
   4:'1:00。先讲共同的基础设施需求：训练/RL 更强调协同计算，推理有角色与副本结构，agent 业务带来突发和延迟压力。并非每次 agent 调用都要创建一个 Pod。',
   5:'1:30。复用 China 架构图，从左右两条路径讲到中间 NodeShard。worker/Binder 的冲突检查是局部机制；不宣称并行一定带来性能提升。',
   6:'1:40。重点对照 nodesDesired 和 nodesInUse。期望集合变化后需等待协调器交接，不迁移运行中的 Pod。旧图中的资源策略是架构扩展点，不表示所有策略都已完成。',
   8:'2:00。用左边训练和右边 serving 两种结构解释 PodGroup 与 SubGroup，先看完整计算组，再看下面的放置域。一个 policy 可以按 replica label 分出多个实际 SubGroup。',
   9:'1:30。从物理网络映射到 HyperNode：非叶节点的成员是 HyperNode，叶节点的成员是 Node。standalone HyperNode 已交付；其他调度器 adapter 是独立的集成工作。',
   10:'2:00。PodGroup 是较大的实例边界，prefill 和 decode 的 locality 约束可以不同。两层约束都显式填写，不假设子组继承 PodGroup 的 topology。',
   11:'1:40。先让每个实例聚拢，再用 PodGroup anti-affinity 将两个实例分开。required 和 preferred 的差别是没有理想域时是否允许回退。',
   13:'1:15。依次区分已有接入和仍在扩展的能力。Grove 的 SubGroup backend 已合入，不表示支持所有 topology 约束。Kubeflow/LWS 已有接入，下一步深入分组与拓扑。',
   14:'1:40。沿用 China Kthena 图及关键 YAML，按 ServingGroup→PodGroup、role replica→SubGroup 的顺序讲。一个 Entry 加一个 Worker 组成两 Pod 副本。',
   15:'1:30。两个 replica，每个两个 hosts；用 matchLabelKeys 保持副本身份。head 另有分组。本页不把尚在推进的 KubeRay topology PR 当作已合入能力。',
   16:'1:10。说明后续在同一个 PodGroup 内表达 SubGroup affinity/anti-affinity 的方向。图是意图示例，不提供假装已可执行的未来 YAML。',
   18:'1:30。沿数据路径解释 benchmark：场景输入→API/调度器→audit-exporter 与 Prometheus→报告。KWOK 只验证调度行为，不代表真实 GPU 执行吞吐。',
   19:'1:20。已有框架、场景和观察能力是本章可以确定展示的进展。继续验证规模、约束和优化，不为了演讲单独制造漂亮结果。命令仅展示框架用法，本次没有运行集群测试。',
   20:'1:20。讲清 created→scheduled 的统计口径、吞吐窗口和对照条件。仍待选定一项代表性结果，可以后续原位替换本页。',
   21:'1:10。回扣四部分：路径协同、分组与拓扑、控制器映射、持续验证。邀请社区贡献具体 workload 与复现方式。',
   22:'5:00。问答。优先收集工作负载如何分组、需要哪些拓扑关系，以及可重复的测试场景。'
  }
  notes=talks[n]
  if n in oldnotes:
   links=references.get(str(oldnotes[n]),[])
   notes+='\n\n技术来源：\n'+'\n'.join(links)
  notes+='\n\n本页新版素材与说明：'+sources[n]
  if n==10:notes+='\n图例使用两个固定角色组，各4 Pods。spec 片段省略 labelSelector；实际使用时给两个 policy 配置匹配各自角色的 Pod selector。不是可直接 apply 的完整 manifest。'
  if n==11:notes+='\n启用 group-topology-affinity 与 network-topology-aware；每个 PodGroup 配置相同分离规则。selector 匹配 PodGroup 标签，默认同 namespace。'
  if n==14:notes+='\n图中每个 role replica 有一个 Entry 和一个 Worker Pod；YAML 保留 gangPolicy、role 副本数与 workerReplicas，省略 entryTemplate、workerTemplate 与 networkTopology。Gang 不表示所有 Pod 原子绑定或同时启动。'
  if n==16:notes+='\n本页为未来方向，不能当作已交付 API。示意同一 PodGroup 内将协作组放近、将副本分开；具体 selector 与亲和关系设计仍需社区讨论。'
  if n==20:notes+='\n尚未选定代表性 benchmark 结果，本页只讲测量口径，不呈现虚构性能曲线或提升比例。'
  notes+='\nVisual: na2026/svg/'+arts[n].name+'.svg。PNG 固定几何；复用的旧图原本为位图，新增 YAML 和注释为 SVG 文本。'
 ptext(sl,.52,7.13,11.5,.22,'Volcano  |  KubeCon + CloudNativeCon North America 2026',9,False,'muted')
 ptext(sl,12.05,7.09,.75,.28,f'{n:02d} / 22',11,False,'muted',PP_ALIGN.RIGHT)
 sl.notes_slide.notes_text_frame.text=notes
 manifest.append({'page':n,'title':titles[n],'chapter':chapters.get(n,0),'svg':f'svg/{arts[n].name}.svg' if n in arts else None,'source':sources.get(n,'Native PowerPoint text'),'previous_draft_notes_page':oldnotes.get(n)})
prs.core_properties.title=titles[1];prs.core_properties.subject='KubeCon NA 2026 — revised technical presentation'
prs.core_properties.author='Ricardo Aravena; Rainie Li';prs.core_properties.comments='2026-10-29. Retained China/EU figures; API excerpts; 4 chapter dividers. No invented benchmark results.'
out=PPT/'Volcano_KubeCon_NA_2026.pptx';prs.save(out)
(ROOT/'manifest.json').write_text(json.dumps({'deck':out.name,'slides':manifest,'examples_are_excerpts':True,'benchmark':'Framework and ongoing validation; no invented results.'},ensure_ascii=False,indent=2)+'\n')
print(out);print('22 slides; reused original figures; six API examples and chapter dividers.')
