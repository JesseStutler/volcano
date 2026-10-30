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
C={'ink':'#17283b','muted':'#414f60','line':'#52677f','light':'#a6b5c6','pale':'#f2f5f9','blue':'#164f89','prefill':'#dce9f8','decode':'#dce5ee','green':'#146653','mint':'#deeee8','purple':'#62448d','lav':'#eae3f3','orange':'#c14421','amber':'#8b621c','sand':'#fff5e2','white':'#ffffff'}
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
 def __init__(self,name,w=1480,h=560):self.name=name;self.w=w;self.h=h;self.bg=[];self.edges=[];self.front=[];self.routes=[];self.nodes={};self.textboxes=[]
 def rect(self,x,y,w,h,fill='white',stroke='light',rx=8,layer='front',dash=False):
  el=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{col(fill)}" stroke="{col(stroke) if stroke else "none"}" stroke-width="2.2"'+(' stroke-dasharray="7 5"' if dash else '')+'/>'
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
  route={'points':points,'arrow':arrow,'color':col(c)}
  self.routes.append(route)
  d='M'+' L'.join(f'{x},{y}' for x,y in points)
  self.edges.append(f'<path d="{d}" fill="none" stroke="{col(c)}" stroke-width="2.5" stroke-linejoin="round"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')
  if arrow:
   # Explicit symmetric chevron, with the same tip coordinate as the shaft.
   # No marker scaling/rotation is delegated to the SVG or PPT renderer.
   x,y=points[-1];px,py=points[-2];dx=x-px;dy=y-py
   length=(dx*dx+dy*dy)**.5
   assert length>=12, (self.name,points)
   ux,uy=dx/length,dy/length
   left=(x-10*ux-5*uy,y-10*uy+5*ux)
   right=(x-10*ux+5*uy,y-10*uy-5*ux)
   route['head']=[left,(x,y),right]
   self.edges.append(f'<path d="M{left[0]},{left[1]} L{x},{y} L{right[0]},{right[1]}" fill="none" stroke="{col(c)}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
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
  markers=''.join(f'<marker id="arrow-{color.lstrip(chr(35))}" viewBox="0 0 12 12" refX="12" refY="6" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 L12 6 L0 12 Z" fill="{color}"/></marker>' for color in sorted(set(C.values())))
  content=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><title>{escape(self.name)}</title><defs>{markers}</defs>'+''.join(self.bg+self.edges+self.front)+'</svg>'
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
 a.rect(x,y,w,h,'#f5f7fa','line',3)
 a.rect(x,y,w,47,'white',None,0)
 a.path([(x,y+47),(x+w,y+47)],False,'blue')
 a.text(x+20,y+32,label,24,'blue',True,width=w-40)
 lh=size*1.19
 for i,line in enumerate(body.strip('\n').splitlines()):
  yy=y+75+i*lh
  if ImageFont.truetype(MONO,size*2).getlength(line)/2>w-36:raise ValueError(f'Code line too wide: {a.name}: {line}')
  if yy>y+h-7:raise ValueError(f'Code overflows {a.name}: {label}')
  if any(k in line for k in highlights):
   a.rect(x+3,yy-size+2,w-6,lh,'#dce9f8',None,0)
   a.rect(x+3,yy-size+2,5,lh,'blue',None,0)
  rawtext(a,x+20,yy,line,size,'blue' if any(k in line for k in highlights) else 'ink',False,True)
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

# 04: composition in approved_revision.py.
a=art(4,'workload-demands','Different Workloads, Shared Infrastructure','Training, inference, and agent applications put different demands on the same cluster.',1,2)

# 05: retain the original detailed architecture, not a replacement box summary.
a=art(5,'unified-architecture','A Coordinated Scheduling Framework','Specialized scheduling paths coordinate through NodeShard.',1,3,'China 2026 slide 7; same architecture family as EU 2026.')
original(a,'china-07-unified-architecture.png',0,0,970,550,(0,115,3129,2051))
note(a,1020,65,'01','Workload paths','Batch-oriented scheduling and a Pod-oriented fast path.',445)
note(a,1020,245,'02','Local coordination','Parallel workers use Binder conflict checks.',445)
note(a,1020,425,'03','Shared node access','NodeShard coordinates candidate-node pools.',445)

# 06: original controller plus an actual NodeShard excerpt.
a=art(6,'nodeshard','NodeShard: Desired Nodes and Current Use','Changing a shard coordinates future placement; it does not migrate running Pods.',1,4,'China 2026 slide 9; docs/design/agent-scheduler.md; shard API types.')
original(a,'china-09-dynamic-node-sharding.png',0,0,620,545)
code(a,690,0,790,500,'NodeShard · spec / status excerpt','''spec:
  nodesDesired:
  - node1
  - node2
status:
  nodesInUse:
  - node0
  - node1
  nodesToRemove:
  - node0
  nodesToAdd:
  - node2''',29,('nodesDesired','nodesInUse'),filename='nodeshard.yaml')
a.text(710,500,'Desired membership ≠ immediate use',29,'blue',True,width=740)
a.text(710,541,'Coordinators reconcile node access.',26,'muted',width=740)

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
      name: rack-a''',30,('type: HyperNode','name: rack-a'),filename='hypernode-parent-spec.yaml')
code(a,995,0,485,510,'Leaf · HyperNode.spec','''tier: 1
tierName: leaf
members:
- type: Node
  selector:
    labelMatch:
      matchLabels:
        rack: rack-a''',30,('type: Node','rack: rack-a'),filename='hypernode-leaf-spec.yaml')
a.text(0,553,'The same hierarchy is available through the standalone HyperNode component.',26,'blue',True,width=1470)

# 10: reuse the actual network drawing, with the two topology levels in YAML.
a=art(10,'multilevel-placement','Place Groups at Different Topology Levels','An eight-Pod instance spans a larger domain; Prefill and Decode use different locality constraints.',2,8,'EU 2026 slide 16 / China 2026 slide 17; PodGroup API. Selector and Decode fragment below are explanatory excerpts.')
original(a,'china-17-multilevel-topology.png',0,0,900,510)
code(a,940,0,540,531,'PodGroup.spec · key fields','''minMember: 8
networkTopology:
  mode: hard
  highestTierName: core
subGroupPolicy:
- name: prefill
  subGroupSize: 4
  networkTopology:
    mode: hard
    highestTierName: leaf
- name: decode
  subGroupSize: 4
  networkTopology:
    mode: hard
    highestTierName: spine'''.replace('    mode: hard\n','').replace('  mode: hard\n',''),28,('highestTierName',),filename='multilevel-topology-spec.yaml')
a.text(0,554,'Named tiers: core (3) · spine (2) · leaf (1)',24,'blue',True,width=910)

# 11: composition in approved_revision.py.
a=art(11,'instance-isolation','Keep Each Instance Together, Place Instances Apart','ServingGroup → PodGroup: a Kthena scenario. Anti-affinity integration in Kthena is proposed.',2,9,'docs/user-guide/how_to_use_podgroup_anti_affinity.md; group-topology-affinity plugin, v1.16.')

# 13: composition in approved_revision.py.
a=art(13,'ecosystem','Next: RBG, Kubeflow, and LWS','Build on current integrations; carry finer group structure and placement requirements.',3,10,'Kthena docs; KubeRay #5249 / #5369; Grove #516; RBG gang-scheduling docs; Kubeflow Trainer Volcano plugin; LWS README / DisaggregatedSet. Roadmap intent supplied by maintainers.')

# 14: strong existing Kthena figure, kept in its original form.
a=art(14,'kthena-mapping','Kthena: From Serving Roles to Scheduling Groups','One ServingGroup maps to one PodGroup; each role replica forms a SubGroup.',3,6,'China 2026 slide 22; Kthena ModelServing gang scheduling guide.')
original(a,'china-22-kthena-gang.png',0,0,970,545)
code(a,1010,0,470,535,'ModelServing.spec · excerpt','''schedulerName: volcano
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
    workerReplicas: 1''',28,('minRoleReplicas','workerReplicas'),filename='kthena-modelserving-spec.yaml')
a.text(1025,540,'Pod templates omitted.',23,'muted',width=440)

# 15: composition in polish_figures.py.
a=art(15,'ray-replicas','KubeRay: A Replica Can Span Multiple Pods','The replica label separates complete groups inside one WorkerGroup.',3,11,'KubeRay #5249; #5369 open as of 2026-10-29. Volcano SubGroup API.')

# 16: composition in approved_revision.py.
a=art(16,'subgroup-next','Next: Relationships Between SubGroups','Keep cooperating groups local while separating replicas inside the same PodGroup.',2,12,'docs/design/group-topology-affinity.md (proposed SubGroup relationships); roadmap #6166.')

# 18: composition in polish_figures.py.
a=art(18,'benchmark-architecture','A Repeatable Scheduling Benchmark Framework','Generate scenarios, observe API events, and retain comparable measurements.',4,13,'benchmark/README.md; benchmark/scripts; benchmark/config; benchmark/testcases.')

# 19: composition in approved_revision.py.
a=art(19,'benchmark-progress','Compare Schedulers on the Same Workload','Repeat controlled runs to understand throughput, latency, and placement tradeoffs.',4,14,'benchmark/README.md; benchmark/Makefile; benchmark/scripts/collect-report.sh.')

# 20: composition in approved_revision.py.
a=art(20,'benchmark-measurement','Which Scenarios Fit Which Scheduler?','Expand tests across arrival patterns, group structure, and network topology.',4,15,'benchmark/scripts/collect-report.sh and audit-exporter event definitions. No performance results selected.')

# 21–22: typographic close in polish_figures.py.
a=art(21,'takeaways','What We Will Work On Next','Next steps in group placement, controller integration, and benchmarking.',4,16)
a=art(22,'questions','Questions & Discussion','Workload shapes, integration feedback, and reproducible observations are welcome.',0,17)
from polish_figures import polish
polish(arts, art, code, rawtext, C, ASSETS)
from approved_revision import revise
revise(arts, art, code, rawtext, original, C, ASSETS)
from light_edit import light_edit
removed_notes=light_edit(arts)
subtitles={n:re.sub(r";\s+([A-Za-z])",lambda m:". "+m.group(1).upper(),s) for n,s in subtitles.items()}
from speaker_labels import speaker_labels
speaker_labels(arts, subtitles, removed_notes, C)
from balanced_captions import balance_captions
balance_captions(arts, subtitles, removed_notes, titles)
from community_slides import add_community_slides
add_community_slides(arts, art, titles, ASSETS)
subtitles[22]=""
order=[1,2,3,4,5,6,7,8,9,10,11,16,12,14,15,23,13,17,18,19,20,21,24,22]
page_for={source_id:page for page,source_id in enumerate(order,1)}
for n,a in arts.items():
 a.name=f'{page_for[n]:02d}-'+a.name.split('-',1)[1]
 a.save()
# Remove only stale generated body images after a page-order change.
valid={a.name for a in arts.values()}|{'background','cover-background'}
for folder in [SVG,PNG]:
 for path in folder.iterdir():
  if path.suffix in ['.svg','.png'] and path.stem not in valid:path.unlink()
(ROOT/'geometry-audit.json').write_text(json.dumps({str(page_for[n]):a.routes for n,a in arts.items()},indent=2)+'\n')

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
for page,n in enumerate(order,1):
 sl=prs.slides.add_slide(prs.slide_layouts[6]);special=n==1 or n in dividers
 sl.shapes.add_picture(str(PNG/('cover-background.png' if special else 'background.png')),0,0,width=prs.slide_width,height=prs.slide_height)
 sl.shapes.add_picture(str(ASSETS/'volcano-logo.png'),Inches(10.85),Inches(.32),width=Inches(1.9))
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
  for x,person,photo,role,detail,link in [(.80,'Ricardo Aravena','ricardo.jpeg','AI Infrastructure Lead · Nunchux AI','CNCF TOC Alternate (GB)\nCloud native and AI infrastructure','nunchux.ai · CNCF TOC'),(7.05,'Rainie Li','rainie.jpeg','Pinterest','Data processing infrastructure\nApache YuniKorn PMC member','Apache YuniKorn · rainieli')]:
   sl.shapes.add_picture(str(ASSETS/photo),Inches(x),Inches(2.00),width=Inches(1.75),height=Inches(1.75))
   ptext(sl,x,4.02,5.4,.5,person,30,True)
   ptext(sl,x,4.68,5.3,.43,role,22,False,'blue')
   ptext(sl,x,5.27,5.3,.85,detail,20,False,'muted')
   ptext(sl,x,6.35,5.3,.30,link,15,False,'blue')
  notes='0:40。Ricardo：NA 2026 官方会议资料列为 Nunchux AI 的 AI Infrastructure Lead；CNCF TOC 页面列为 TOC Alternate (GB)，不是 Governing Board 成员，不写 Founder 或 CEO。2026-10-29 核查。照片来自 Linux Foundation 公开讲者页。\nhttps://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/program/schedule/?id=1289640\nhttps://www.cncf.io/people/technical-oversight-committee/\nhttps://events.linuxfoundation.org/archive/2026/open-source-summit-north-america/program/program-committee/\nhttps://events.linuxfoundation.org/spinnaker-live/program/featured-speakers/\nhttps://yunikorn.apache.org/community/people/\nhttps://www.linkedin.com/in/rainie-li-71b2b146'
 elif n in dividers:
  c,title,bridge,question=dividers[n];titles[n]=title.replace('\n',' ');chapters[n]=c
  ptext(sl,.65,1.42,2,.70,f'{c:02d}',38,True,'blue')
  ptext(sl,.65,2.28,8.6,1.65,title,41,True)
  ptext(sl,.68,4.42,10.9,.60,bridge,24,False,'blue')
  for i,t in enumerate(agenda,1):ptext(sl,9.30,1.7+(i-1)*.76,3.45,.68,f'{i:02d}  {t}',15,i==c,'blue' if i==c else 'muted')
  notes={3:'0:10。从统一调度框架切入，后面落到工作负载、生态和验证。',7:'0:15。转场：拿到可用节点之后，还要保留完整副本以及它们的通信局部性。',12:'0:10。转场：这些分组和拓扑语义，最终要由用户真正使用的 controller 传进来。',17:'0:10。转场：接入的控制器和约束越多，就越需要可重复的 benchmark。'}[n]
 else:
  ptext(sl,.50,.88,12.30,.70,titles[n],31 if len(titles[n])<52 else 28.5,True)
  if subtitles[n]:ptext(sl,.52,1.50,12.25,.47,subtitles[n],21,False,'blue')
  sl.shapes.add_picture(str(PNG/(arts[n].name+'.png')),Inches(.50),Inches(2.05 if subtitles[n] else 1.80),width=Inches(12.333333),height=Inches(4.666667))
  talks={
   4:'1:20。训练图展示两个 PP stage，每个 stage 两个 TP ranks，需要完整子组及通信局部性。推理展示 P/D 分离，不同角色及副本的 gang 与 topology 约束。Agent 路径先命中预热池并复用 ready runtime；池子耗尽时由 runtime/pool controller 请求容量，经快速 Pod 调度补池。请求突发图是需求示意，没有测量值。池管理不是 Volcano 自带能力，也不是每次调用创建 Pod。',
   5:'1:30。复用 China 架构图，从左右两条路径讲到中间 NodeShard。worker/Binder 的冲突检查是局部机制；不宣称并行一定带来性能提升。',
   6:'1:40。重点对照 nodesDesired 和 nodesInUse。期望集合变化后需等待协调器交接，不迁移运行中的 Pod。旧图中的资源策略是架构扩展点，不表示所有策略都已完成。',
   8:'2:00。用左边训练和右边 serving 两种结构解释 PodGroup 与 SubGroup，先看完整计算组，再看下面的放置域。一个 policy 可以按 replica label 分出多个实际 SubGroup。',
   9:'1:30。从物理网络映射到 HyperNode：非叶节点的成员是 HyperNode，叶节点的成员是 Node。standalone HyperNode 已交付；其他调度器 adapter 是独立的集成工作。',
   10:'2:00。PodGroup 是较大的实例边界，prefill 和 decode 的 locality 约束可以不同。两层约束都显式填写，不假设子组继承 PodGroup 的 topology。',
   11:'1:40。复用第 10 页网络层级及交换机符号，两个 Supernode 共用上层 core fabric。两个完整服务实例各在一个域，避免一次域故障同时影响两份实例。P/D 是简化角色标记，不代表唯一模型结构。Kthena ServingGroup→PodGroup 可作为场景，但 topology affinity 接入截至 2026-10-29 仍是开放 proposal #1478 / issue #645，不能说 Kthena 已交付 anti-affinity。HA 的服务恢复还需 routing/health checks，scheduler 不提供应用故障切换。',
   13:'0:50。具体 Kthena、KubeRay、Grove 案例之后再讲后续社区方向。RBG 推进中，已有 RoleInstance→SubGroup 基础；Kubeflow 计划在现有 Volcano 插件上深化分组及拓扑；LWS 计划 multi-role/multi-group 支持。状态来自 maintainer 的推进计划，不能写作全部已交付。',
   14:'1:40。沿用 China Kthena 图及关键 YAML，按 ServingGroup→PodGroup、role replica→SubGroup 的顺序讲。一个 Entry 加一个 Worker 组成两 Pod 副本。',
   15:'1:30。两个 replica，每个两个 hosts；用 matchLabelKeys 保持副本身份。head 另有分组。本页不把尚在推进的 KubeRay topology PR 当作已合入能力。',
   16:'1:20。放在第二章，以相同 fabric 演进关系语义。同一个 PodGroup 的 Prefill 与两个 Decode SubGroup 都位于 Supernode A，满足上层亲和；两个 Decode 副本分别位于 Leaf 0 与 Leaf 1，满足更细层级的反亲和。每个 SubGroup 都是完整两 Pod 组。Supernode B 和其他空闲 rack 表明这些约束是有选择的放置，而非资源只剩此处。关系 API 为 proposed，不提供伪造的可执行 YAML。',
   18:'1:30。沿数据路径解释 benchmark：场景输入→API/调度器→audit-exporter 与 Prometheus→报告。KWOK 只验证调度行为，不代表真实 GPU 执行吞吐。',
   19:'1:20。已有 harness 为重复场景和指标采集打底。后续在同样集群容量、相同 workload arrivals/grouping/resources 下逐个运行不同 scheduler；每次 reset，不能让调度器同时竞争资源。固定每个实现的版本、配置和指标口径；记录各自合理调参后的配置。Kubernetes scheduler 可作为支持场景的 baseline，其他调度器集合待确定。未支持 gang 或 topology 的调度器不强行比较相同语义，须标注差异。比较 tail latency、binding throughput、完整 gang 数及放置正确性，不展示虚构结果。',
   20:'1:20。选择代表性场景，寻找每种 scheduler 的适用边界，不只找有利 Volcano 的配置。第一类改变 arrival rate、预留容量，观察突发的尾延迟和积压恢复；只测试 pool 容量请求的调度，不用 KWOK 宣称完整 agent runtime 延迟。第二类改变 SubGroup 大小和可用资源碎片，观察完整 gangs 和 binding throughput。第三类组合 topology tier limits、可用域、gang/anti-affinity，检查 placement correctness 与完成延迟。KWOK 可以验证调度行为；NCCL/KV 带宽及实际模型吞吐需要真实硬件另测。本页是 ongoing/planned test matrix，没有 benchmark 数字。',
   21:'1:00。收尾强调下一步：SubGroup affinity/anti-affinity 的语义与实现；RBG/Kubeflow/LWS multi-group 的社区工作；多调度器横向对照、代表性场景及 topology-aware gang 测试。',
   23:'0:50。根据 Grove main 的实际 Volcano backend：一个 PodGang 生成一个 Volcano PodGroup；PodGang.spec.podGroups 中每一项生成 SubGroup policy，name 和 PodClique label 选中组，subGroupSize=max(minReplicas,1)，minSubGroups=1。图示两个组分别 2 和 4 Pods，总 minMember=6。当前 main 明确拒绝 PodCliqueSet / PodClique / PodCliqueScalingGroup 上的 topologyConstraint。区分已合入的 adapter 与发布版本支持；不要只依据 #516 初始 PR 描述判断后续 main。\nhttps://github.com/NVIDIA/grove/blob/main/operator/internal/scheduler/volcano/backend.go',
   24:'0:20。复用 China 第 25 页的 32 个社区用户 logo，保留素材来源，不新增商业伙伴关系或用户数量声明。',
   22:'5:00。问答。优先收集工作负载如何分组、需要哪些拓扑关系，以及可重复的测试场景。'
  }
  notes=talks[n]
  if removed_notes.get(n):notes+='\n移入备注的外围说明：\n'+'\n'.join(removed_notes[n])
  if n==22:notes+='\n二维码复用 China 第 25 页，分别指向 https://volcano.sh、https://github.com/volcano-sh/volcano、https://cloud-native.slack.com/archives/C011GJDQS0N。'
  if n in oldnotes:
   links=references.get(str(oldnotes[n]),[])
   notes+='\n\n技术来源：\n'+'\n'.join(links)
  notes+='\n\n本页新版素材与说明：'+sources[n]
  if n==13:notes+='\nhttps://github.com/sgl-project/rbg/blob/main/doc/features/gang-scheduling.md\nhttps://github.com/kubernetes-sigs/lws/blob/main/README.md\n右侧为 maintainer 提供的推进方向；RBG 公开文档已有 RoleInstance→SubGroup 基础。LWS 已有副本组，下一步是跨角色 multi-group 调度集成。'
  if n==10:notes+='\n本页三处 networkTopology 均按 mode: hard 讲解，展示片段省略重复字段。图例使用两个固定角色组，各4 Pods。spec 片段省略 labelSelector；实际使用时给两个 policy 配置匹配各自角色的 Pod selector。不是可直接 apply 的完整 manifest。'
  if n==11:notes+='\nhttps://github.com/volcano-sh/kthena/pull/1478\nhttps://github.com/volcano-sh/kthena/issues/645\n启用 group-topology-affinity 与 network-topology-aware；每个 PodGroup 配置相同分离规则。selector 匹配 PodGroup 标签，默认同 namespace。'
  if n==14:notes+='\n图中每个 role replica 有一个 Entry 和一个 Worker Pod；YAML 保留 gangPolicy、role 副本数与 workerReplicas，省略 entryTemplate、workerTemplate 与 networkTopology。Gang 不表示所有 Pod 原子绑定或同时启动。'
  if n==16:notes+='\n本页为未来方向，不能当作已交付 API。示意同一 PodGroup 内将协作组放近、将副本分开；具体 selector 与亲和关系设计仍需社区讨论。'
  if n==20:notes+='\n口径：scheduledAt−createdAt；binding throughput 为成功 bindings / 首尾成功 bind 时间差。对照时保留原始事件、重复次数与环境配置。命令与完整指标定义见 benchmark/README.md。'
  notes+='\nVisual: na2026/svg/'+arts[n].name+'.svg。PNG 固定几何；复用的旧图原本为位图，新增 YAML 和注释为 SVG 文本。'
 ptext(sl,.52,7.13,11.5,.22,'Volcano  |  KubeCon + CloudNativeCon North America 2026',9,False,'muted')
 ptext(sl,12.05,7.09,.75,.28,f'{page:02d} / {len(order)}',11,False,'muted',PP_ALIGN.RIGHT)
 sl.notes_slide.notes_text_frame.text=notes
 manifest.append({'page':page,'source_id':n,'title':titles[n],'chapter':chapters.get(n,0),'svg':f'svg/{arts[n].name}.svg' if n in arts else None,'source':sources.get(n,'Native PowerPoint text'),'previous_draft_notes_page':oldnotes.get(n)})
prs.core_properties.title=titles[1];prs.core_properties.subject='KubeCon NA 2026 — revised technical presentation'
prs.core_properties.author='Ricardo Aravena; Rainie Li';prs.core_properties.comments='2026-10-29. Retained China/EU figures; API excerpts; 4 chapter dividers. No invented benchmark results.'
out=PPT/'Volcano_KubeCon_NA_2026.pptx';prs.save(out)
(ROOT/'manifest.json').write_text(json.dumps({'deck':out.name,'slides':manifest,'examples_are_excerpts':True,'benchmark':'Framework and ongoing validation; no invented results.'},ensure_ascii=False,indent=2)+'\n')
print(out);print(f'{len(order)} slides; r12 diagram explanations at API mappings; eight YAML excerpts and chapter dividers.')
