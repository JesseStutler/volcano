"""Approved r5 edits. Share the China topology vocabulary across placement pages.

Solid outlines are physical domains; dashed outlines are scheduling groups.
Physical cables are undirected. Process arrows use explicit orthogonal routes.
"""

def revise(arts, art, code, raw, original, C, assets):
    def renew(n):
        a=type(arts[n])(arts[n].name);arts[n]=a;return a
    def line(a,points,c='line',arrow=False,dash=False):
        assert all(x==xx or y==yy for (x,y),(xx,yy) in zip(points,points[1:])),points
        a.path(points,arrow,c,dash)
    def foot(a,t,c='blue'):
        line(a,[(0,513),(1480,513)],'light')
        a.text(0,550,t,25,c,True,width=1475)
    def scope(a,x,y,w,h,label,c='blue'):
        a.rect(x,y,w,h,'white',c,12,layer='bg',dash=True)
        a.text(x+15,y+29,label,23,c,True,width=w-30)
    def pod(a,x,y,w,label,c='blue',h=47):
        a.rect(x,y,w,h,'prefill' if c=='blue' else ('mint' if c=='green' else 'lav'),c,4)
        a.text(x+w/2,y+h/2+8,label,23,c,True,width=w-12,anchor='middle')
    def module(a,x,y,w,h,title,sub='',c='blue'):
        a.rect(x,y,w,h,'white',c,4)
        a.text(x+w/2,y+h/2+(0 if sub else 8),title,25,'ink',True,width=w-18,anchor='middle')
        if sub:a.text(x+w/2,y+h/2+28,sub,21,'muted',width=w-18,anchor='middle')

    # Shared fabric: the original two-core / four-spine / four-leaf layout.
    # Reuse the original switch symbol through a viewport; only placement changes.
    def fabric(a,mode):
        for x,name in [(0,'Supernode A'),(462,'Supernode B')]:
            a.rect(x,117,442,355,'white','line',12,layer='bg')
            a.text(x+221,502,name+(' · PG '+str(x//462) if mode=='ha' else (' · one PG' if x==0 else ' · spare')),23,'ink',True,width=438,anchor='middle')
        a.text(454,24,'Shared core fabric',23,'muted',True,width=400,anchor='middle')
        cores=[310,594];branches=[112,332,574,794]
        def switch(cx,y):
            original(a,'china-17-multilevel-topology.png',cx-34,y,68,48,(818,110,158,114))
            # Clip to the switch silhouette, excluding source-image cable stubs.
            symbol=a.front.pop();clip=f'switch-{cx}-{y}'
            k=48/114;left=cx-158*k/2
            pts=' '.join(f'{left+px*k},{y+py*k}' for px,py in [(48,0),(158,0),(158,52),(118,114),(0,114),(0,56)])
            a.front.append(f'<defs><clipPath id="{clip}"><polygon points="{pts}"/></clipPath></defs><g clip-path="url(#{clip})">{symbol}</g>')
        def cable(points):
            a.path(points,False,'line');a.routes[-1]['kind']='fabric'
        for cx in cores:
            switch(cx,40)
            for tx in branches:cable([(cx,88),(tx,168)])
        for cx in branches:switch(cx,168)
        for pair in [branches[:2],branches[2:]]:
            for cx in pair:
                for tx in pair:cable([(cx,216),(tx,279)])
        for i,cx in enumerate(branches):
            switch(cx,279)
            a.text(cx-103,310,'Leaf '+str(i),19,'muted',True,width=68)
        centers=[64,160,284,380,526,622,746,842]
        for i,cx in enumerate(centers):
            cable([(branches[i//2],327),(cx,374)])
            a.rect(cx-37,374,74,87,'#f2f5f9','line',1)
            a.text(cx,396,({0:'Prefill',1:'Decode 0',3:'Decode 1'}.get(i,'Rack '+str(i+1)) if mode!='ha' else 'Rack '+str(i+1)),16 if mode!='ha' else 18,'ink',True,width=72,anchor='middle')
            if mode=='ha':
                c='blue' if i<4 else 'green';label=['P0','P1','D0','D1'][i%4]
                pod(a,cx-29,410,58,label,c,47)
            elif i in [0,1,3]:
                c='blue' if i==0 else 'green'
                labels={0:['P0','P1'],1:['D0','D1'],3:['D2','D3']}[i]
                for j,t in enumerate(labels):
                    a.rect(cx-29,404+j*33,58,29,'prefill' if c=='blue' else 'mint',c,3)
                    a.text(cx,425+j*33,t,20,c,True,width=54,anchor='middle')
            else:
                a.text(cx,441,'free',19,'muted',width=70,anchor='middle')
        if mode=='ha':
            for x,t,c in [(10,'PG 0 · complete instance','blue'),(472,'PG 1 · complete instance','green')]:
                a.rect(x,365,422,103,'none',c,10,dash=True)
                # Identity belongs above the group contour, not on a physical link.
                # Instance identity is in the domain heading, away from cables.
        else:
            # The PodGroup stays in A; distinct decode groups occupy different leaves.
            a.rect(10,365,422,103,'none','purple',10,dash=True)
            for cx,c in [(64,'blue'),(160,'green'),(380,'green')]:
                a.rect(cx-43,367,86,98,'none',c,7,dash=True)

    # 04: upper compute structures, lower burst-to-capacity path. No Pod per call.
    a=renew(4)
    a.text(0,28,'TRAINING',26,'blue',True,width=670)
    a.text(770,28,'INFERENCE',26,'green',True,width=710)
    scope(a,0,52,690,193,'PodGroup · pipeline stages','blue')
    scope(a,770,52,710,193,'PodGroup · disaggregated serving','green')
    for x,t in [(20,'PP stage 0'),(389,'PP stage 1')]:
        a.rect(x,101,281,121,'white','blue',7,dash=True)
        a.text(x+140,129,t,23,'blue',True,width=250,anchor='middle')
        for j in range(2):pod(a,x+12+j*135,153,122,'TP '+str(j))
    line(a,[(301,174),(389,174)],'blue',True)
    a.text(345,153,'PP',20,'blue',True,width=60,anchor='middle')
    for x,w,t,labels in [(790,235,'Prefill',['P0','P1']),(1140,320,'Decode replicas',['D0','D1'])]:
        a.rect(x,101,w,121,'white','green',7,dash=True)
        a.text(x+w/2,129,t,23,'green',True,width=w-18,anchor='middle')
        for j,t2 in enumerate(labels):pod(a,x+12+j*(w-12)/2,153,(w-36)/2,t2,'green')
    line(a,[(1025,174),(1140,174)],'green',True)
    a.text(1082,153,'KV',20,'green',True,width=90,anchor='middle')
    a.text(0,280,'Complete TP / PP gangs + network locality',25,'blue',True,width=720)
    a.text(770,280,'Role groups + topology-aware placement',25,'green',True,width=710)
    line(a,[(0,306),(1480,306)],'light')
    a.text(0,347,'AGENTS',26,'orange',True,width=220)
    a.text(0,383,'Bursty arrivals',24,'ink',True,width=260)
    # Schematic arrival rate: a stepped burst, not benchmark data.
    line(a,[(0,471),(180,471)],'light')
    line(a,[(5,460),(32,460),(32,425),(65,425),(65,407),(94,407),(94,444),(127,444),(127,460),(175,460)],'orange')
    a.text(0,504,'Low startup latency',23,'orange',True,width=270)
    module(a,275,393,220,78,'Agent runtime',c='orange')
    line(a,[(190,432),(275,432)],'orange',True)
    # Warm hit is the short path; a miss asks for capacity through Kubernetes.
    module(a,630,331,285,67,'Warm pool','reuse ready capacity','orange')
    line(a,[(495,432),(553,432),(553,365),(630,365)],'orange',True)
    a.text(572,349,'hit',20,'orange',True,width=55)
    module(a,630,438,285,67,'Capacity request','pool controller','orange')
    line(a,[(553,432),(553,471),(630,471)],'orange',True)
    a.text(567,496,'miss',20,'orange',True,width=60)
    module(a,1100,438,380,67,'Fast Pod scheduling',c='blue')
    line(a,[(915,471),(1100,471)],'blue',True)
    a.text(958,449,'scale up',21,'blue',True,width=135)
    line(a,[(1290,438),(1290,365),(915,365)],'blue',True)
    a.text(978,347,'replenish the pool',22,'blue',True,width=310)
    foot(a,'Schedule complete groups and their locality; keep latency-sensitive capacity ready.')

    # 11: same fabric as 10, now two complete instances in separate domains.
    a=renew(11);fabric(a,'ha')
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
    code(a,920,0,560,461,'PodGroup.spec · key fields','''networkTopology:
  mode: hard
  highestTierName: supernode
topologyAffinity:
  podGroupAntiAffinity:
    required:
    - podGroupSelector:
        matchLabels:
          app: model-a
      topologyTierName: supernode''',26,('highestTierName','topologyTierName'))
    a.text(954,499,'Each PodGroup: app=model-a',22,'blue',True,width=515)
    foot(a,'One domain can fail without taking both complete instances with it.')

    # 12 (source 16): physically composable rules, not two unrelated diagrams.
    a=renew(16);fabric(a,'subgroup')
    a.text(958,31,'PROPOSED · SUBGROUP RELATIONSHIPS',22,'purple',True,width=520)
    a.text(958,100,'Affinity · supernode',30,'blue',True,width=515)
    a.text(958,148,'Prefill + Decode',28,'ink',True,width=510)
    a.text(958,190,'Keep KV exchange inside the same supernode.',26,'muted',width=500)
    line(a,[(958,265),(1480,265)],'light')
    a.text(958,320,'Anti-affinity · leaf',30,'green',True,width=510)
    a.text(958,368,'Decode replica 0 + replica 1',27,'ink',True,width=510)
    a.text(958,410,'Keep complete replicas on separate leaf domains.',26,'muted',width=505)
    foot(a,'Cooperate at one topology level; isolate replicas at a finer level.')

    # 17 (source 13): three next communities after the concrete integration cases.
    a=renew(13)
    rows=[(15,'rbg.svg','RBG','IN PROGRESS','RoleInstance → SubGroup','Extend the existing gang integration.'),
          (184,'kubeflow.svg','Kubeflow','PLANNED','Training groups + topology','Build on the Volcano scheduler plugin.'),
          (353,'leaderworkerset.svg','LWS','PLANNED','Multi-role / multi-group support','Connect group relationships to scheduling.')]
    for y,logo,name,status,title,sub in rows:
        a.image(12,y+20,112,105,assets/logo)
        a.text(163,y+57,name,34,'ink',True,width=360)
        a.text(165,y+99,status,21,'purple',True,width=360)
        a.text(585,y+57,title,30,'blue',True,width=880)
        a.text(585,y+104,sub,25,'muted',width=880)
        if y<353:line(a,[(163,y+148),(1480,y+148)],'light')
    foot(a,'Carry roles, replicas, and placement intent from the controller into Volcano.')

    # 16 (new source 23): actual main-branch Grove adapter, no topology claim.
    a=art(23,'grove-mapping','Grove: Carry PodGang Structure into Volcano',
          'The backend translates Grove PodGroups into Volcano SubGroup policies.',3,
          source='https://github.com/NVIDIA/grove/blob/1d8f83b38a3f54d9827bb579a68c0315ed54ce91/operator/internal/scheduler/volcano/backend.go (reviewed 2026-10-29); #516 merged. topologyConstraint is currently rejected.')
    a.image(0,0,80,65,assets/'dynamo-grove.svg')
    a.text(106,43,'Grove PodGang',31,'ink',True,width=530)
    a.text(875,43,'Volcano PodGroup',31,'blue',True,width=580)
    scope(a,0,94,610,310,'PodGang.spec.podGroups','blue')
    scope(a,870,94,610,310,'PodGroup.spec.subGroupPolicy','green')
    for yy,name,count in [(153,'prefill',2),(283,'decode',4)]:
        a.text(24,yy,name,28,'ink',True,width=210)
        raw(a,270,yy,'minReplicas: '+str(count),25,'blue',False,True)
        for j in range(count):pod(a,24+j*141,yy+19,126,'Pod '+str(j),'blue',48)
        line(a,[(610,yy+32),(870,yy+32)],'line',True)
        a.text(739,yy+14,'one policy',21,'muted',width=190,anchor='middle')
        a.text(894,yy,name,28,'ink',True,width=200)
        raw(a,1120,yy,'subGroupSize: '+str(count),24,'green',False,True)
        raw(a,894,yy+48,'minSubGroups: 1',24,'green',False,True)
    a.text(0,463,'PodGang minimum = 2 + 4 = 6 Pods',27,'ink',True,width=700)
    raw(a,894,463,'minMember: 6',28,'green',True,True)
    foot(a,'Gang / SubGroup mapping is available; topologyConstraint is not yet supported.')

    # 20 (source 19): a controlled comparison, not pretend result bars.
    a=renew(19)
    a.text(0,31,'ONE WORKLOAD, REPLAYED',23,'blue',True,width=680)
    a.text(940,31,'CROSS-SCHEDULER TESTING',23,'purple',True,width=540)
    # A job envelope with explicit arrival batches and group sizes.
    a.rect(0,77,495,320,'white','line',5,layer='bg')
    a.text(25,119,'Fixed scenario',30,'ink',True,width=445)
    for y,t,sizes in [(167,'Batch 0',[2,2]),(249,'Batch 1',[4,2])]:
        a.text(25,y,t,23,'muted',True,width=130)
        xx=158
        for size in sizes:
            a.rect(xx,y-24,142,57,'white','blue',5,dash=True)
            a.text(xx+71,y+12,str(size)+' Pods',24,'blue',True,width=130,anchor='middle');xx+=157
    a.text(25,356,'Same arrivals · groups · resources',24,'ink',width=460)
    line(a,[(495,236),(632,236)],'blue',True)
    module(a,632,190,285,92,'Reset & replay','one scheduler per run')
    a.text(632,332,'Same cluster capacity',25,'ink',True,width=285)
    a.text(632,378,'Pin versions + config',24,'muted',width=285)
    for y,t,c in [(78,'Volcano','blue'),(213,'Kubernetes scheduler¹','line'),(348,'Other schedulers¹','line')]:
        module(a,1090,y,390,81,t,c=c)
    line(a,[(917,236),(1004,236)],'line')
    line(a,[(1004,118),(1004,388)],'line')
    for yy in [118,253,388]:line(a,[(1004,yy),(1090,yy)],'line',True)
    a.text(0,457,'Compare latency · binding throughput · completed gangs · placement',28,'ink',True,width=1470)
    a.text(0,496,'¹ Planned comparison set; match workload semantics and record unsupported constraints.',22,'muted',width=1470)
    foot(a,'Harness available. Next: cross-scheduler runs and representative scenarios.')

    # 21 (source 20): real test shapes, not decorative boxes or fake data.
    a=renew(20)
    a.text(0,27,'TEST SHAPE',22,'muted',True,width=490)
    a.text(630,27,'WHAT TO VARY',22,'muted',True,width=370)
    a.text(1090,27,'WHAT TO OBSERVE',22,'muted',True,width=390)
    for yy in [52,207,362]:line(a,[(0,yy),(1480,yy)],'light')
    a.text(0,91,'Bursts',28,'orange',True,width=170)
    # Actual arrival steps with a bounded capacity line.
    line(a,[(180,174),(540,174)],'light')
    line(a,[(185,164),(235,164),(235,117),(285,117),(285,91),(335,91),(335,145),(390,145),(390,164),(535,164)],'orange')
    line(a,[(180,137),(540,137)],'line',dash=True)
    a.text(630,111,'Arrival rate / spare capacity',26,'ink',True,width=430)
    a.text(630,157,'Warm-pool capacity requests',23,'muted',width=430)
    a.text(1090,111,'Tail scheduling latency',26,'ink',True,width=380)
    a.text(1090,157,'Backlog recovery',24,'muted',width=380)
    a.text(0,246,'Gang size',28,'blue',True,width=170)
    for x,labels in [(180,['P0','P1']),(378,['P2','P3'])]:
        a.rect(x,238,167,91,'none','blue',7,dash=True)
        for j,t in enumerate(labels):pod(a,x+9+j*77,263,72,t,h=47)
    a.text(630,266,'SubGroup size / fragmentation',26,'ink',True,width=435)
    a.text(630,312,'Few large vs. many small groups',23,'muted',width=430)
    a.text(1090,266,'Complete gangs placed',26,'ink',True,width=380)
    a.text(1090,312,'Binding throughput',24,'muted',width=380)
    a.text(0,401,'Topology',28,'green',True,width=170)
    # Same gang straddling domains vs. packed locally: test constraint effect.
    for x,t,labels in [(180,'Leaf A',['P0','P1']),(378,'Leaf B',['D0','D1'])]:
        a.rect(x,385,167,108,'white','line',4,layer='bg')
        a.text(x+83,411,t,22,'muted',True,width=150,anchor='middle')
        for j,label in enumerate(labels):pod(a,x+9+j*77,434,72,label,'green',47)
    line(a,[(347,422),(378,422)],'line')
    a.text(630,421,'Tier limits / available domains',26,'ink',True,width=435)
    a.text(630,467,'Locality + gang + anti-affinity',23,'muted',width=430)
    a.text(1090,421,'Placement correctness',26,'ink',True,width=380)
    a.text(1090,467,'Gang completion + latency',24,'muted',width=385)
    foot(a,'Find the best-fit scenarios and their tradeoffs; validate topology-aware gang placement.')
