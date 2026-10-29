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
    def fanout(a,source,targets,bus_y,c='line',arrow=False):
        # Draw a shared trunk once, then a symmetric bus and exact endpoint stems.
        xs=[x for x,y in targets]
        assert len({y for x,y in targets}) == 1
        assert abs(source[0]-(min(xs)+max(xs))/2) < 0.001
        wire(a,[source,(source[0],bus_y)],c,False)
        wire(a,[(min(xs),bus_y),(max(xs),bus_y)],c,False)
        for target in targets:wire(a,[(target[0],bus_y),target],c,arrow)

    def rack(a,x,y,w,title,roles,color='blue',h=157):
        # Explicit node chassis and named Pod rows; no implied GPU count.
        a.rect(x,y,w,h,'#f5f7fa','line',1)
        a.text(x+w/2,y+26,title,21,'ink',True,width=w-8,anchor='middle')
        rh=(h-48)/len(roles)
        for i,label in enumerate(roles):
            yy=y+37+i*rh
            a.rect(x+9,yy,w-18,rh-8,'prefill' if color=='blue' else 'mint',color,4)
            a.text(x+w/2,yy+25,label,21,color,True,width=w-24,anchor='middle')
            if rh>=70:
                a.text(x+w/2,yy+55,'Pod',19,'muted',width=w-24,anchor='middle')
        return (x+w/2,y)

    def scope(a,x,y,w,h,label,color='blue',fill='white'):
        a.rect(x,y,w,h,fill,color,22,layer='bg',dash=True)
        a.text(x+18,y+32,label,24,color,True,width=w-36)

    def service(a,x,y,w,label,sub=None,color='blue',h=66):
        # A named runtime component, not a Kubernetes Pod symbol.
        a.rect(x,y,w,h,'white',color,8)
        a.text(x+w/2,y+(h/2-6 if sub else h/2+8),label,25,'ink',True,width=w-20,anchor='middle')
        if sub:a.text(x+w/2,y+h/2+21,sub,21,'muted',width=w-20,anchor='middle')

    def flat_switch(a,cx,y,w=100):
        # Front elevation: no perspective face or hand-drawn asymmetric arrow.
        x=cx-w/2
        a.rect(x,y,w,44,'#08749d',None,2)
        for x1,x2,yy in [(x+17,x+w-17,y+14),(x+w-17,x+17,y+30)]:
            direction=1 if x2>x1 else -1
            a.front.append(f'<path d="M{x1},{yy} H{x2} M{x2-direction*8},{yy-4} L{x2},{yy} L{x2-direction*8},{yy+4}" fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/>')
        return (cx,y+44)

    def host(a,x,y,w,label,pods,color='blue',h=86):
        a.rect(x,y,w,h,'white','line',2)
        a.text(x+12,y+25,label,20,'muted',True,width=w-24)
        pw=(w-30)/len(pods)
        for i,t in enumerate(pods):
            xx=x+10+i*(pw+10)
            a.rect(xx,y+37,pw,35,'prefill' if color=='blue' else 'mint',color,3)
            a.text(xx+pw/2,y+61,t,21,color,True,width=pw-6,anchor='middle')
        return x+w/2,y

    # 04: distinct workload structures, with short routes and aligned ports.
    a=renew(4)
    a.text(0,28,'TRAINING & RL',24,'blue',True)
    a.text(0,64,'Complete compute groups; collective communication',24,'muted',width=510)
    scope(a,0,112,515,370,'One training gang','blue')
    sb=flat_switch(a,253,190)
    a.text(253,173,'Collective fabric',23,'ink',True,width=250,anchor='middle')
    ports=[]
    for x,title,roles in [(35,'GPU node A',['rank 0','rank 1']),(294,'GPU node B',['rank 2','rank 3'])]:
        ports.append(rack(a,x,304,177,title,roles,h=153))
    fanout(a,sb,ports,272)
    a.text(253,296,'all-reduce',21,'blue',True,width=150,anchor='middle')
    a.text(610,28,'AGENT APPLICATION',24,'orange',True)
    a.text(610,64,'Variable fan-out; latency-sensitive runtime calls',24,'muted',width=850)
    service(a,620,110,210,'Planner',color='orange',h=80)
    service(a,1050,115,415,'Retrieval','tool service',color='orange',h=70)
    service(a,1050,215,415,'Sandbox','runtime session',color='orange',h=70)
    wire(a,[(830,150),(970,150)],'orange',False)
    wire(a,[(970,150),(1050,150)],'orange')
    wire(a,[(970,150),(970,250),(1050,250)],'orange')
    a.text(854,134,'tool calls',21,'orange',width=170)
    # A straight vertical model-call path connects an agent runtime to serving.
    wire(a,[(725,190),(725,395)],'orange')
    a.text(746,309,'model calls',22,'orange',True,width=180)
    a.text(960,329,'INFERENCE',24,'green',True)
    a.text(960,360,'Long-lived replicas; local KV transfer',23,'muted',width=520)
    service(a,620,395,210,'Router',color='green',h=80)
    scope(a,940,380,540,108,'','green')
    service(a,960,400,200,'Prefill','prompt compute',color='green',h=70)
    service(a,1260,400,200,'Decode','token generation',color='blue',h=70)
    wire(a,[(830,435),(960,435)],'green')
    wire(a,[(1160,435),(1260,435)],'green')
    a.text(1210,421,'KV',21,'green',True,width=80,anchor='middle')
    foot(a,'Shared cluster capacity: training needs complete groups; inference needs locality; agents add variable demand.')

    # 11: two real placement domains above two independent API explanations.
    # Topology is conveyed by undirected cables; membership by dashed contours.
    a=renew(11)
    for x,domain,instance,color in [(0,'Supernode A','instance-a','blue'),(780,'Supernode B','instance-b','green')]:
        a.text(x,26,domain,27,'ink',True,width=700)
        a.rect(x,44,700,215,'white','line',6,layer='bg')
        a.text(x+223,87,instance+' · PodGroup',26,color,True,width=460)
        raw(a,x+223,120,'app: model-a',23,'muted',False,True)
        a.rect(x+212,149,468,96,'white',color,10,layer='bg',dash=True)
        end=flat_switch(a,x+85,88)
        a.text(x+85,181,'Network',22,'ink',True,width=170,anchor='middle')
        ports=[]
        for xx,node,roles in [(x+226,'Node 0',['P0','P1']),(x+464,'Node 1',['D0','D1'])]:
            ports.append(host(a,xx,154,202,node,roles,color,h=86))
        # One level bus, and two vertical drops. Draw each segment only once.
        wire(a,[end,(end[0],140),(ports[-1][0],140)],arrow=False)
        for port in ports:wire(a,[(port[0],140),port],arrow=False)
    code(a,0,290,660,270,'LOCALITY · spec.networkTopology','''mode: hard
highestTierName: supernode''',30,('highestTierName',))
    a.text(20,452,'One complete instance inside one domain.',27,'blue',True,width=615)
    a.text(20,503,'P = Prefill · D = Decode',25,'muted',width=610)
    code(a,700,290,780,270,'SEPARATION · spec.topologyAffinity','''podGroupAntiAffinity:
  required:
  - podGroupSelector:
      matchLabels:
        app: model-a
    topologyTierName: supernode''',26,('podGroupAntiAffinity','topologyTierName'))
    # Keep a single coherent API excerpt in the downloadable examples.
    (assets.parent/'examples'/'podgroup-anti-affinity.yaml').write_text('''metadata:
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
        topologyTierName: supernode
''')

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

    # 16: compare the actual placement rules, without decorative topology arrows.
    # The physical domain outlines and SubGroup outlines use different line styles.
    a=renew(16)
    a.text(0,27,'PROPOSED · relationships between SubGroups inside one PodGroup',23,'purple',True,width=1480)
    # Affinity row: two collaborating subgroups share one topology domain.
    a.text(0,100,'Affinity',32,'ink',True,width=300)
    a.text(0,145,'Prefill + Decode',26,'blue',True,width=325)
    a.text(0,185,'Keep cooperating groups local.',24,'muted',width=310)
    a.rect(370,60,1110,189,'white','line',5,layer='bg')
    a.text(390,95,'Supernode A',25,'ink',True,width=300)
    for x,label,roles,color in [(395,'Prefill SubGroup',['P0','P1'],'blue'),(940,'Decode SubGroup',['D0','D1'],'green')]:
        a.rect(x,119,510,109,'white',color,9,layer='bg',dash=True)
        a.text(x+15,148,label,23,color,True,width=470)
        for i,t in enumerate(roles):
            a.rect(x+15+i*247,167,232,43,'prefill' if color=='blue' else 'mint',color,3)
            a.text(x+131+i*247,196,t+' · Pod',23,color,True,width=210,anchor='middle')
    # Anti-affinity row: the same role replicas have independent domain boundaries.
    a.text(0,335,'Anti-affinity',32,'ink',True,width=320)
    a.text(0,380,'Independent replicas',26,'blue',True,width=330)
    a.text(0,420,'Use different topology domains.',24,'muted',width=315)
    for x,domain,replica in [(370,'Rack A','Replica 0'),(940,'Rack B','Replica 1')]:
        a.rect(x,295,540,189,'white','line',5,layer='bg')
        a.text(x+20,330,domain,25,'ink',True,width=490)
        a.rect(x+20,354,500,109,'white','blue',9,layer='bg',dash=True)
        a.text(x+35,383,replica+' · SubGroup',23,'blue',True,width=470)
        for i,t in enumerate(['Pod 0','Pod 1']):
            a.rect(x+35+i*237,402,222,43,'prefill','blue',3)
            a.text(x+146+i*237,431,t,23,'blue',True,width=210,anchor='middle')
    foot(a,'Solid outline: topology domain. Dashed outline: SubGroup. Relationship APIs remain under discussion.')

    # 18: component centers share rows; vertical arrows land on exact face ports.
    a=renew(18)
    a.text(0,29,'SCENARIO',22,'muted',True)
    a.text(430,29,'CLUSTER UNDER TEST',22,'muted',True)
    a.text(1130,29,'OBSERVATION',22,'muted',True)
    service(a,0,105,300,'Scenario runner','Gang / Pod generation',h=90)
    a.text(0,252,'Workload parameters',25,'ink',True,width=320)
    for yy,t in [(299,'JOBS'),(341,'REPLICAS'),(383,'MIN_AVAILABLE')]:raw(a,0,yy,t,25,'blue',True,True)
    a.text(0,452,'Version + resources + topology',23,'muted',width=325)
    a.rect(390,65,690,415,'pale','line',4,layer='bg')
    a.rect(430,105,610,90,'white','line',3)
    icon(a,448,124,52,'api');a.text(520,141,'Kubernetes API',28,'ink',True,width=490)
    a.text(520,176,'Pods · PodGroups · HyperNodes',23,'muted',width=490)
    a.rect(430,325,610,90,'white','blue',3)
    a.image(450,347,76,44,assets/'volcano-icon.svg');a.text(548,378,'Volcano scheduler',29,'ink',True,width=470)
    a.text(430,458,'Kind + KWOK / existing cluster',25,'ink',True,width=610)
    wire(a,[(300,150),(430,150)])
    a.text(318,132,'create',21,'muted',width=85)
    wire(a,[(610,195),(610,325)],'blue')
    a.text(504,270,'watch',23,'blue',True,width=90)
    wire(a,[(860,325),(860,195)],'blue')
    a.text(878,270,'bind',23,'blue',True,width=90)
    service(a,1130,105,350,'Audit log','create / bind events',h=90)
    service(a,1130,325,350,'Prometheus','audit + scheduler metrics',h=90)
    service(a,1130,445,350,'Report / Grafana',h=55)
    wire(a,[(1040,150),(1130,150)])
    wire(a,[(1305,195),(1305,325)],'green')
    a.text(1130,270,'audit-exporter',22,'green',True,width=170)
    wire(a,[(1040,370),(1130,370)],'green')
    wire(a,[(1305,415),(1305,445)],'green')
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

    # 20: vertical event sequences, explicit intervals, and the actual formulas.
    # No invented result curve or decorative sampling dots.
    a=renew(20)
    a.text(0,31,'Scheduling latency',31,'ink',True,width=700)
    a.text(0,77,'One Pod · creation to scheduling',24,'muted',width=700)
    a.text(800,31,'Scheduling throughput',31,'ink',True,width=680)
    a.text(800,77,'Successful pods/binding events',24,'muted',width=680)
    a.text(800,112,'ResponseComplete · HTTP 2xx',23,'green',True,width=680)
    wire(a,[(740,0),(740,480)],arrow=False,c='light')
    # Time advances downward. Interval endpoints are also event endpoints.
    wire(a,[(60,155),(60,475)],'line')
    wire(a,[(60,155),(60,300)],'blue',False)
    for yy,label,color in [(155,'created','blue'),(300,'scheduled','blue'),(440,'ready','muted')]:
        a.rect(54,yy-6,12,12,color,None,0)
        a.text(95,yy+8,label,27,color,True,width=255)
    a.text(95,381,'runtime / application',23,'muted',width=280)
    # A precise interval bar, separate from the time axis and the event labels.
    wire(a,[(365,155),(365,300)],'blue',False)
    wire(a,[(352,155),(378,155)],'blue',False)
    wire(a,[(352,300),(378,300)],'blue',False)
    a.text(405,215,'Latency',27,'blue',True,width=300)
    raw(a,405,259,'scheduledAt',25,'ink',False,True)
    raw(a,405,295,'− createdAt',25,'ink',False,True)
    a.text(405,364,'Report P50 / P90 / P99',23,'muted',width=310)
    # The window is from first to last successful binding in the selected data.
    wire(a,[(830,155),(830,440)],'green',False)
    wire(a,[(817,155),(843,155)],'green',False)
    wire(a,[(817,440),(843,440)],'green',False)
    a.text(866,163,'First successful bind',26,'green',True,width=590)
    a.text(866,448,'Last successful bind',26,'green',True,width=590)
    raw(a,955,280,'N / Δt',43,'green',True,True)
    a.text(955,328,'N = successful bindings',24,'ink',width=500)
    a.text(955,368,'Δt = last bind − first bind',24,'ink',width=500)
    foot(a,'Definitions only; no result values shown. Compare runs with the same version, workload, and resources.')

    # 21: concrete maintainer priorities and the evidence each one needs.
    a=renew(21)
    for x,title,w in [(0,'WORKSTREAM',325),(360,'NEXT STEP',500),(935,'WHAT TO VALIDATE',545)]:
        a.text(x,30,title,22,'muted',True,width=w)
    wire(a,[(0,56),(1480,56)],arrow=False,c='line')
    rows=[
      (98,'Group placement','SubGroup affinity / anti-affinity',
       'Extend the existing gang and topology model.',
       'Cooperating groups stay local; replicas use separate domains.'),
      (238,'Community integration','RBG · Kubeflow · LWS multi-group',
       'Carry roles and replica identity into scheduling.',
       'Controllers preserve complete groups and map placement constraints.'),
      (378,'Benchmark validation','Repeat runs across workload shapes',
       'Vary scale, grouping, and topology.',
       'Retain latency distributions, binding throughput, and raw events.')]
    for y,title,step,detail,evidence in rows:
        a.text(0,y,title,29,'ink',True,width=320)
        a.text(360,y,step,26,'blue',True,width=540)
        a.text(360,y+45,detail,24,'muted',width=520)
        a.text(935,y,evidence,26,'ink',width=535)
        if y<378:wire(a,[(0,y+105),(1480,y+105)],arrow=False,c='light')
    foot(a,'Bring a controller mapping, a placement requirement, or a reproducible workload to the community.')
    # Discussion page is a typographic close, not a diagram.
    a=renew(22)
    a.text(0,103,'What must run together?',48,'ink',True,width=1460)
    a.text(0,183,'What should stay apart?',48,'blue',True,width=1460)
    wire(a,[(0,264),(1480,264)],arrow=False,c='line')
    a.text(0,354,'Bring a workload, a topology constraint, or a reproducible test.',30,'ink',width=1470)
    a.text(0,454,'github.com/volcano-sh/volcano',34,'blue',True,width=1460)
    a.text(0,515,'Roadmap and feedback · issue #6166',25,'muted',width=1460)
