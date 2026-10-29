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
        a.rect(x,y,w,44,'white',None,0)
        a.path([(x,y+44),(x+w,y+44)],False,color)
        a.text(x+17,y+30,label,size,color,True,width=w-34)

    def frame(a,x,y,w,h,title,color='blue',fill='white'):
        a.rect(x,y,w,h,fill,color,3,layer='bg')
        bar(a,x,y,w,title,color)

    def foot(a,text):
        wire(a,[(0,511),(1480,511)],arrow=False,c='light')
        a.text(0,549,text,25,'ink',True,width=1478)

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

    # Physical symbols follow the EU/China multi-level topology figure.
    # A switch is hardware; a dashed contour is a scheduling group.
    def switch(a,x,y,label,w=104):
        top=26; depth=19; height=27
        points=[(x,y+top),(x+depth,y),(x+w,y),(x+w-depth,y+top)]
        a.front.append('<polygon points="'+' '.join(f'{px},{py}' for px,py in points)+'" fill="#08749d" stroke="white" stroke-width="2.5"/>')
        a.front.append(f'<path d="M{x},{y+top} h{w-depth} v{height} h-{w-depth} Z M{x+w-depth},{y+top} l{depth},-{top} v{height} l-{depth},{top} Z" fill="#075e87" stroke="white" stroke-width="2.5"/>')
        # Two opposed port-direction marks, explicitly anchored to the top face.
        a.front.append(f'<path d="M{x+31},{y+9} h40 l-6,-3 m6,3 l-8,3 M{x+64},{y+19} h-40 l6,3 m-6,-3 l8,-3" fill="none" stroke="white" stroke-width="2"/>')
        if label:a.text(x+w/2,y-9,label,23,'ink',True,width=w+90,anchor='middle')
        return (x+w/2,y),(x+(w-depth)/2,y+top+height)

    def rack(a,x,y,w,title,roles,color='blue',h=157):
        # Explicit node chassis and named Pod rows; no implied GPU count.
        a.rect(x,y,w,h,'#f5f7fa','line',1)
        a.front.append(f'<path d="M{x+w},{y} l9,-7 v{h} l-9,7" fill="#dce5ee" stroke="{C["line"]}" stroke-width="1.4"/>')
        a.text(x+w/2,y+26,title,21,'ink',True,width=w-8,anchor='middle')
        rh=(h-48)/len(roles)
        for i,label in enumerate(roles):
            yy=y+37+i*rh
            a.rect(x+9,yy,w-18,rh-8,'prefill' if color=='blue' else 'mint',color,4)
            a.text(x+w/2,yy+25,label,21,color,True,width=w-24,anchor='middle')
            if rh>=70:
                a.text(x+w/2,yy+55,'Pod',19,'muted',width=w-24,anchor='middle')
        return (x+w/2,y-4)

    def scope(a,x,y,w,h,label,color='blue',fill='white'):
        a.rect(x,y,w,h,fill,color,22,layer='bg',dash=True)
        a.text(x+18,y+32,label,24,color,True,width=w-36)

    def service(a,x,y,w,label,sub=None,color='blue',h=66):
        # A named runtime component, not a Kubernetes Pod symbol.
        a.rect(x,y,w,h,'white',color,8)
        a.text(x+w/2,y+(29 if sub else 40),label,25,'ink',True,width=w-20,anchor='middle')
        if sub:a.text(x+w/2,y+54,sub,21,'muted',width=w-20,anchor='middle')

    # 04: asymmetric composition. Distributed compute, a request graph, and
    # disaggregated serving have different shapes because they behave differently.
    a=renew(4)
    a.text(0,28,'TRAINING & RL',24,'blue',True)
    a.text(0,64,'Complete compute groups; collective communication',24,'muted',width=510)
    scope(a,0,112,515,370,'One training gang','blue')
    st,sb=switch(a,206,190,'Collective fabric')
    # Two nodes / four ranks form a real compute group; a labeled bus shows all-reduce.
    for x,title,roles in [(35,'GPU node A',['rank 0','rank 1']),(294,'GPU node B',['rank 2','rank 3'])]:
        rp=rack(a,x,299,177,title,roles,h=158)
        wire(a,[sb,(sb[0],271),(rp[0],271),rp],arrow=False)
    a.text(256,286,'all-reduce',21,'blue',True,width=150,anchor='middle')
    a.text(610,28,'AGENT APPLICATION',24,'orange',True)
    a.text(610,64,'Variable fan-out; latency-sensitive runtime calls',24,'muted',width=850)
    service(a,617,105,190,'Planner',color='orange',h=70)
    service(a,927,105,205,'Retrieval', 'tool service',color='orange',h=70)
    service(a,1235,105,230,'Sandbox','runtime session',color='orange',h=70)
    wire(a,[(807,139),(924,139)],'orange')
    wire(a,[(712,105),(712,88),(1350,88),(1350,102)],'orange')
    a.text(846,122,'tool',20,'orange',width=70)
    # Model calls branch downward from the planner, rather than becoming Pods.
    wire(a,[(710,175),(710,194),(572,194),(572,377),(614,377)],'orange')
    a.text(726,220,'model calls',21,'orange',True,width=180)
    a.text(935,219,'Requests reuse services and runtimes.',23,'muted',width=530)
    a.text(610,277,'INFERENCE',24,'green',True)
    a.text(610,310,'Long-lived roles; local KV transfer; complete replicas',24,'muted',width=865)
    service(a,617,341,190,'Router',color='green',h=73)
    scope(a,888,339,577,143,'Serving instance','green')
    service(a,908,390,200,'Prefill','prompt compute',color='green',h=70)
    service(a,1243,390,200,'Decode','token generation',color='blue',h=70)
    wire(a,[(807,377),(859,377),(859,425),(905,425)],'green')
    wire(a,[(1108,425),(1240,425)],'green')
    a.text(1175,409,'KV',21,'green',True,width=90,anchor='middle')
    a.text(1175,456,'transfer',20,'muted',width=110,anchor='middle')
    foot(a,'Shared Kubernetes capacity · compute groups, serving replicas, and runtime demand are different scheduling concerns.')

    # 11: network hierarchy and concrete placement, with no abstract apart-arrow.
    a=renew(11)
    ct,cb=switch(a,295,35,'Shared fabric')
    a.text(435,31,'P: Prefill · D: Decode',23,'muted',width=265)
    for x,domain,instance,color in [(0,'Supernode A','instance-a','blue'),(365,'Supernode B','instance-b','green')]:
        scope(a,x,155,325,327,domain,color)
        st,sb=switch(a,x+110,212,'')
        wire(a,[cb,(cb[0],107),(x+270,107),(x+270,200),(st[0],200),st],arrow=False)
        for xx,title,roles in [(x+18,'Node 0',['P0','P1']),(x+175,'Node 1',['D0','D1'])]:
            rp=rack(a,xx,304,128,title,roles,color,h=122)
            wire(a,[sb,(sb[0],283),(rp[0],283),rp],arrow=False)
        a.text(x+163,463,instance+' · PodGroup',22,color,True,width=305,anchor='middle')
    code(a,740,0,740,482,'PodGroup · same rule on each instance','''metadata:
  labels:
    app: model-a
spec:
  networkTopology:
    mode: hard
    highestTierName: supernode
  topologyAffinity:
    podGroupAntiAffinity:
      required:
      - podGroupSelector:
          matchLabels:
            app: model-a
        topologyTierName: supernode''',24,('highestTierName','podGroupAntiAffinity','topologyTierName'),filename='podgroup-anti-affinity.yaml')
    foot(a,'Locality keeps each instance within one domain; anti-affinity places matching PodGroups in different domains.')

    # 13: community-specific next steps; no generic hub or placeholder grouping art.
    a=renew(13)
    a.text(0,29,'INTEGRATIONS & CURRENT GAPS',23,'blue',True)
    a.text(790,29,'NEXT COMMUNITY WORK',23,'purple',True)
    wire(a,[(730,12),(730,480)],arrow=False,c='light')
    projects=[(64,'Kthena','kthena.svg','ModelServing → role replicas','Gang and topology available.'),
              (210,'KubeRay','kuberay.png','Multi-host replica → SubGroup','Gang merged; topology in progress.'),
              (356,'Grove','dynamo-grove.svg','PodClique / scaling group → SubGroup','Backend merged; topology mapping remains.')]
    for y,title,logo,mapping,status in projects:
        a.image(0,y,64,48,assets/logo)
        a.text(85,y+31,title,30,'ink',True,width=575)
        a.text(85,y+72,mapping,24,'ink',width=590)
        a.text(85,y+109,status,23,'muted',width=600)
        if y<356:wire(a,[(85,y+132),(688,y+132)],arrow=False,c='light')
    for y,title,status,line1,line2 in [
        (64,'RBG','IN PROGRESS','RoleInstance → SubGroup foundation.','Continue the integration with the community.'),
        (210,'Kubeflow','PLANNED','Build on the existing Volcano plugin.','Extend finer grouping and topology support.'),
        (356,'LWS','PLANNED · MULTI-GROUP','Build on existing gang scheduling.','Connect multi-role groups to scheduling intent.')]:
        a.text(790,y+31,title,30,'ink',True,width=240)
        a.text(1040,y+29,status,21,'purple',True,width=438)
        a.text(790,y+72,line1,24,'ink',width=680)
        a.text(790,y+109,line2,23,'muted',width=680)
        if y<356:wire(a,[(790,y+132),(1480,y+132)],arrow=False,c='light')
    foot(a,'The next integration step: preserve roles, replica identity, and locality across controller boundaries.')

    # 15: each multi-host replica is an explicit pair of worker Pods.
    # No shared switch here: merged gang support does not yet guarantee topology.
    a=renew(15)
    (assets.parent/'examples'/'ray-worker-group.yaml').write_text('minReplicas: 2\nnumOfHosts: 2\n')
    a.text(0,29,'RayCluster · worker group',28,'ink',True,width=680)
    raw(a,0,71,'minReplicas: 2',26,'blue',False,True)
    raw(a,0,104,'numOfHosts: 2',26,'blue',False,True)
    service(a,235,103,225,'Ray head','separate group',h=70)
    for x,r,color in [(0,'0','blue'),(365,'1','green')]:
        scope(a,x,235,325,211,'SubGroup · replica '+r,color)
        for xx,host in [(x+18,'0'),(x+175,'1')]:
            rack(a,xx,296,128,'host '+host,['worker'],color,h=120)
        # Head-to-worker RPC: common bus, no topology placement meaning.
        wire(a,[(348,173),(348,205),(x+162,205),(x+162,233)],c='line')
        a.text(x+163,478,'replica-name = '+r,23,color,True,width=325,anchor='middle')
    a.text(0,195,'worker registration / RPC',21,'muted',width=300)
    code(a,750,0,730,372,'PodGroup.spec · generated grouping','''subGroupPolicy:
- name: worker
  labelSelector:
    matchLabels:
      ray.io/group: worker
  matchLabelKeys:
  - ray.io/worker-group-replica-name
  minSubGroups: 2
  subGroupSize: 2''',25,('matchLabelKeys','minSubGroups','subGroupSize'),filename='ray-subgroup-spec.yaml')
    a.text(770,424,'One replica label → one complete SubGroup',26,'ink',True,width=690)
    a.text(770,470,'Two replicas × two hosts = four worker Pods',25,'muted',width=690)
    foot(a,'Grouping view, not a topology guarantee. Gang support is merged; replica topology is still in progress.')

    # 16: same physical vocabulary as slide 10; two separate proposed intents.
    a=renew(16)
    a.text(0,29,'PROPOSED · SubGroup relationships within one PodGroup',23,'purple',True,width=1450)
    a.text(0,84,'Affinity: cooperating groups',30,'ink',True,width=700)
    a.text(780,84,'Anti-affinity: independent replicas',30,'ink',True,width=700)
    wire(a,[(740,65),(740,482)],arrow=False,c='light')
    # Shared-domain affinity: a common switch above distinct role subgroups.
    scope(a,0,122,700,356,'Supernode A','purple')
    st,sb=switch(a,295,183,'')
    for x,label,roles,color in [(22,'Prefill SubGroup',['P0','P1'],'blue'),(378,'Decode SubGroup',['D0','D1'],'green')]:
        scope(a,x,285,300,180,'',color)
        rp=rack(a,x+57,305,180,'GPU node',roles,color,h=122)
        a.text(x+150,452,label,23,color,True,width=290,anchor='middle')
        wire(a,[sb,(sb[0],261),(rp[0],261),rp],arrow=False)
    # Replica separation: two distinct rack-level HyperNode domains.
    for x,label,r in [(780,'Rack A','Replica 0'),(1145,'Rack B','Replica 1')]:
        scope(a,x,122,335,356,label,'purple')
        st,sb=switch(a,x+111,183,'')
        scope(a,x+18,285,299,180,'','blue')
        rp=rack(a,x+75,305,180,'GPU node',['Pod 0','Pod 1'],'blue',h=122)
        a.text(x+168,452,r+' · SubGroup',23,'blue',True,width=290,anchor='middle')
        wire(a,[sb,(sb[0],267),(rp[0],267),rp],arrow=False)
    foot(a,'Place cooperating SubGroups together; spread replicas across domains. These relationships remain proposed.')

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
