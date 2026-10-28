"""Build editable NA 2026 working slides. Requires python-pptx.
Run from any directory; output is written to the parent ppt directory.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
from PIL import ImageFont

OUT = Path(__file__).resolve().parent.parent
prs = Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
C={'navy':'202D3C','muted':'647282','line':'8EA8CB','blue':'356696','pale':'F0F5FB','white':'FFFFFF','yellow':'FFF4D8','amber':'8B621C','purple':'765399','lav':'F2EDF8','green':'386C5A','mint':'EDF5F1','decode':'E8EDF3'}
FONT='Liberation Sans'; MONO='Liberation Mono'; CN='Noto Sans CJK SC'

def color(v): return RGBColor.from_string(C.get(v,v))
def rect(sl,x,y,w,h,fill='pale',line=None,radius=False):
 sh=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
 sh.fill.solid(); sh.fill.fore_color.rgb=color(fill)
 sh._element.spPr.append(OxmlElement('a:effectLst'))
 if line: sh.line.color.rgb=color(line); sh.line.width=Pt(1)
 else: sh.line.fill.background()
 if radius:
  try: sh.adjustments[0]=0.08
  except Exception: pass
 return sh

def txt(sl,x,y,w,h,text,size=20,bold=False,c='navy',font=FONT,align=None):
 sh=sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf=sh.text_frame
 tf.word_wrap=True; tf.margin_left=Inches(.02); tf.margin_right=Inches(.02); tf.margin_top=Inches(.02); tf.margin_bottom=0
 for i,line in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.text=line
  p.font.name=font; p.font.size=Pt(size); p.font.bold=bold; p.font.color.rgb=color(c)
  p.space_after=Pt(5)
  if align is not None:p.alignment=align
 return sh

def box(sl,x,y,w,h,label,fill='white',size=17,c='navy',line='line'):
 sh=rect(sl,x,y,w,h,fill,line,True); tf=sh.text_frame;tf.clear();tf.word_wrap=True;tf.vertical_anchor=MSO_ANCHOR.MIDDLE
 tf.margin_left=Inches(.12);tf.margin_right=Inches(.12)
 p=tf.paragraphs[0];p.text=label;p.alignment=PP_ALIGN.CENTER;p.font.name=FONT;p.font.size=Pt(size);p.font.color.rgb=color(c)
 return sh

def link(sl,x1,y1,x2,y2,c='line'):
 sh=sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2));sh.line.color.rgb=color(c);sh.line.width=Pt(1.5)
 return sh

def badge(sl,x,y,label,fill='pale',c='blue',w=1.8):
 rect(sl,x,y,w,.32,fill);txt(sl,x+.07,y+.03,w-.1,.24,label,10,True,c)

def note(sl,text,sources=()):
 sl.notes_slide.notes_text_frame.text='讲者备注 / Draft notes\n'+text+'\n\nSources (status checked 2026-10-28):\n'+'\n'.join(sources)

def base(title,chapter,n,timing,edit,source=''):
 sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.background.fill.solid();sl.background.fill.fore_color.rgb=color('white')
 rect(sl,.0,.0,13.333,.08,'navy')
 txt(sl,.52,.25,10,.3,chapter.upper(),11,True,'blue')
 txt(sl,.52,.76,12.25,.88,title,29 if len(title)<60 else 27,True)
 rect(sl,.55,6.57,12.23,.51,'yellow')
 txt(sl,.70,6.67,11.92,.30,edit,10.5,False,'amber',CN)
 txt(sl,.55,7.20,10.5,.19,'VOLCANO  /  KUBECON NA 2026  /  WORKING DRAFT  •  '+timing,9,False,'muted')
 txt(sl,12.04,7.16,.71,.26,f'{n:02d} / 17',10,False,'muted',align=PP_ALIGN.RIGHT)
 if source:txt(sl,.57,6.29,12,.18,source,9,False,'muted')
 return sl

def bullets(sl,items,x=.63,y=1.95,w=4.30,size=21):
 for head,body in items:
  f=ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',round(size*4))
  lines=['']
  for word in head.split():
   proposed=(lines[-1]+' '+word).strip()
   if f.getlength(proposed)>(w-.08)*72*4 and lines[-1]:lines.append(word)
   else:lines[-1]=proposed
  hh=.38*len(lines)
  txt(sl,x,y,w,hh+.04,'\n'.join(lines),size,True)
  txt(sl,x,y+hh+.10,w,.77,body,17,False,'muted')
  y+=1.42

def panel(sl,label='EDITABLE DIAGRAM DRAFT',x=5.30,y=1.85,w=7.45,h=4.22):
 rect(sl,x,y,w,h,'pale');txt(sl,x+.18,y+.14,w-.36,.27,label,10,False,'muted',MONO)

def pod(sl,x,y,label,fill='pale',w=.70):return box(sl,x,y,w,.43,label,fill,12)

def replica(sl,x,y,label,fill='pale',w=2.2):
 rect(sl,x,y,w,1.10,'white','line',True);txt(sl,x+.10,y+.08,w-.20,.27,label,12,True)
 pod(sl,x+.14,y+.48,'Pod 1',fill,.85);pod(sl,x+1.13,y+.48,'Pod 2',fill,.85)

D='https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/design/'
R16='https://github.com/volcano-sh/volcano/releases/tag/v1.16.0'
R17='https://github.com/volcano-sh/volcano/issues/6166'
AA='https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/user-guide/how_to_use_podgroup_anti_affinity.md'
KT='https://github.com/volcano-sh/kthena/blob/main/docs/kthena/versioned_docs/version-v1.0.0/user-guide/'
RAY='https://github.com/kuberay-project/kuberay/pull/'
GROVE='https://github.com/ai-dynamo/grove/pull/516'

# 01 — title
s=base('','Maintainer Track',1,'0:30','待确认：讲者姓名、署名顺序与单位；当前为工作版式，未套用官方模板。')
txt(s,.64,1.20,11.9,1.55,'Volcano for the\nAgentic AI Era',43,True)
txt(s,.68,3.00,11.5,1.12,'Unified Scheduling Across Training,\nInference, and Agents',29,False,'blue')
txt(s,.70,4.45,11,.5,'KubeCon + CloudNativeCon North America 2026',19,False,'muted')
box(s,.70,5.25,7.8,.55,'SPEAKERS / AFFILIATIONS — TO CONFIRM','pale',14,'muted')
note(s,'0:30。原标题保持不变。开场一句：今天先讲调度路径之间如何协调，再讲分布式工作负载内部如何成组和放置。姓名与单位由讲者最终确认。')

# 02
s=base('Different Workloads, Shared Infrastructure','01 / Coordinating scheduling paths',2,'1:00','复用：生命周期图精简。Agent 应用依赖推理服务，不把每次调用画成一个新 Pod。')
bullets(s,[('Different arrival patterns','Long-running services, grouped compute, and bursts.'),('Different scheduling needs','Responsiveness, complete groups, and communication locality.'),('A shared resource pool','Coordinate infrastructure without forcing one execution model.')])
panel(s)
box(s,8.9,2.42,3.23,.60,'Agent applications');link(s,10.52,3.02,10.52,3.60)
box(s,5.75,3.60,2.65,.75,'Training / RL');box(s,8.9,3.60,3.23,.75,'Inference services')
link(s,7.07,4.35,7.07,4.85);link(s,10.52,4.35,10.52,4.85)
box(s,5.75,4.85,6.38,.75,'Shared Kubernetes infrastructure','white',21)
note(s,'1:00。Agentic AI 是应用背景，Volcano 讨论底层 Kubernetes 工作负载。训练与 RL 是平台工作负载，不暗示每次 Agent 请求都会触发它们。Substrate / CubeSandbox 可在 worker 资源池上自行调度执行单元。')

# 03
s=base('A Coordinated Scheduling Framework','01 / Coordinating scheduling paths',3,'1:30','复用：China 7–8 / EU 9。worker / Binder 讲 30–45 秒；本页不放性能提升数字。')
bullets(s,[('Keep different scheduling paths','Support distinct workload requirements.'),('Coordinate access to nodes','NodeShard connects the paths at the infrastructure layer.'),('Handle local conflicts','Workers and Binder coordinate within the Agent Scheduler.')])
panel(s,'SCHEMATIC — REUSE / SIMPLIFY EXISTING ARCHITECTURE')
box(s,5.67,2.60,2.65,1.25,'Volcano Scheduler\nGroup scheduling','white',19)
box(s,9.08,2.60,3.25,1.25,'Agent Scheduler\nWorkers + Binder','white',19)
link(s,7.0,3.85,7.0,4.50);link(s,10.7,3.85,10.7,4.50)
box(s,5.67,4.5,6.66,.85,'NodeShard coordination','white',21)
txt(s,5.82,5.52,6.4,.30,'Scheduler-internal conflicts ≠ cross-scheduler coordination',11,False,'muted',MONO)
note(s,'1:30。这张图是职责概览，不表示 Binder 是所有 scheduler 共享的全局事务协调器。Worker 使用自己的 snapshot；Binder 的冲突处理属于 Agent Scheduler 内部。统一框架不等于统一算法，也不代表全局资源记账已经强一致。',[D+'agent-scheduler.md'])

# 04
s=base('NodeShard: Coordinating Node Access','01 / Coordinating scheduling paths',4,'2:00','复用：China 9 / EU 10–11。补一个节点范围交接例子；不是迁移运行中的 Pods。')
bullets(s,[('Controller sets desired membership','Express which nodes belong in each desired shard.'),('Coordinators synchronize usage','Reconcile desired and in-use nodes around scheduling cycles.'),('Mode defines the boundary','none: all nodes · soft: preference · hard: restricted scope')],size=20)
panel(s,'CONTROL FLOW — NOT A PHYSICAL TOPOLOGY TREE')
box(s,5.70,2.52,2.65,.75,'Sharding controller');box(s,9.10,2.52,3.14,.75,'NodeShard objects');link(s,8.35,2.90,9.10,2.90)
link(s,10.67,3.27,10.67,3.83)
box(s,5.70,3.83,6.54,.75,'Scheduler coordinators');link(s,8.97,4.58,8.97,5.06)
box(s,5.70,5.06,6.54,.63,'Candidate nodes for the next cycle / session','white',16)
note(s,'2:00。controller 分配候选节点范围；coordinator 协调当前周期正在使用的节点与期望节点。讲一次从 A 向 B 调整一个节点的例子，等相关周期完成再确认交接。none 不分片，soft 可回退到 shard 外，hard 限定范围。NodeShard 不迁移运行中的 Pods；soft 也不代表消除所有跨 scheduler 冲突。',[D+'agent-scheduler.md'])

# 05
s=base('Available Nodes Are Only the Beginning','01 → 02 / The handoff',5,'1:00','新增转场：NodeShard 是候选范围，HyperNode 是物理拓扑；不要画成父子层级。')
txt(s,.65,1.95,11.9,.75,'Enough free resources can still leave a workload unable to run.',26,True)
for x,num,title,body in [(0.67,'01','Complete replicas','Do all required members fit?'),(4.82,'02','Communication locality','Are the nodes in the right domain?'),(8.97,'03','Group relationships','Should instances share a domain?')]:
 rect(s,x,3.12,3.70,2.35,'pale');txt(s,x+.20,3.34,3.25,.45,num,23,True,'blue');txt(s,x+.20,4.02,3.25,.5,title,20,True);txt(s,x+.20,4.65,3.25,.60,body,17,False,'muted')
note(s,'1:00。交接句：So far, we have discussed how scheduling paths coordinate their use of cluster nodes. But a set of available nodes is not enough for a distributed AI workload. We also need complete groups, the right topology, and placement relationships between groups. 不将 NodeShard、HyperNode、SubGroup 画成一棵包含树。')

# 06
s=base('PodGroup and SubGroup: Complete Replicas','02 / Coordinating workload groups',6,'2:30','复用：China 14、22。policy 可以产生多个实际 SubGroups；以下为 P/D 示意，不是完整 API。')
bullets(s,[('PodGroup: overall gang requirements','Describe what the workload needs as a whole.'),('SubGroup: complete member sets','Preserve a replica that spans multiple Pods.'),('Use role and replica identity','Extra Pods in one role cannot fill a missing replica in another.')],size=20)
panel(s,'ILLUSTRATIVE KTHENA PREFILL / DECODE INSTANCE')
rect(s,5.65,2.46,6.72,3.12,'white','line',True);txt(s,5.84,2.65,6.3,.38,'ServingGroup → PodGroup',20,True)
replica(s,5.94,3.35,'Prefill replica','pale',2.2);replica(s,9.65,3.35,'Decode replica','decode',2.2)
txt(s,5.94,4.90,5.99,.43,'SubGroup policies preserve role / replica membership',14,False,'muted')
note(s,'2:30。先用一个总 minMember 满足但必需角色缺失的反例。随后解释两级 gang。一个 subGroupPolicy 能生成多个实际 SubGroups；图中各画一个示意副本，不代表整个 Role 只能有一个 gang。成组调度不等于所有进程同一时刻启动或跨 Pod 原子 bind。',[KT+'gang-scheduling.md'])

# 07
s=base('HyperNode: Expressing Topology Domains','02 / Coordinating workload groups',7,'2:00','复用：China 16。仅保留一棵树；层级名称按现场集群映射，不写固定带宽收益。')
bullets(s,[('Describe nested infrastructure domains','Represent nodes and their topology hierarchy.'),('Choose a placement level','A group can target an appropriate domain size.'),('Express hard or soft constraints','State whether locality is required or preferred.')],size=20)
panel(s)
box(s,8.05,2.40,2.0,.60,'Supernode')
for x in [6.35,9.80]:
 link(s,9.05,3.0,x+1.0,3.68);box(s,x,3.68,2.0,.60,'Rack')
 for xx in [x-.15,x+1.10]:
  link(s,x+1,4.28,xx+.52,5.03);box(s,xx,5.03,1.07,.53,'Node','white',14)
note(s,'2:00。HyperNode 表达拓扑域；图示层级不是所有集群必须采用的物理架构。讲清 hard/soft topology constraint。它与 scheduler sharding mode 的 hard/soft 不是同一个配置，也不代表节点所有权。',[KT+'network-topology.md',R16])

# 08
s=base('Place Groups at Different Topology Levels','02 / Coordinating workload groups',8,'2:00','复用：China 17。延续 P/D 案例；用两层边框区分实例范围和完整副本范围。')
bullets(s,[('One boundary for the instance','Keep the PodGroup inside a larger topology domain.'),('Tighter boundaries for replicas','Place each multi-Pod replica in a smaller domain.'),('Check capacity within the domain','Cluster-wide capacity alone is insufficient.')],size=20)
panel(s,'ILLUSTRATIVE PLACEMENT — NOT AN API OBJECT TREE')
rect(s,5.62,2.43,6.8,3.22,'white','line',True);txt(s,5.80,2.58,6.4,.38,'Supernode A · instance / PodGroup scope',17,True)
for x,label,role,fill in [(5.88,'Rack A1','Prefill replica','pale'),(9.21,'Rack A2','Decode replica','decode')]:
 rect(s,x,3.25,2.94,2.02,'pale','line',True);txt(s,x+.13,3.40,2.7,.3,label,14,True);replica(s,x+.32,3.91,role,fill,2.2)
note(s,'2:00。整个实例限制在较大的 HyperNode 范围，实际 SubGroups 使用较小的范围。这里是放置示意，不是 NodeShard→HyperNode→PodGroup 的 API 包含关系。硬约束下局部域容量不足时，即使全集群资源充足也可能无法放置。',[KT+'network-topology.md'])

# 09
s=base('Keep Instances Together, Place Them Apart','02 / Coordinating workload groups',9,'2:00','新增重点：v1.16 PodGroup anti-affinity。复用 China 15 的构图，更新功能状态。', 'SOURCE  Volcano v1.16  ·  PodGroup anti-affinity #5349')
badge(s,.65,1.88,'AVAILABLE IN v1.16','mint','green',2.1)
txt(s,.65,2.47,4.25,.95,'Locality within.\nSeparation between.',23,True)
txt(s,.65,3.80,4.20,1.55,'Combine PodGroup network topology with anti-affinity across selected PodGroups.',21,False,'muted')
panel(s)
for x,domain,inst in [(5.65,'Supernode A','Instance A'),(9.13,'Supernode B','Instance B')]:
 rect(s,x,2.52,3.18,2.92,'white','line',True);txt(s,x+.14,2.70,2.9,.34,domain,17,True)
 box(s,x+.24,3.36,2.7,.61,inst+' / PG','pale',16)
 pod(s,x+.35,4.40,'Prefill','pale',1.15);pod(s,x+1.67,4.40,'Decode','decode',1.15)
txt(s,5.80,5.68,6.35,.26,'Within-group topology + between-group anti-affinity',12,False,'blue',MONO)
note(s,'2:00。每个实例是一个 PodGroup，内部约束到同一个 supernode，两个 PodGroups 用 anti-affinity 分散。需要启用 plugin；规则选择 PodGroup labels / namespaces，相互分离时双方都应配置规则。主要通过 allocate 执行，不承诺 backfill 的 BestEffort Pods 同样受约束。拓扑分散本身不等于应用 failover。',[AA,'https://github.com/volcano-sh/volcano/pull/5349'])

# 10
s=base('When Placement Rules Cannot Be Satisfied','02 / Coordinating workload groups',10,'1:30','待补：45–60 秒录屏或实际放置截图。当前是预期行为示意，不是测试结果。')
txt(s,.65,1.92,11.9,.58,'Example: only one domain has enough resources.',25,True)
for x,title,fill,result,body in [(.67,'REQUIRED','pale','Keep the second group Pending','Do not violate the separation rule.'),(6.87,'PREFERRED','decode','Allow a feasible fallback','The preference may be relaxed.')]:
 rect(s,x,2.92,5.79,2.80,fill);txt(s,x+.23,3.16,5.30,.33,title,13,True,'blue',MONO);txt(s,x+.23,3.94,5.25,.85,result,24,True);txt(s,x+.23,5.02,5.25,.44,body,18,False,'muted')
note(s,'1:30。隔离测试环境中，其他资源与约束都满足，仅 anti-affinity 无第二个合法域。required 保持 Pending；preferred 可以选择违反偏好的可行放置，并非保证一定放到某节点。若无实测截图，保留 illustrative 标签，不宣称已经运行演示。',[AA])

# 11
s=base('Controllers Bring Workload Structure to Scheduling','03 / Ecosystem progress',11,'2:00','状态截至 2026-10-28；已合并不等于下游稳定版已发布。演讲前核对 PR 和版本。')
cols=[.65,2.57,7.25]; widths=[1.92,4.68,4.80]
headers=['PROJECT','EXISTING / MERGED','NEXT / IN PROGRESS']
for x,w,h in zip(cols,widths,headers):rect(s,x,1.92,w,.51,'navy');txt(s,x+.12,2.04,w-.24,.26,h,12,True,'white')
rows=[('Kthena','Role / replica gang + topology','Reference use cases for group relationships'),('KubeRay','SubGroup support · #5249 merged','Replica topology · #5369 open'),('Grove','Gang / SubGroup backend merged','Topology mapping not yet supported'),('Kubeflow','Existing Volcano integration','Finer TrainJob groups + topology'),('LWS','Existing gang / Volcano integration','Explore roles / slices + group relationships')]
for i,row in enumerate(rows):
 y=2.44+i*.62
 for j,(x,w,st) in enumerate(zip(cols,widths,row)):
  rect(s,x,y,w,.61,'pale' if i%2==0 else 'white');txt(s,x+.12,y+.16,w-.24,.39,st,14 if j else 16,j==0,'navy' if j<2 else 'muted')
txt(s,.72,5.86,11.8,.28,'Controllers supply identity; the scheduler applies group and placement constraints.',18,True,'blue')
note(s,'2:00。Kthena 已有 gang/topology。KubeRay #5249 已合并，#5369 截至核查仍 open。Grove #516 最终实现包含 SubGroupPolicy，但显式拒绝 topology constraints。Kubeflow / LWS 不是从零集成，后续深化分组与拓扑。各条既有能力不都意味着同等支持两级 gang 或 topology。',[KT+'gang-scheduling.md',KT+'network-topology.md',RAY+'5249',RAY+'5369',GROVE,'https://trainer.kubeflow.org/en/latest/operator-guides/job-scheduling/volcano.html','https://github.com/kubernetes-sigs/lws/pull/498'])

# 12
s=base('KubeRay: A Replica Can Span Multiple Pods','03 / Ecosystem progress',12,'1:00','新增案例：WorkerGroup / policy / 实际 replica 不混为一谈；省略 head，仅聚焦一个 worker group。')
txt(s,.65,1.94,4.2,.60,'minReplicas = 2\nnumOfHosts = 2',22,True,'blue',MONO)
txt(s,.65,3.28,4.2,1.40,'The requirement is two complete replicas, each spanning two Pods.',24,True)
txt(s,.65,5.05,4.2,.65,'Any four Pods are not enough.',19,False,'muted')
panel(s)
replica(s,5.90,2.85,'Replica 0 → SubGroup','pale',2.2);replica(s,9.63,2.85,'Replica 1 → SubGroup','pale',2.2)
box(s,5.90,4.43,5.93,.70,'2 complete replicas × 2 hosts','white',22)
badge(s,5.90,5.47,'GANG: MERGED','mint','green',2.42);badge(s,8.52,5.47,'TOPOLOGY: IN PROGRESS','yellow','amber',3.19)
note(s,'1:00。仅讨论一个 worker group，忽略 head 等其他需求。minReplicas=2,numOfHosts=2，需要两套完整 replica identity，每套两个 Pods。三个来自 replica 0、一个来自 replica 1 并不满足。一个 WorkerGroup / subgroup policy 能生成多个实际 SubGroups。',[RAY+'5249',RAY+'5369'])

# 13
s=base('HyperNode Beyond a Single Scheduler','03 / Ecosystem progress',13,'1:00','复用：China 19。独立 controller 更新为已交付；外部 scheduler adapter 单独标状态。')
bullets(s,[('Standalone discovery and controller','Topology can be maintained as a reusable component.'),('A shared topology API','Consumers read the HyperNode model.'),('Adapters remain separate work','API availability does not imply every scheduler is integrated.')],size=20)
panel(s)
box(s,6.30,2.52,5.35,.70,'Discovery / standalone controller');link(s,8.97,3.22,8.97,3.77)
box(s,6.30,3.77,5.35,.70,'HyperNode API');link(s,8.97,4.47,7.22,5.03);link(s,8.97,4.47,10.82,5.03)
box(s,5.70,5.03,3.02,.60,'Volcano','white',17);box(s,9.32,5.03,3.02,.60,'Other consumers*','white',17)
txt(s,6.00,5.78,6.15,.23,'*Scheduler adapters: planned / separate integrations',11,False,'muted',MONO)
note(s,'1:00。standalone HyperNode controller 已在 v1.16 交付。外部消费者可使用 API，但 kube-scheduler / coscheduling 等 adapter 仍要单独实现，不能画成全部已经支持。',[R16,R17])

# 14
s=base('Next: Relationships Between SubGroups','04 / What comes next',14,'2:00','未来方向：同一 PodGroup 内的 SubGroup 关系。以下只说明需求，不代表已发布字段。')
badge(s,.65,1.88,'PROPOSED','lav','purple',1.65)
txt(s,.65,2.52,4.20,1.06,'Beyond a boundary\nfor each group.',26,True)
txt(s,.65,3.88,4.20,1.70,'Express which SubGroups should be near each other, and which should be spread across domains.',21,False,'muted')
panel(s,'SAME PODGROUP — TWO SEPARATE SCENARIOS')
for yy,label in [(2.48,'AFFINITY: share a target domain'),(4.25,'ANTI-AFFINITY: use different domains')]:
 txt(s,5.66,yy,6.65,.33,label,14,True,'purple')
if True:
 rect(s,5.75,3.00,6.4,.88,'lav','line',True);box(s,6.0,3.18,2.5,.48,'SubGroup A','white',14);box(s,9.4,3.18,2.5,.48,'SubGroup B','white',14)
 for xx,lab in [(5.75,'SubGroup A'),(9.2,'SubGroup B')]:
  rect(s,xx,4.80,2.95,.88,'lav','line',True);box(s,xx+.20,4.98,2.55,.48,lab,'white',14)
note(s,'2:00。回到同一个 PodGroup 内部的关系需求，与前面两个 PodGroups 的 anti-affinity 区分。需明确作用层级、匹配实际副本的方法以及 required/preferred 语义。图是两个独立场景，不表示同一对组同时要求共置与分离。',[D+'group-topology-affinity.md','https://github.com/volcano-sh/volcano/issues/5347',R17])

# 15
s=base('From Placement Primitives to Ecosystem Adoption','04 / What comes next',15,'1:30','路线建议：与实际投入对齐；不承诺这页所有事项都在 v1.17 一次交付。')
for x,num,title,body in [(.65,'01','Define relationships','SubGroup affinity / anti-affinity\nClear matching and failure semantics'),(4.83,'02','Preserve workload intent','Deepen KubeRay / Grove mappings\nExtend Kubeflow / LWS integration'),(9.01,'03','Validate real scenarios','Runnable examples\nPlacement and failure behavior')]:
 rect(s,x,2.02,3.65,3.33,'pale');txt(s,x+.18,2.21,3.25,.44,num,23,True,'blue');txt(s,x+.18,2.95,3.25,.81,title,22,True);txt(s,x+.18,4.08,3.25,1.00,body,17,False,'muted')
txt(s,.72,5.72,11.8,.38,'Further out: topology adapters and device / network locality.',18,False,'muted')
note(s,'1:30。近期主线：关系语义、controller 映射、真实场景验证。Kthena 继续作为参考场景；KubeRay / Grove 深化；Kubeflow / LWS 在已有集成上拓展。xPU / DRA / GPU-NIC locality 为中期方向，不把整个路线图照搬到正文。',[R17])

# 16
s=base('One Framework, Workload-Aware Placement','04 / What comes next',16,'1:30','可用 20–30 秒提及 Global / 混部已有能力；正文收回到当前推进方向与社区参与。')
for yy,no,head,sub in [(1.95,'01','Coordinate scheduling paths','NodeShard and scheduler coordination'),(3.23,'02','Preserve workload structure','Complete groups, topology, and placement relationships'),(4.51,'03','Bring the semantics into controllers','Share use cases and help build integrations')]:
 badge(s,.68,yy+.06,no,'pale','blue',.58);txt(s,1.55,yy,10.8,.45,head,25,True);txt(s,1.55,yy+.56,10.8,.43,sub,19,False,'muted')
txt(s,.70,6.00,11.8,.30,'github.com/volcano-sh/volcano  ·  v1.17 roadmap: issue #6166',15,False,'blue')
note(s,'1:30。总结：框架协调、工作负载结构、生态采用。邀请大家带来角色、副本和互联需求，参与 controller 集成与关系语义讨论。若需呼应摘要，可简述项目仍有 Global / 混部已有覆盖，但不宣称新的推进成果。',[R17,'https://github.com/volcano-sh/volcano'])

# 17
s=base('Questions?','Discussion',17,'5:00','备份材料：NodeShard 模式、关键 API、plugin 开关、生态版本与来源；正式版移除此提示。')
txt(s,.70,2.05,11.8,.64,'What should your workload keep together—or place apart?',28,True)
box(s,.75,3.55,5.45,1.16,'Scheduling paths\nNodeShard coordination','pale',24)
box(s,7.13,3.55,5.45,1.16,'Workload groups\nGang + topology + relationships','pale',24)
txt(s,.75,5.48,11.8,.46,'github.com/volcano-sh/volcano',24,False,'blue')
note(s,'5:00。问答准备：NodeShard 和 HyperNode 的区别；hard shard 切开拓扑域的取舍；Gang 不等于进程同时启动；PodGroup anti-affinity 的 allocate 范围；SubGroup 关系尚未发布；生态 PR 合并与发行版本的区别。',[D+'agent-scheduler.md',AA,R17])

prs.core_properties.title='Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents'
prs.core_properties.subject='KubeCon NA 2026 Maintainer Track — editable content draft'
prs.core_properties.author='Volcano presentation working draft'
prs.core_properties.comments='English slide content; Chinese production notes. Status checked 2026-10-28. Illustrative diagrams, not measured results.'
for slide in prs.slides:
 for effect in slide._element.xpath('.//a:effectRef'):
  effect.set('idx','0')
out=OUT/'Volcano_KubeCon_NA_2026_draft.pptx';prs.save(out)
# Check every shape lies inside its slide (text clipping is reviewed after PDF rendering).
for idx,sl in enumerate(prs.slides,1):
 for sh in sl.shapes:
  assert sh.left>=0 and sh.top>=0 and sh.left+sh.width<=prs.slide_width+100 and sh.top+sh.height<=prs.slide_height+100,(idx,sh.name)
assert len(prs.slides)==17
print(out)
