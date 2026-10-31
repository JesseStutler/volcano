"""Approved review: workload mappings, gang victims and concise visual labels."""
from lxml import etree
from PIL import Image
from collections import Counter


def refine(arts, code, original, titles, subtitles, sources, assets):
    def renew(n):
        a = type(arts[n])(arts[n].name)
        arts[n] = a
        subtitles[n] = ''
        return a

    def badge(a, x, y, w, name, logo, fill='prefill'):
        a.rect(x, y, w, 62, fill, None, 5)
        a.image(x+12, y+7, 58, 48, assets/logo)
        a.text(x+85, y+41, name, 31, 'blue', True, width=w-100)

    def tag(a, x, y, w, title, color='blue', h=54, size=29):
        a.rect(x, y, w, h, 'white', color, 5)
        a.text(x+w/2, y+h/2+size*.34, title, size, color, True,
               width=w-20, anchor='middle')

    def compact_pod(a, x, y, w, label, color='blue', h=38, faded=False):
        fill = 'prefill' if color == 'blue' else 'mint' if color == 'green' else '#faece7'
        a.rect(x, y, w, h, 'pale' if faded else fill, 'light' if faded else color, 3)
        a.text(x+w/2, y+h/2+8, label, 23, 'muted' if faded else color,
               True, width=w-6, anchor='middle')

    def raster_label(a, file, scale, ox, oy, rect, text, size, color='blue', bold=True):
        # Overlay only a text region, preserving the underlying source bitmap.
        x,y,w,h=rect
        im=Image.open(assets/'reused'/file).convert('RGB')
        # The dominant fill avoids accidentally sampling an old glyph or border.
        fill='#%02x%02x%02x' % Counter(im.crop((x,y,x+w,y+h)).getdata()).most_common(1)[0][0]
        a.rect(ox+x*scale,oy+y*scale,w*scale,h*scale,fill,None,0)
        a.text(ox+(x+w/2)*scale,oy+(y+h/2)*scale+size*.34,text,size,color,bold,
               width=w*scale-2,anchor='middle')

    # Keep the original China group drawing; split its teaching labels.
    a = renew(8)
    original(a, 'china-14-podgroup-subgroup.png', 0, 0, 1480, 560)
    a.rect(129, 0, 1222, 56, 'white', None, 0)
    tag(a, 35, 0, 690, 'PodGroup: whole job or serving gang')
    tag(a, 755, 0, 690, 'SubGroup: TP group or role replica', 'green')
    # Remove dot separators and textual arrows embedded in the reused PNG.
    sc=560/880;ox=(1480-1920*sc)/2
    for rect,text,size in [
        ((80,98,440,36),'Training PodGroup',18),
        ((1000,98,470,36),'Serving PodGroup',18),
        ((160,211,280,33),'TP SubGroup',16),
        ((580,211,280,33),'TP SubGroup',16),
        ((1080,169,280,35),'Prefill SubGroup',16),
        ((1480,169,280,35),'Decode SubGroup',16),
        ((180,324,240,23),'Placed in Leaf A',13),
        ((600,324,240,23),'Placed in Leaf B',13),
        ((1100,310,240,27),'Placed in Leaf C',13),
        ((1500,310,240,27),'Placed in Leaf D',13),
        ((185,709,230,31),'Leaf A (TP / PP0)',15),
        ((605,709,230,31),'Leaf B (TP / PP1)',15),
        ((1100,709,240,31),'Prefill on Leaf C',15),
        ((1500,709,240,31),'Decode on Leaf D',15),
    ]:raster_label(a,'china-14-podgroup-subgroup.png',sc,ox,0,rect,text,size)

    a = renew(10)
    original(a, 'china-17-multilevel-topology.png', 0, 64, 900, 430)
    tag(a, 12, 0, 876, 'Different SubGroups, different topology constraints', size=29)
    tag(a, 12, 506, 420, 'Prefill at leaf tier', size=29, h=50)
    tag(a, 466, 506, 422, 'Decode at spine tier', 'green', size=29, h=50)
    code(a, 940, 0, 540, 556, 'PodGroup.spec (example)', '''minMember: 8
networkTopology:
  mode: hard
  highestTierName: core
subGroupPolicy:
- name: prefill
  subGroupSize: 4
  networkTopology:
    highestTierName: leaf
- name: decode
  subGroupSize: 4
  networkTopology:
    highestTierName: spine''', 28, ('highestTierName',), filename='multilevel-topology-spec.yaml')

    # The identical initial resources support either choice of four victims.
    # A has four Pods in HyperNode A. B has two Pods in each HyperNode.
    a = renew(26)
    a.rect(0, 0, 1480, 80, 'prefill', None, 5)
    a.text(20, 32, 'Incoming gang S', 31, 'blue', True, width=360)
    a.text(20, 65, 'minMember: 4', 25, 'blue', width=320, mono=True)
    for j in range(4):
        compact_pod(a, 380+j*83, 21, 69, 'S'+str(j))
    a.text(760, 32, 'Four Pods in one spine HyperNode', 29, 'blue', True, width=700)
    a.text(760, 65, 'highestTierName: spine', 25, 'blue', width=700, mono=True)

    def cable(points):
        a.path(points, False, 'light')
        a.routes[-1]['kind'] = 'fabric'

    def switch(cx, y):
        original(a, 'china-17-multilevel-topology.png', cx-21, y, 42, 30, (818,110,158,114))
        symbol=a.front.pop(); clip=f'victim-switch-{cx}-{y}'
        scale=42/158; left=cx-21; top=y+(30-114*scale)/2
        pts=' '.join(f'{left+px*scale},{top+py*scale}' for px,py in [(48,0),(158,0),(158,52),(118,114),(0,114),(0,56)])
        a.front.append(f'<defs><clipPath id="{clip}"><polygon points="{pts}"/></clipPath></defs><g clip-path="url(#{clip})">{symbol}</g>')

    cases = [
        ('Before', ['A0','A1','A2','A3','B0','B1'], ['B2','B3','free','free'],
         'Two complete training gangs', 'A: 4 Pods     B: 4 Pods'),
        ('Pod-level victims', ['S0','S1','A2','A3','S2','S3'], ['B2','B3','free','free'],
         'Two training jobs interrupted', 'Evict 2 Pods from A and 2 from B'),
        ('Gang-aware victims', ['S0','S1','S2','S3','B0','B1'], ['B2','B3','free','free'],
         'Training gang B stays complete', 'Evict the complete 4-Pod gang A'),
    ]
    for i,(heading,slots_a,slots_b,outcome,detail) in enumerate(cases):
        x=i*505; w=470; c='orange' if i==1 else 'blue'
        a.text(x+w/2, 127, heading, 32, c, True, width=w-10, anchor='middle')
        a.rect(x, 155, w, 190, 'white', 'line', 7, layer='bg')
        a.text(x+18, 186, 'HyperNode A (spine)', 25, 'ink', True, width=430)
        switch(x+235, 200)
        for leaf in (x+78, x+235, x+392):
            cable([(x+235,230),(leaf,244)]);switch(leaf,244)
        for j,t in enumerate(slots_a):
            px=x+13+j*75
            cable([(x+78+(j//2)*157,274),(px+34,292)])
            if t.startswith('S'):color='blue'
            elif t.startswith('A'):color='orange'
            else:color='green'
            compact_pod(a, px, 292, 68, t, color, faded=(i==1 and t.startswith('A')))
        # A complete gang is outlined as one victim/admission unit.
        if i in (0,2):
            a.rect(x+8, 285, 299, 51, 'none', 'orange' if i==0 else 'blue', 5, dash=True)
        a.rect(x, 367, w, 111, 'white', 'line', 7, layer='bg')
        a.text(x+18, 397, 'HyperNode B (spine)', 25, 'ink', True, width=430)
        for j,t in enumerate(slots_b):
            px=x+23+j*111
            if t=='free':
                a.rect(px, 421, 92, 38, 'white', 'light', 3)
                a.text(px+46, 448, t, 23, 'muted', width=85, anchor='middle')
            else:compact_pod(a, px, 421, 92, t, 'green', faded=i==1)
        a.text(x+w/2, 516, outcome, 28, c, True, width=w-12, anchor='middle')
        a.text(x+w/2, 554, detail, 24, 'ink', width=w-12, anchor='middle')
    sources[26] = 'China 2026 gang-preemption motivation. Authored comparison with identical initial capacity: gang A has 4 Pods in HyperNode A; gang B has 2 Pods in each domain. Pod-level victims interrupt both jobs, whole-gang victims preserve B. Illustration, not a measured optimality claim.'

    # A project badge separates each controller's identity from the diagrams.
    a=arts[14]
    a.rect(0, 0, 750, 65, 'white', None, 0)
    badge(a, 0, 0, 750, 'Kthena', 'kthena.svg')
    # The reused bitmap has a tiny dot-separated footer; replace that footer.
    a.rect(0, 466, 750, 44, 'white', None, 0)
    for rect,text,size,color in [
        ((609,143,326,36),'ServingGroup 0 PodGroup',9,'purple'),
        ((597,244,300,32),'SubGroup: prefill-0',9,'green'),
        ((109,278,245,23),'1 replica with 2 Pods',7,'muted'),
        ((109,480,310,25),'3 replicas with 2 Pods each',7,'muted'),
        ((594,369,340,26),'minSubGroups: 1, subGroupSize: 2',7,'muted'),
        ((572,437,340,31),'3 Decode SubGroups',9,'blue'),
        ((596,528,230,28),'SubGroup: decode-0',8,'blue'),
        ((596,625,230,28),'SubGroup: decode-1',8,'blue'),
        ((596,722,230,28),'SubGroup: decode-2',8,'blue'),
        ((572,838,399,27),'Decode replicas grouped by role-id',7,'muted'),
        ((1360,148,307,33),'PodGroup at spine tier',9,'blue'),
        ((1696,154,115,23),'hard',6,'muted'),
        ((1424,321,126,22),'rolePolicy: hard',6,'green'),
        ((1666,321,126,22),'rolePolicy: hard',6,'blue'),
    ]:raster_label(a,'china-22-kthena-gang.png',750/1920,0,87.0625,rect,text,size,color)

    subtitles[11]='Separate matching PodGroups across supernodes'
    a=arts[16]
    a.rect(1140,0,340,46,'sand',None,5)
    a.text(1310,31,'Planned',27,'amber',True,width=320,anchor='middle')

    def mapping_badges(a, project, logo):
        badge(a, 0, 0, 700, project, logo)
        badge(a, 780, 0, 700, 'Volcano', 'volcano-icon.svg', 'mint')

    def group_shell(a, x, title):
        a.rect(x, 382, 700, 176, 'white', 'blue', 7, layer='bg')
        a.text(x+18, 412, title, 27, 'blue', True, width=664)

    def small_group(a, x, w, name, pods, color='blue', subgroup=False):
        a.rect(x, 429, w, 116, 'white', color, 5, dash=subgroup)
        a.text(x+w/2, 456, name, 25, color, True, width=w-10, anchor='middle')
        pw=(w-22-(len(pods)-1)*6)/len(pods)
        for j,t in enumerate(pods):
            px=x+11+j*(pw+6)
            a.rect(px, 478, pw, 43, 'prefill' if color=='blue' else 'mint', color, 3)
            a.text(px+pw/2, 507, t, 21, color, True, width=pw-3, anchor='middle')

    # Kthena: four role replicas are visible as four complete SubGroups.
    a=renew(27);mapping_badges(a, 'Kthena', 'kthena.svg')
    code(a,0,80,700,280,'ModelServing.spec.template', '''roles:
- name: prefill
  replicas: 1
  workerReplicas: 1
- name: decode
  replicas: 3
  workerReplicas: 1''',26,('replicas:','workerReplicas:'),filename='kthena-roles.yaml')
    code(a,780,80,700,288,'PodGroup.spec (role policies)', '''minMember: 8
subGroupPolicy:
- name: prefill
  minSubGroups: 1
  subGroupSize: 2
- name: decode
  minSubGroups: 3
  subGroupSize: 2''',24,('minMember','minSubGroups','subGroupSize'),filename='kthena-podgroup-overview.yaml')
    for ox,heading in [(0,'ServingGroup: 4 role replicas'),(780,'PodGroup: 4 SubGroups, 8 Pods')]:
        group_shell(a,ox,heading)
        for j,name in enumerate(['prefill-0','decode-0','decode-1','decode-2']):
            small_group(a,ox+12+j*172,160,name,['E','W'],'green' if j==0 else 'blue',subgroup=ox>0)
    a.path([(706,487),(774,487)], True, 'blue')

    # KubeRay: include the head SubGroup as well as both worker replicas.
    a=renew(15);mapping_badges(a,'KubeRay','kuberay.png')
    code(a,0,80,700,280,'RayCluster.spec', '''enableInTreeAutoscaling: true
workerGroupSpecs:
- groupName: worker
  minReplicas: 2
  replicas: 2
  maxReplicas: 4
  numOfHosts: 2''',26,('minReplicas','numOfHosts'),filename='kuberay-raycluster-spec.yaml')
    code(a,780,80,700,280,'PodGroup.spec (worker policy)', '''minMember: 5
subGroupPolicy:
- name: worker
  minSubGroups: 2
  subGroupSize: 2
  matchLabelKeys:
  - ray.io/worker-group-replica-name''',25,('minMember','minSubGroups','subGroupSize'),filename='kuberay-podgroup-overview.yaml')
    for ox,heading in [(0,'RayCluster: head and worker replicas'),(780,'PodGroup: 3 SubGroups, 5 Pods')]:
        group_shell(a,ox,heading)
        small_group(a,ox+12,154,'headgroup',['Head'],'green',ox>0)
        small_group(a,ox+182,247,'worker 0',['Host 0','Host 1'],subgroup=ox>0)
        small_group(a,ox+445,243,'worker 1',['Host 0','Host 1'],subgroup=ox>0)
    a.path([(706,487),(774,487)], True, 'blue')

    a=renew(23);mapping_badges(a,'Grove','dynamo-grove.svg')
    code(a,0,80,700,280,'PodGang.spec', '''podGroups:
- name: prefill
  minReplicas: 2
- name: decode
  minReplicas: 4''',28,('minReplicas',),filename='grove-podgang-spec.yaml')
    code(a,780,80,700,288,'PodGroup.spec (group policies)', '''minMember: 6
subGroupPolicy:
- name: prefill
  minSubGroups: 1
  subGroupSize: 2
- name: decode
  minSubGroups: 1
  subGroupSize: 4''',24,('minMember','minSubGroups','subGroupSize'),filename='grove-podgroup-overview.yaml')
    for ox,heading in [(0,'PodGang: 2 named groups'),(780,'PodGroup: 2 SubGroups, 6 Pods')]:
        group_shell(a,ox,heading)
        small_group(a,ox+12,238,'prefill',['P0','P1'],'green',ox>0)
        small_group(a,ox+266,422,'decode',['D0','D1','D2','D3'],subgroup=ox>0)
    a.path([(706,487),(774,487)],True,'blue')

    a=renew(13)
    rows=[('RoleBasedGroup (RBG)','rbg.svg','Integration in progress','RoleInstance gang mapping','HyperNode tree queries'),
          ('Kubeflow','kubeflow.svg','Planned','Training group structure','Network topology constraints'),
          ('LeaderWorkerSet (LWS)','leaderworkerset.svg','Planned','Multi-role and multi-group support','Relationships across groups')]
    for i,(name,logo,status,head,detail) in enumerate(rows):
        y=i*185
        a.rect(0,y,505,155,'prefill',None,6)
        a.image(12,y+22,88,88,assets/logo)
        a.text(122,y+54,name,29,'blue',True,width=367)
        a.text(122,y+113,status,25,'purple',True,width=366)
        a.text(555,y+54,head,32,'ink',True,width=915)
        a.text(555,y+113,detail,30,'blue',width=915)
        if i<2:a.path([(555,y+166),(1480,y+166)],False,'light')
    sources[13] += ' RBG integration including HyperNode tree queries is ongoing, as confirmed by the maintainer in this review.'

    # A comparison plan, not a fabricated results chart.
    a=renew(19)
    a.text(0,34,'Matched workloads and cluster capacity',32,'blue',True,width=1000)
    a.rect(1140,0,340,50,'sand',None,5)
    a.text(1310,34,'Comparisons planned',28,'amber',True,width=320,anchor='middle')
    xcols=[0,500,750,1080,1480]
    for x,w,head in [(0,500,'Scenario'),(500,250,'Volcano'),(750,330,'Kubernetes scheduler'),(1080,400,'Measurements')]:
        a.rect(x,77,w,61,'prefill',None,0)
        a.text(x+16,116,head,27,'blue',True,width=w-28)
    rows=[('Bursty arrivals','Planned','Planned','Tail latency\nBacklog recovery'),
          ('Mixed workloads','Planned','Planned','Binding throughput\nWait time by workload'),
          ('Complete gangs','Planned','Capability check','Gang completion\nPartial placement'),
          ('Network topology','Planned','Capability check','Placement validity\nGang admission latency')]
    for i,(name,v,k,metrics) in enumerate(rows):
        y=138+i*89
        a.rect(0,y,1480,89,'white' if i%2 else 'pale',None,0,layer='bg')
        for x in xcols[1:-1]:a.path([(x,y),(x,y+89)],False,'light')
        a.text(157,y+52,name,29,'ink',True,width=325)
        a.text(625,y+52,v,27,'blue',True,width=230,anchor='middle')
        a.text(915,y+52,k,26,'muted',width=310,anchor='middle')
        a.text(1100,y+35,metrics,25,'ink',width=365)
        if i==0:
            a.path([(18,y+65),(37,y+65),(37,y+47),(57,y+47),(57,y+24),(78,y+24),(78,y+57),(101,y+57),(101,y+65),(130,y+65)],False,'blue')
        elif i==1:
            for j,(ww,c) in enumerate([(95,'blue'),(52,'green'),(75,'orange')]):
                a.rect(23,y+17+j*22,ww,13,c,None,2)
        elif i==2:
            a.rect(17,y+15,114,62,'white','blue',4,dash=True)
            for j in range(3):a.rect(27+j*33,y+33,25,27,'prefill','blue',2)
        else:
            a.rect(64,y+15,22,15,'blue',None,2)
            a.path([(75,y+30),(75,y+45),(34,y+45),(34,y+57)],False,'blue')
            a.path([(75,y+45),(115,y+45),(115,y+57)],False,'blue')
            for xx in (23,104):a.rect(xx,y+57,22,15,'prefill','blue',2)
    a.text(0,546,'Find the scenarios each scheduler handles well',29,'blue',True,width=1000)
    a.text(1480,546,'More schedulers to follow',25,'muted',width=460,anchor='end')

    titles.update({
        5:'Unified Scheduling Framework',
        6:'Dynamic Node Sharding',
        8:'Multi-Level Gang Scheduling',
        9:'HyperNode: Network Topology',
        11:'PodGroup Anti-Affinity',
        16:'SubGroup Affinity and Anti-Affinity',
        25:'Training and Inference Groups',
        26:'Gang-Aware Preemption',
        14:'Kthena: Group and Role Topology',
        27:'Kthena: Role Replica Mapping',
        15:'KubeRay: Multi-Host Replica Mapping',
        23:'Grove: PodGang Mapping',
        13:'Ecosystem Roadmap',
        18:'Scheduling Benchmark Framework',
        19:'Cross-Scheduler Benchmarks',
        20:'Workload and Topology Test Matrix',
        21:'v1.17 Priorities',
        24:'Volcano Users',
    })
    # Edit wording at text nodes so neither arrow symbols nor dot separators
    # survive in author-created labels. Geometric diagram arrows stay intact.
    replacements={
        'Gang scheduling · network locality':'Gang scheduling with network locality',
        'Profiles → paths':'Profiles select paths',
        'NodeShard · spec / status':'NodeShard spec and status',
        'Job gang → complete TP groups':'Complete TP groups within a job',
        'Serving gang → complete role replicas':'Complete replicas within a serving gang',
        'Supernode A · PG 0':'Supernode A (PG 0)',
        'Supernode B · PG 1':'Supernode B (PG 1)',
        'Supernode A · one PG':'Supernode A (one PG)',
        'Supernode B · spare':'Supernode B (spare)',
        'PodGroup.spec · key fields':'PodGroup.spec (key fields)',
        'PodGroup anti-affinity · separate supernodes':'Separate supernodes with PodGroup anti-affinity',
        '1 Affinity · same supernode':'1  Affinity within a supernode',
        '2 Anti-affinity · separate leaves':'2  Anti-affinity across leaves',
        'ModelServing.spec · excerpts':'ModelServing.spec (excerpt)',
        'Resources · topology':'Resources and topology',
        'Pods · PodGroups · HyperNodes':'Pods, PodGroups, HyperNodes',
        'Arrival rate · capacity':'Arrival rate and capacity',
        'Group size · fragmentation':'Group size and fragmentation',
        'Tier limits · domains':'Tier limits and domains',
        'Gang · anti-affinity':'Gang with anti-affinity',
        'Topology-aware reclaim · in review':'Topology-aware reclaim under review',
        'API and integration work · planned':'API and integration work planned',
        'Cross-scheduler / topology tests · next':'Scheduler comparisons and topology tests next',
    }
    for a in arts.values():
        for layer in ('bg','edges','front'):
            updated=[]
            for part in getattr(a,layer):
                r=etree.fromstring(('<g>'+part+'</g>').encode())
                for e in r.iter():
                    if e.text:
                        for old,new in replacements.items():e.text=e.text.replace(old,new)
                        if e.tag in ('text','tspan'):
                            assert not any(c in e.text for c in '→·•|'),(a.name,e.text)
                updated.append(''.join(etree.tostring(e,encoding='unicode') for e in r))
            setattr(a,layer,updated)
