"""r9: audience-facing labels; explanations belong in speaker notes.

Keep the original technical figures. Edit authored annotations by exact text,
with explicit position and type size, rather than deleting small text globally.
"""
from lxml import etree


def speaker_labels(arts, subtitles, removed, C):
    original_subtitles = dict(subtitles)
    subtitles.update({
        4:'Gang size · network locality · startup latency',
        5:'Batch path · fast path · shared NodeShard',
        6:'Desired membership → coordinated handoff',
        8:'Workload gang · replica gang',
        9:'Physical network → scheduling domains',
        10:'PodGroup: core   ·   Prefill: leaf   ·   Decode: spine',
        11:'PodGroup anti-affinity · Kthena integration proposed',
        13:'RBG in progress · Kubeflow and LWS planned',
        14:'ServingGroup → PodGroup   ·   Role replica → SubGroup',
        15:'Multi-host replicas · label-based grouping',
        16:'SubGroup affinity / anti-affinity · proposed',
        18:'Scenario → cluster → measurements',
        19:'Cross-scheduler comparisons · planned',
        20:'Bursts · group size · topology',
        21:'Group placement · ecosystem · benchmarks',
        23:'Gang / SubGroup mapping available · topology unsupported',
    })
    for n,s in original_subtitles.items():
        if s and s != subtitles.get(n):removed.setdefault(n,[]).append(s)

    # (new text, size, optional x, y). Empty labels move solely into notes.
    changes={
      4:{
        'Complete TP / PP gangs + network locality':('TP / PP gangs · locality',32),
        'Role groups + topology-aware placement':('P/D groups · locality',32),
        'Training':('Training',34), 'Inference':('Inference',34), 'Agents':('Agents',34),
        'Bursty arrivals':('Bursty arrivals',28), 'Low startup latency':('Low startup latency',30),
        'reuse ready capacity':('ready capacity',24),
        'replenish the pool':('Pool refill',28),
      },
      5:{
        '01':('',0), '02':('',0), '03':('',0),
        'Workload paths':('Workload paths',36,1020,75),
        'Batch-oriented scheduling and a Pod-oriented fast path.':('Batch · fast path',32,1020,125),
        'Local coordination':('Worker coordination',36,1020,250),
        'Parallel workers use Binder conflict checks.':('Binder conflict checks',32,1020,300),
        'Shared node access':('Shared node access',36,1020,425),
        'NodeShard coordinates candidate-node pools.':('NodeShard',32,1020,475),
      },
      6:{
        'Desired membership ≠ immediate use':('Desired ≠ in use',34,710,550),
        'Coordinators reconcile node access.':('',0),
      },
      8:{'A SubGroup policy selects Pods. Replica identity can split them into multiple SubGroups.':('Pod selection + replica identity',32,0,551)},
      9:{
        'Physical fabric':('Physical fabric',28),
        'The same hierarchy is available through the standalone HyperNode component.':('Standalone HyperNode',32,0,552),
      },
      10:{'Named tiers: core (3) · spine (2) · leaf (1)':('Core (3)  /  Spine (2)  /  Leaf (1)',30,0,552)},
      11:{
        'Each PodGroup: app=model-a':('PG label: app=model-a',28,950,497),
        'One domain can fail without taking both complete instances with it.':('Separate failure domains',34,0,550),
      },
      16:{
        'Proposed SubGroup relationships':('',0),
        'Affinity · supernode':('Affinity',38,958,110),
        'Prefill + Decode':('Prefill + Decode',34,958,165),
        'Keep KV exchange inside the same supernode.':('Same supernode · KV locality',30,958,215),
        'Anti-affinity · leaf':('Anti-affinity',38,958,335),
        'Decode replica 0 + replica 1':('Decode replicas',34,958,390),
        'Keep complete replicas on separate leaf domains.':('Separate leaves',32,958,440),
      },
      13:{
        'Extend the existing gang integration.':('Gang integration',30),
        'Build on the Volcano scheduler plugin.':('Volcano plugin',30),
        'Connect group relationships to scheduling.':('Cross-group placement',30),
        'RoleInstance → SubGroup':('RoleInstance → SubGroup',36),
        'Training groups + topology':('Training groups + topology',36),
        'Multi-role / multi-group support':('Multi-role / multi-group',36),
        'In progress':('In progress',28), 'Planned':('Planned',28),
      },
      15:{
        'One replica label → one complete SubGroup':('Replica label → SubGroup',34,770,433),
        'Two replicas × two hosts = four worker Pods':('',0),
        'Gang support is merged. Replica topology is in progress.':('Gang: merged   ·   Topology: in progress',30,0,550),
        'worker registration / RPC':('Worker RPC',26),
      },
      23:{
        'PodGang minimum = 2 + 4 = 6 Pods':('PodGang: 6 Pods',34),
        'Gang and SubGroup mapping are available. Topology support is pending.':('',0),
        'one policy':('policy',26),
      },
      18:{
        'Scenario':('Scenario',30), 'Cluster under test':('Cluster under test',30), 'Observation':('Measurements',30),
        'Version + resources + topology':('Resources · topology',28),
        'audit + scheduler metrics':('Scheduler metrics',26),
        'Gang / Pod generation':('Gangs / Pods',28),
        'audit-exporter':('audit-exporter',26),
      },
      19:{
        'One workload, replayed':('Fixed workload',32),
        'Planned comparisons':('Schedulers',32),
        'Same arrivals · groups · resources':('Arrivals · groups · resources',30,25,356),
        'Same cluster capacity':('Fixed capacity',32),
        'Pin versions + config':('Versions + config',30),
        'one scheduler per run':('One per run',26),
        'Compare latency · binding throughput · completed gangs · placement':('Latency  ·  Throughput  ·  Complete gangs  ·  Placement',34,0,490),
        'Kubernetes scheduler':('Kubernetes scheduler',30),
      },
      20:{
        'Test shape':('Scenario',30), 'What to vary':('Variables',30), 'What to observe':('Metrics',30),
        'Arrival rate / spare capacity':('Arrival rate · capacity',30),
        'Warm-pool capacity requests':('Pool capacity requests',28),
        'SubGroup size / fragmentation':('Group size · fragmentation',30),
        'Few large vs. many small groups':('Large / small gangs',28),
        'Tier limits / available domains':('Tier limits · domains',30),
        'Locality + gang + anti-affinity':('Gang · anti-affinity',28),
        'Tail scheduling latency':('Tail latency',32),
        'Complete gangs placed':('Complete gangs',32),
        'Placement correctness':('Valid placement',32),
        'Backlog recovery':('Backlog recovery',30),
        'Binding throughput':('Binding throughput',30),
        'Gang completion + latency':('Gang latency',30),
        'Find the best-fit scenarios and test topology-aware gang placement.':('',0),
      },
    }
    for n,a in arts.items():
        edits=changes.get(n,{})
        seen=set();out=[]
        for fragment in a.front:
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                if label not in edits:continue
                seen.add(label);new,size,*position=edits[label]
                removed.setdefault(n,[]).append(label)
                if not new:wrapper.remove(e);continue
                for child in list(e):e.remove(child)
                e.text=new;e.set('font-size',str(size))
                if position:e.set('x',str(position[0]));e.set('y',str(position[1]))
            out.append(''.join(etree.tostring(e,encoding='unicode') for e in wrapper))
        a.front=out
        assert set(edits)==seen,(n,'unmatched labels',set(edits)-seen)
        if n in [20,23]:
            a.routes=[r for r in a.routes if not (r['points'][0][0]==0 and r['points'][-1][0]==1480 and r['points'][0][1]>=510)]
            a.edges=[s for s in a.edges if not any(f'M0,{y} L1480,{y}' in s for y in [511,513])]

    # Roadmap: keep the three concrete workstreams, use aligned keywords.
    old=arts[21]
    for fragment in old.front:
        wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
        for e in wrapper:
            if e.tag=='text':removed.setdefault(21,[]).append(' '.join(e.itertext()))
    a=type(old)(old.name);arts[21]=a
    for x,t in [(0,'Workstream'),(440,'Next'),(1050,'Validation')]:a.text(x,35,t,30,'muted',True,width=430)
    for y,title,step,detail,evidence in [
        (115,'Group placement','SubGroup relationships','Affinity / anti-affinity','Locality\nReplica isolation'),
        (285,'Ecosystem','RBG · Kubeflow · LWS','Multi-group integration','Group identity\nPlacement intent'),
        (455,'Benchmarks','Cross-scheduler testing','Best-fit scenarios · topology','Latency · throughput\nPlacement correctness'),
    ]:
        a.path([(0,y-50),(1480,y-50)],False,'light')
        a.text(0,y,title,38,'ink',True,width=420)
        a.text(440,y,step,34,'blue',True,width=590)
        a.text(440,y+54,detail,30,'muted',width=590)
        a.text(1050,y,evidence,30,'ink',width=425)

    # r10: remove redundant annotation layers, not just their sentence grammar.
    # Keep roles inside the figures and retain explicit delivery status.
    for n,s in list(subtitles.items()):
        if s:removed.setdefault(n,[]).append(s)
        subtitles[n]=''
    subtitles.update({
        11:'Kthena anti-affinity integration: proposed',
        16:'Proposed',
        19:'Planned comparisons',
        20:'Planned test matrix',
        23:'Gang mapping available · topology unsupported',
    })
    drop={
        4:{'ready capacity','pool controller'},
        5:{'Workload paths','Worker coordination','Shared node access'},
        6:{'Desired ≠ in use'},
        8:{'Pod selection + replica identity'},
        9:{'Physical fabric'},
        10:{'Core (3) / Spine (2) / Leaf (1)'},
        11:{'Separate failure domains'},
        16:{'Prefill + Decode','Decode replicas'},
        13:{'Gang integration','Volcano plugin','Cross-group placement'},
        15:{'Replica label → SubGroup','separate group'},
        23:{'PodGang: 6 Pods','policy'},
        18:{'Scenario','Cluster under test','Measurements','Workload parameters','Gangs / Pods','Scheduler metrics'},
        19:{'Fixed workload','Schedulers','One per run','Latency · Throughput · Complete gangs · Placement'},
    }
    replace={
        4:{'TP / PP gangs · locality':('Gang + locality',34,0,280),
           'P/D groups · locality':('Gang + locality',34,770,280),
           'Warm pool':('Warm pool',28,772.5,374),
           'Capacity request':('Capacity request',27,772.5,480)},
        5:{'Batch · fast path':('Batch / fast path',38,1020,135),
           'Binder conflict checks':('Binder checks',38,1020,310),
           'NodeShard':('Shared node pools',38,1020,485)},
        15:{'Ray head':('Ray head',28,347.5,147)},
        18:{'Scenario runner':('Scenario runner',28,150,160),
            'Prometheus':('Prometheus',28,1305,380)},
        16:{'Affinity':('Affinity',40,958,130),
            'Same supernode · KV locality':('Supernode · KV locality',34,958,188),
            'Anti-affinity':('Anti-affinity',40,958,355),
            'Separate leaves':('Leaf · replica isolation',34,958,413)},
    }
    for n,a in arts.items():
        targets=drop.get(n,set());edits=replace.get(n,{})
        seen=set();out=[]
        for fragment in a.front:
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                if label in targets:
                    seen.add(label);removed.setdefault(n,[]).append(label);wrapper.remove(e)
                elif label in edits:
                    seen.add(label);removed.setdefault(n,[]).append(label)
                    t,size,x,y=edits[label]
                    for child in list(e):e.remove(child)
                    e.text=t;e.set('font-size',str(size));e.set('x',str(x));e.set('y',str(y))
                    if n==5:e.set('font-weight','700');e.set('fill',C['blue'])
            out.append(''.join(etree.tostring(e,encoding='unicode') for e in wrapper))
        a.front=out
        assert targets|set(edits)==seen,(n,'r10 unmatched labels',(targets|set(edits))-seen)
        if n==11:
            a.routes=[r for r in a.routes if not (r['points'][0][0]==0 and r['points'][-1][0]==1480 and r['points'][0][1]>=510)]
            a.edges=[s for s in a.edges if 'M0,513 L1480,513' not in s]
