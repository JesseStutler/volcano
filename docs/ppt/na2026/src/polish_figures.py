"""Technical figure compositions for the NA talk.

Use containment for membership, aligned lanes for process, and event markers for
measurement. Connectors are orthogonal and terminate at explicit ports. Source
China/EU figures are deliberately left intact by this module.
"""
from html import escape


def polish(arts, art, code, raw, C, assets):
    def renew(n):
        a = type(arts[n])(arts[n].name)
        arts[n] = a
        return a

    def wire(a, points, c='line', arrow=True, dash=False):
        assert all(x1 == x2 or y1 == y2 for (x1,y1),(x2,y2) in zip(points,points[1:])), points
        a.path(points, arrow, c, dash)

    def dot(a,x,y,label,color='blue',r=17):
        a.front.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{C.get(color,color)}"/>')
        a.text(x,y+7,str(label),21,'white',True,70,'middle')

    def bar(a,x,y,w,label,color='ink',size=23):
        a.rect(x,y,w,44,color,None,0)
        a.text(x+17,y+30,label,size,'white',True,width=w-34)

    def frame(a,x,y,w,h,title,color='blue',fill='white'):
        a.rect(x,y,w,h,fill,color,3,layer='bg')
        bar(a,x,y,w,title,color)

    def foot(a,text):
        a.rect(0,511,1480,49,'ink',None,0)
        a.rect(0,511,6,49,'orange',None,0)
        a.text(22,545,text,26,'white',True,width=1430)

    def icon(a,x,y,size,name='pod'):
        a.image(x,y,size,size,assets/'icons'/f'{name}.svg')

    def pod(a,x,y,label,w=145,color='blue',size=22):
        a.rect(x,y,w,66,'white',color,3)
        icon(a,x+10,y+11,42)
        a.text(x+61,y+42,label,size,'ink',True,width=w-70)

    def server(a,x,y,w,name,labels,color='blue'):
        # A node chassis contains actual pod units rather than generic role boxes.
        a.rect(x,y,w,128,'#f2f5f9','line',3)
        a.text(x+15,y+27,name,22,'muted',True,width=w-55)
        for j in range(3):
            a.rect(x+w-43+j*9,y+15,5,5,color,None,0)
        pw=(w-34)/2
        for j,label in enumerate(labels):pod(a,x+12+j*(pw+10),y+46,label,pw,color,20)

    def bundle(a,x,y,w,h,label,color='blue',pods=('Pod 0','Pod 1')):
        frame(a,x,y,w,h,label,color,'white')
        pw=(w-46)/2
        for j,label in enumerate(pods):pod(a,x+15+j*(pw+16),y+69,label,pw,color,21)

    # 04: workload demands as distinct workload shapes on a common foundation.
    a=renew(4)
    for y in [0,161,322]:
        a.rect(0,y,1480,145,'white',None,0,layer='bg')
        wire(a,[(0,y+145),(1480,y+145)],arrow=False,c='light')
    for y,title,desc in [(0,'Training & RL','Coordinated compute'),(161,'Inference','Roles and complete replicas'),(322,'Agent applications','Bursty, latency-sensitive requests')]:
        a.text(0,y+39,title,32,'ink',True,width=340)
        a.text(0,y+81,desc,25,'muted',width=335)
    # Training: one gang boundary, four member Pods.
    a.rect(390,12,620,111,'pale','blue',2,layer='bg',dash=True)
    for i in range(4):pod(a,410+i*149,34,f'W{i}',130,'blue',23)
    a.text(1060,48,'Start a complete group',29,'blue',True,width=400)
    a.text(1060,92,'Resources + coordination',24,'muted',width=400)
    # Serving: two explicit role groups; containment carries membership.
    for x,label,color in [(390,'Prefill','green'),(720,'Decode','blue')]:
        a.rect(x,176,290,113,'white',color,2,layer='bg')
        a.text(x+16,205,label,23,color,True,width=260)
        icon(a,x+22,224,47);icon(a,x+94,224,47)
        a.text(x+166,254,'replica',23,'muted',width=110)
    a.text(1060,210,'Keep communication local',29,'blue',True,width=410)
    a.text(1060,254,'Roles + topology',24,'muted',width=400)
    # Requests are small events, not Pod symbols.
    for i,x in enumerate([408,444,480,553,589,625]):
        a.front.append(f'<circle cx="{x}" cy="393" r="10" fill="{C["orange"]}"/>')
    a.text(397,437,'request bursts',22,'muted',width=260)
    a.rect(764,350,246,94,'pale','line',3)
    icon(a,783,365,53,'svc');a.text(850,386,'Serving /',24,'ink',True,width=145);a.text(850,416,'sandbox',24,'ink',True,width=145)
    wire(a,[(646,393),(761,393)])
    a.text(1060,370,'Respond to bursts',29,'blue',True,width=400)
    a.text(1060,414,'Runtime determines the unit',24,'muted',width=410)
    foot(a,'Shared cluster capacity; different requirements for coordination, locality, and latency.')

    # 11: placement is visible on node chassis; each service instance has a boundary.
    a=renew(11)
    for y,domain,instance,color in [(0,'Supernode A','instance-a','blue'),(250,'Supernode B','instance-b','green')]:
        frame(a,0,y,690,223,domain,'ink')
        a.rect(14,y+58,662,150,'white',color,3,layer='bg',dash=True)
        a.text(27,y+85,instance+' · PodGroup',24,color,True,width=600)
        # Short host strips keep the boundary legible without pretending Pods are nodes.
        for x,node_name,labels in [(28,'Node '+domain[-1]+'0',['P0','D0']),(359,'Node '+domain[-1]+'1',['P1','D1'])]:
            a.rect(x,y+98,301,94,'pale','line',2)
            a.text(x+12,y+124,node_name,20,'muted',True,width=275)
            for j,t in enumerate(labels):
                icon(a,x+12+j*148,y+137,39)
                a.text(x+59+j*148,y+165,t,22,color,True,width=90)
    code(a,740,0,740,475,'PodGroup · same rule on each instance','''metadata:
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
        topologyTierName: supernode''',25,('highestTierName','podGroupAntiAffinity','topologyTierName'),filename='podgroup-anti-affinity.yaml')
    foot(a,'Inside an instance: locality. Between instances: separation. PodGroup anti-affinity is available in v1.16.')

    # 13: inspect controller inputs and the grouping model they convey, not a logo hub.
    a=renew(13)
    a.text(0,29,'CONTROLLER INPUTS',22,'muted',True)
    projects=[(65,'Kthena','kthena.svg','ModelServing / role replicas','Gang + topology available','green'),
              (203,'KubeRay','kuberay.png','RayCluster / multi-host replicas','SubGroup merged · topology in progress','blue'),
              (341,'Grove','dynamo-grove.svg','PodCliqueSet / scaling groups','SubGroup backend · topology mapping open','blue')]
    for y,title,logo,resource,status,color in projects:
        a.image(0,y,62,53,assets/logo)
        a.text(83,y+31,title,30,'ink',True,width=420)
        a.text(83,y+70,resource,25,'ink',width=580)
        a.text(83,y+107,status,23,color,True,width=595)
    # A labeled translation boundary, no many-to-one decorative arrows.
    wire(a,[(700,50),(700,469)],arrow=False,c='light')
    a.text(785,29,'VOLCANO GROUPING MODEL',22,'muted',True)
    frame(a,785,59,695,408,'PodGroup · workload admission','ink')
    a.text(810,143,'Select role',25,'ink',True,width=270)
    raw(a,1080,143,'labelSelector',24,'blue',False,True)
    a.text(810,191,'Partition replicas',25,'ink',True,width=280)
    raw(a,1080,191,'matchLabelKeys',24,'blue',False,True)
    wire(a,[(810,216),(1454,216)],arrow=False,c='light')
    bundle(a,810,240,303,143,'SubGroup 0','blue',('0','1'))
    bundle(a,1151,240,303,143,'SubGroup 1','green',('0','1'))
    a.text(810,435,'Topology constraints are a separate integration step.',23,'muted',width=640)
    foot(a,'Kubeflow Trainer and LWS already integrate with Volcano; finer groups and locality are next.')

    # 15: show the replica label on actual member Pods and align it with API fields.
    a=renew(15)
    (assets.parent/'examples'/'ray-worker-group.yaml').write_text('minReplicas: 2\nnumOfHosts: 2\n')
    frame(a,0,0,700,475,'WorkerGroup · 2 replicas × 2 hosts','ink')
    a.text(20,85,'Each replica is one complete SubGroup.',25,'muted',width=655)
    for x,r,color in [(20,'0','blue'),(365,'1','green')]:
        frame(a,x,115,315,280,'Replica '+r,color)
        for y,host in [(183,'0'),(282,'1')]:
            pod(a,x+16,y,'host '+host,283,color,25)
            a.text(x+20,y+91,'replica-name = '+r,21,color,True,width=275)
    a.text(20,441,'Same replica label → same SubGroup',25,'ink',True,width=660)
    code(a,750,0,730,372,'PodGroup.spec · generated grouping','''subGroupPolicy:
- name: worker
  labelSelector:
    matchLabels: {ray.io/group: worker}
  matchLabelKeys:
  - ray.io/worker-group-replica-name
  minSubGroups: 2
  subGroupSize: 2''',25,('matchLabelKeys','minSubGroups','subGroupSize'),filename='ray-subgroup-spec.yaml')
    dot(a,770,419,'1');a.text(800,428,'Partition by the replica label',27,'ink',True,width=660)
    dot(a,770,464,'2','green');a.text(800,473,'Require two complete, two-Pod groups',25,'ink',True,width=660)
    foot(a,'Gang support is merged. Replica topology is in progress. The head has its own group.')

    # 16: two different topology intents, not a single ambiguous near/apart arrow.
    a=renew(16)
    a.text(0,29,'PROPOSED · SubGroup relationships within one PodGroup',23,'purple',True,width=1450)
    for x,num,title,subtitle in [(0,'01','Affinity','Cooperating groups share a domain'),(780,'02','Anti-affinity','Replicas occupy different domains')]:
        dot(a,x+18,78,num,'purple',18)
        a.text(x+55,89,title,32,'ink',True,width=620)
        a.text(x,135,subtitle,25,'muted',width=680)
    # Affinity: one supernode, two groups, same frame. No claim of replica-index pairing.
    frame(a,0,170,700,260,'Supernode A','ink')
    bundle(a,20,240,315,155,'Prefill SubGroup','green',('P0','P1'))
    bundle(a,365,240,315,155,'Decode SubGroup','blue',('D0','D1'))
    a.text(20,475,'One shared topology boundary',26,'ink',True,width=660)
    # Anti-affinity: two separate racks within the current workload.
    for x,label,r in [(780,'Rack A','Replica 0'),(1145,'Rack B','Replica 1')]:
        frame(a,x,170,335,260,label,'ink')
        bundle(a,x+17,240,301,155,r,'blue',('P0','P1'))
    a.text(800,475,'Distinct topology boundaries',26,'ink',True,width=650)
    foot(a,'Two placement intents, shown separately. SubGroup affinity / anti-affinity remains proposed.')

    # 18: an instrumented cluster, with execution and observation kept on separate lanes.
    a=renew(18)
    a.text(0,29,'SCENARIO',22,'muted',True)
    a.text(442,29,'CLUSTER UNDER TEST',22,'muted',True)
    a.text(1135,29,'OBSERVATION',22,'muted',True)
    # Input document: enough real configuration to explain what the harness changes.
    frame(a,0,60,330,415,'benchmark/','ink')
    icon(a,20,124,60,'job');a.text(94,162,'Gang / Pod profiles',25,'ink',True,width=215)
    raw(a,20,230,'JOBS',25,'blue',True,True);raw(a,20,272,'REPLICAS',25,'blue',True,True);raw(a,20,314,'MIN_AVAILABLE',25,'blue',True,True)
    wire(a,[(20,346),(307,346)],arrow=False,c='light')
    a.text(20,389,'Version + resources',24,'muted',width=290)
    a.text(20,432,'Optional topology',24,'muted',width=290)
    # Cluster boundary and real scheduler / API landmarks.
    a.rect(430,60,605,415,'pale','line',4,layer='bg')
    a.rect(462,90,540,94,'white','line',3)
    icon(a,480,111,52,'api');a.text(551,128,'Kubernetes API',28,'ink',True,width=420)
    a.text(551,163,'Pods · PodGroups · HyperNodes',22,'muted',width=420)
    a.rect(462,286,540,92,'white','blue',3)
    a.image(481,308,78,44,assets/'volcano-icon.svg');a.text(584,341,'Volcano scheduler',29,'ink',True,width=390)
    a.text(462,433,'Kind + KWOK  /  existing cluster',25,'ink',True,width=540)
    # Opposite directions use separate vertical lanes and never share labels.
    wire(a,[(330,137),(459,137)]);a.text(346,119,'create',21,'muted',width=85)
    wire(a,[(585,185),(585,282)],'blue');a.text(482,243,'watch',22,'blue',True,width=100)
    wire(a,[(887,283),(887,187)],'blue');a.text(907,243,'bind',22,'blue',True,width=90)
    # Observation: audit event feed, metric collection, and the report artifact.
    for y,title,sub in [(90,'Audit log','create / bind events'),(286,'Prometheus','audit-exporter + metrics'),(415,'Report / Grafana','P50 / P90 / P99 · throughput')]:
        h=94 if y<415 else 60
        a.rect(1130,y,350,h,'white','line',3)
        a.text(1148,y+33,title,27,'ink',True,width=315)
        if y<415:a.text(1148,y+70,sub,22,'muted',width=315)
    wire(a,[(1003,137),(1127,137)])
    wire(a,[(1400,185),(1400,282)],'green');a.text(1150,242,'audit-exporter',22,'green',True,width=245)
    wire(a,[(1003,332),(1127,332)],'green');a.text(1039,315,'metrics',20,'green',True,width=85)
    wire(a,[(1400,381),(1400,411)],'green')
    foot(a,'The harness controls the scenario and records observations; KWOK does not execute GPU work.')

    # 19: actual commands plus experiment controls, not a second architecture diagram.
    a=renew(19)
    code(a,0,0,765,320,'RUN A SCENARIO · benchmark/','''make setup

make test-gang-env \\
  JOBS=10 REPLICAS=100 \\
  MIN_AVAILABLE=100''',29,('JOBS=','MIN_AVAILABLE'))
    a.text(0,370,'COLLECT THE EVIDENCE',22,'muted',True)
    raw(a,0,414,'logs/kube-apiserver-audit.log',25,'ink',False,True)
    raw(a,0,456,'results/report-<timestamp>.json',25,'ink',False,True)
    a.text(840,31,'ONGOING VALIDATION',22,'purple',True,width=600)
    for y,num,title,desc in [(85,'01','Vary one dimension','Workload size, grouping, or topology.'),(224,'02','Keep the comparison fixed','Version, resources, and metric definitions.'),(363,'03','Repeat and inspect','Retain raw events; investigate bottlenecks.')]:
        dot(a,858,y+9,num,'blue',18)
        a.text(897,y+20,title,29,'ink',True,width=570)
        a.text(897,y+65,desc,25,'muted',width=565)
        if y<363:wire(a,[(840,y+107),(1480,y+107)],arrow=False,c='light')
    foot(a,'Available: scenario setup, Gang / Pod workloads, topology, metrics, and report collection.')

    # 20: event timelines explain the metric, without inventing a performance curve.
    a=renew(20)
    a.text(0,29,'MEASUREMENT DEFINITIONS · schematic, not benchmark results',22,'muted',True,width=1470)
    # Latency event line.
    a.text(0,104,'Per-Pod latency',31,'ink',True,width=330)
    a.text(0,150,'Created → scheduled',25,'blue',True,width=330)
    wire(a,[(405,150),(1445,150)],'line')
    for x,label,color in [(440,'created','blue'),(1000,'scheduled','blue'),(1370,'ready','muted')]:
        a.front.append(f'<circle cx="{x}" cy="150" r="8" fill="{C[color]}"/>')
        a.text(x,111,label,25,color,True,200,'middle')
    wire(a,[(440,167),(440,208),(1000,208),(1000,167)],'blue',False)
    a.text(720,248,'scheduling latency',28,'blue',True,530,'middle')
    a.text(1190,208,'runtime / application',22,'muted',False,360,'middle')
    # Throughput line uses first/last successful bind events, matching collect-report.sh.
    wire(a,[(0,285),(1480,285)],arrow=False,c='light')
    a.text(0,359,'Scheduling throughput',29,'ink',True,width=370)
    a.text(0,405,'Successful binds / window',24,'green',True,width=365)
    wire(a,[(405,385),(1445,385)],'line')
    for x in [440,605,690,810,1085,1370]:
        wire(a,[(x,370),(x,400)],'green',False)
        a.front.append(f'<circle cx="{x}" cy="385" r="5" fill="{C["green"]}"/>')
    a.text(440,345,'first bind',24,'green',True,220,'middle')
    a.text(1370,345,'last bind',24,'green',True,220,'middle')
    wire(a,[(440,414),(440,444),(1370,444),(1370,414)],'green',False)
    a.text(905,484,'successful binding-event window',25,'green',True,900,'middle')
    foot(a,'Compare latency distributions and throughput with the same version, workload, resources, and window.')

    # 21: confident typography rather than another box-and-arrow drawing.
    a=renew(21)
    rows=[('01','Coordinate the paths','NodeShard + scheduler coordination','blue'),
          ('02','Preserve workload structure','Complete groups + topology + separation','green'),
          ('03','Carry intent through controllers','Roles and replica identity reach scheduling','blue'),
          ('04','Measure and keep improving','Repeatable scenarios + comparable observations','purple')]
    for i,(num,title,detail,color) in enumerate(rows):
        y=i*127
        a.text(0,y+53,num,40,color,True,width=90)
        a.text(115,y+53,title,35,'ink',True,width=1320)
        a.text(115,y+98,detail,28,'muted',width=1320)
        if i<3:wire(a,[(115,y+119),(1480,y+119)],arrow=False,c='light')
    # Discussion page is a typographic close, not a diagram.
    a=renew(22)
    a.text(0,103,'What must run together?',48,'ink',True,width=1460)
    a.text(0,183,'What should stay apart?',48,'blue',True,width=1460)
    wire(a,[(0,264),(1480,264)],arrow=False,c='line')
    a.text(0,354,'Bring a workload, a topology constraint, or a reproducible test.',30,'ink',width=1470)
    a.text(0,454,'github.com/volcano-sh/volcano',34,'blue',True,width=1460)
    a.text(0,515,'Roadmap and feedback · issue #6166',25,'muted',width=1460)
