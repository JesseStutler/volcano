"""Figures for victim selection, controlled comparisons and roadmap directions."""

GANGS = {
    'A': {'priority': 10, 'domain': 'West', 'pods': ['A0', 'A1'], 'minMember': 2},
    'B': {'priority': 20, 'domain': 'West', 'pods': ['B0', 'B1'], 'minMember': 2},
    'C': {'priority': 30, 'domain': 'West', 'pods': ['C0', 'C1'], 'minMember': 2},
    'D': {'priority': 40, 'domain': 'West', 'pods': ['D0', 'D1'], 'minMember': 2},
    'E': {'priority': 50, 'domain': 'East', 'pods': ['E0', 'E1'], 'minMember': 2},
    'F': {'priority': 60, 'domain': 'East', 'pods': ['F0', 'F1'], 'minMember': 2},
}
PREEMPTOR = {'priority': 100, 'minMember': 4, 'highestTierName': 'spine'}
SCATTERED_VICTIMS = ['A0', 'B0', 'C0', 'D0']
SELECTED_GANGS = ['A', 'B']


def draw_preemption(a, original):
    colors={'A':'blue','B':'green','C':'purple','D':'amber','E':'green','F':'purple'}
    fills={'blue':'prefill','green':'mint','purple':'lav','amber':'sand'}

    def pod(x,y,w,t,c='blue',victim=False,h=38,size=24):
        a.rect(x,y,w,h,'white' if victim else fills[c],'orange' if victim else c,3)
        a.text(x+w/2,y+h/2+size*.33,t,size,c,True,width=w-8,anchor='middle')
        if victim:
            # An X is a victim mark, not a routed edge through explanatory text.
            a.front.append(f'<path d="M{x+4},{y+4} L{x+w-4},{y+h-4} M{x+w-4},{y+4} L{x+4},{y+h-4}" stroke="#c14421" stroke-width="3" opacity="0.85"/>')

    def switch(cx,y):
        original(a,'china-17-multilevel-topology.png',cx-21,y,42,30,(818,110,158,114))
        symbol=a.front.pop();clip=f'gang-switch-{cx}-{y}'
        sc=42/158;left=cx-21;top=y+(30-114*sc)/2
        pts=' '.join(f'{left+px*sc},{top+py*sc}' for px,py in [(48,0),(158,0),(158,52),(118,114),(0,114),(0,56)])
        a.front.append(f'<defs><clipPath id="{clip}"><polygon points="{pts}"/></clipPath></defs><g clip-path="url(#{clip})">{symbol}</g>')

    a.rect(0,0,1480,79,'prefill',None,5)
    a.text(18,32,'Incoming gang S',31,'blue',True,width=350)
    a.text(18,65,'priority: 100',25,'blue',width=320,mono=True)
    for j in range(4):pod(380+j*86,21,72,'S'+str(j))
    a.text(800,32,'minMember: 4',27,'blue',True,width=660,mono=True)
    a.text(800,65,'highestTierName: spine',25,'blue',width=660,mono=True)

    a.text(210,125,'Pod-level victims',31,'orange',True,width=410,anchor='middle')
    a.rect(0,155,420,335,'white','line',6,layer='bg')
    a.text(16,183,'HyperNode West',29,'ink',True,width=320)
    switch(383,164)
    a.text(16,211,'Each training gang needs both Pods',22,'muted',width=390)
    for j,name in enumerate('ABCD'):
        y=228+j*63;data=GANGS[name];c=colors[name]
        a.rect(12,y,396,53,'white',c,5,dash=True)
        a.text(25,y+34,f'Job {name} (priority {data["priority"]})',24,c,True,width=225)
        for k,t in enumerate(data['pods']):pod(262+k*72,y+8,62,t,c,victim=t in SCATTERED_VICTIMS,h=37)
    a.text(210,536,'4 training jobs interrupted',29,'orange',True,width=420,anchor='middle')

    a.text(707,125,'Victim priority order',31,'blue',True,width=475,anchor='middle')
    for j,name in enumerate('ABCD'):
        x=470+j*121;c=colors[name];selected=name in SELECTED_GANGS
        a.rect(x,155,111,94,'#faece7' if selected else 'white','orange' if selected else 'light',5)
        a.text(x+55,185,f'{name} ({GANGS[name]["priority"]})',28,c,True,width=103,anchor='middle')
        for k,t in enumerate(GANGS[name]['pods']):pod(x+9+k*49,201,44,t,c,h=33,size=21)
    a.text(707,283,'Simulate within HyperNode West',28,'blue',True,width=485,anchor='middle')
    a.rect(470,300,475,102,'white','blue',6)
    a.text(707,330,'Try victim gangs A and B',28,'blue',True,width=451,anchor='middle')
    for j in range(4):pod(496+j*108,349,95,'S'+str(j))
    a.path([(945,367),(1046,367)],True,'blue')
    a.text(987,342,'Fits',25,'blue',True,width=83,anchor='middle')
    a.text(987,400,'Commit',22,'blue',True,width=83,anchor='middle')
    a.path([(707,402),(707,455)],True,'muted')
    a.text(739,438,'No fit',25,'muted',width=195)
    a.box('failed-trial',470,455,475,87,'No eviction','pale',30,True,'muted','light')

    a.text(1255,125,'Feasible placement',31,'blue',True,width=450,anchor='middle')
    a.rect(1030,155,450,285,'white','line',6,layer='bg')
    a.text(1046,183,'HyperNode West',29,'ink',True,width=330)
    switch(1443,164)
    for j,name in enumerate('CD'):
        x=1046+j*216;c=colors[name]
        a.rect(x,210,202,78,'white',c,5,dash=True)
        a.text(x+101,237,'Job '+name,26,c,True,width=185,anchor='middle')
        for k,t in enumerate(GANGS[name]['pods']):pod(x+11+k*94,246,86,t,c,h=33)
    a.rect(1046,308,418,88,'white','blue',5,dash=True)
    a.text(1255,337,'Gang S',28,'blue',True,width=390,anchor='middle')
    for j in range(4):pod(1056+j*102,350,92,'S'+str(j))
    a.text(1255,426,'A and B evicted as gangs',25,'blue',True,width=430,anchor='middle')
    a.rect(1030,455,450,101,'white','line',6,layer='bg')
    a.text(1046,483,'HyperNode East unchanged',27,'ink',True,width=418)
    for j,name in enumerate('EF'):
        x=1046+j*216;c=colors[name]
        a.rect(x,498,202,46,'white',c,4,dash=True)
        a.text(x+10,528,'Job '+name,23,c,True,width=70)
        for k,t in enumerate(GANGS[name]['pods']):pod(x+84+k*56,505,49,t,c,h=32,size=20)


def draw_comparison(a):
    a.text(0,34,'One workload, independent runs',32,'blue',True,width=1030)
    a.rect(1140,0,340,50,'sand',None,5)
    a.text(1310,34,'Comparisons planned',28,'amber',True,width=320,anchor='middle')
    # One fixed arrival stream is replayed unchanged for every scheduler.
    a.rect(0,95,360,350,'white','line',6)
    a.text(180,137,'Workload definition',29,'blue',True,width=338,anchor='middle')
    for i,count in enumerate([2,4,2]):
        y=176+i*85
        a.text(17,y+42,'Arrival '+str(i+1),24,'ink',True,width=125)
        a.rect(150,y,191,65,'white','blue',4,dash=True)
        for j in range(count):
            w=35 if count==4 else 72
            a.rect(164+j*(w+10),y+17,w,32,'prefill','blue',3)
    a.text(180,479,'Fixed resource requests',27,'blue',True,width=360,anchor='middle')
    a.path([(360,297),(435,297)],True,'blue')

    a.rect(435,95,625,350,'pale','line',6,layer='bg')
    a.text(747,137,'One scheduler per run',31,'blue',True,width=595,anchor='middle')
    for x,w,text,active in [(455,175,'Volcano',True),(645,250,'Kubernetes',False),(910,130,'Others',False)]:
        a.box(text,x,164,w,51,text,'blue' if active else 'white',27,True,'white' if active else 'muted','blue' if active else 'light')
    for i,x in enumerate([475,675,875]):
        a.rect(x,252,155,135,'white','line',5)
        a.text(x+77,281,'Node '+str(i),25,'ink',True,width=137,anchor='middle')
        for r in range(2):
            for c in range(3):a.rect(x+13+c*45,300+r*36,38,28,'prefill','blue',2)
    a.text(747,424,'Matched capacity and policies',27,'blue',True,width=590,anchor='middle')
    a.path([(1060,297),(1140,297)],True,'blue')

    a.rect(1140,95,340,350,'white','line',6)
    a.text(1310,137,'Run report',30,'blue',True,width=312,anchor='middle')
    for y,text in [(195,'Scheduler version'),(237,'Configuration'),(299,'Scheduling latency'),(341,'Binding throughput'),(383,'Placement validity')]:
        a.text(1158,y,text,26,'ink',width=304)
    a.path([(1158,258),(1462,258)],False,'light')
    # The loop returns to the same isolated environment for a fresh run.
    a.path([(1310,445),(1310,510),(400,510),(400,385),(435,385)],True,'blue')
    a.text(845,551,'Reset state and replay for the next scheduler',30,'blue',True,width=1240,anchor='middle')


def draw_roadmap(a, assets):
    a.path([(750,0),(750,494)],False,'light')
    a.path([(0,247),(1480,247)],False,'light')
    entries=[
        (0,0,'Resource defragmentation','PodGroup-level relocation','Consolidate GPU capacity'),
        (780,0,'HyperNode and SubGroups','kube-scheduler extender','SubGroup affinity / anti-affinity'),
        (780,267,'Ecosystem integration','Kubeflow, KubeRay, LWS','Gang and topology support'),
    ]
    for x,y,head,first,second in entries:
        a.text(x+234,y+42,head,31,'blue',True,width=466)
        a.text(x+234,y+113,first,28,'ink',width=466)
        a.text(x+234,y+157,second,28,'ink',width=466)

    a.text(234,309,'xPU Topology and DRA',31,'blue',True,width=466)
    for y,label in zip([346,381,416,451,486],[
        'Generic xPU topology',
        'DRA binpack',
        'DRA-backed extended resources',
        'DRA preemption and reclaim',
        'DRANET network allocation',
    ]):
        a.text(234,y,label,27,'ink',width=466)

    # Equal GPU slots before and after moving complete two-Pod groups.
    for row,occupancy in enumerate([[2,2,2],[4,2,0]]):
        y=66+row*96
        for i,used in enumerate(occupancy):
            x=12+i*68
            a.rect(x,y,60,61,'white','line',4)
            for j in range(4):a.rect(x+7+(j%2)*25,y+8+(j//2)*25,20,20,'prefill' if j<used else 'white','blue' if j<used else 'light',2)
    a.path([(102,129),(102,157)],True,'blue')

    # A shared HyperNode hierarchy, with two separate SubGroup domains.
    a.rect(863,65,66,35,'prefill','blue',4)
    for x in [807,907]:
        a.path([(896,100),(896,123),(x+39,123),(x+39,143)],False,'blue')
        a.rect(x,143,78,65,'white','green',5,dash=True)
        for k in range(2):a.rect(x+10+k*33,161,25,29,'mint','green',2)

    # Device interconnect and a network device use separate visual levels.
    for x in [12,121]:
        a.rect(x,334,88,91,'white','line',5)
        a.text(x+44,357,'xPU',22,'blue',True,width=76,anchor='middle')
        a.rect(x+14,370,60,39,'prefill','blue',3)
    a.path([(100,388),(121,388)],False,'blue')
    a.rect(67,454,89,33,'mint','green',3)
    a.text(111,478,'NIC',23,'green',True,width=77,anchor='middle')
    a.path([(56,425),(56,439),(111,439),(111,454)],False,'green')
    a.path([(165,425),(165,439),(111,439)],False,'green')

    # Reuse project marks, with the names in the adjacent roadmap text.
    for y,logo in [(318,'kubeflow.svg'),(379,'kuberay.png'),(440,'leaderworkerset.svg')]:
        a.image(831,y,130,51,assets/logo)
    a.text(0,546,'Further work on preemption, queue fairness and performance',28,'muted',width=1480)
