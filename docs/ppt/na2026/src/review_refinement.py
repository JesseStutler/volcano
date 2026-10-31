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

    from review_focus import draw_preemption, draw_comparison, draw_roadmap
    a=renew(26)
    draw_preemption(a, original)
    sources[26]='Illustrative six-job scenario. Each two-Pod training gang stays inside one HyperNode. Four scattered victim Pods interrupt four West jobs; gangs A and B release the same four slots. Priority-ordered gang candidates are simulated within the preemptor domain before committing. Based on gangpreempt.go and actions/utils/bundle.go and simulate.go; not a scheduler benchmark result.'

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
    rows=[('RoleBasedGroup (RBG)','rbg.svg','Integration in progress','PodGroup and SubGroup integration','HyperNode tree queries'),
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
    sources[13] += ' RBG PodGroup and SubGroup integration, including HyperNode tree queries, is ongoing, as confirmed by the maintainer in this review.'

    a=renew(19)
    draw_comparison(a)
    sources[19]='Maintainer comparison plan: replay one workload definition in reset, isolated runs with one scheduler at a time; record versions, configuration and common measurements. Planned comparisons, no invented results.'
    a=renew(21)
    draw_roadmap(a, assets)
    sources[21]='v1.17 roadmap #6166. Selected directions for this session, not an official priority ranking: PodGroup-level resource defragmentation #3948; HyperNode extender #6028 and SubGroup affinity #5347; generic xPU topology #5751 and DRA/DRANET integration; ecosystem expansion. Preemption/reclaim, queue fairness and performance are also tracked.'

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
        21:'v1.17 Roadmap',
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
