"""R15: approved structural edits and object-local explanatory labels.

Original China/EU bitmap figures remain intact. New authored geometry is SVG;
PowerPoint embeds its raster export so arrows and labels stay attached.
"""
from lxml import etree
from pathlib import Path
import base64, json


def apply_batch(arts, art, code, original, titles, subtitles, sources, assets):
    def renew(n):
        a=type(arts[n])(arts[n].name);arts[n]=a;subtitles[n]='';return a
    def label(a,x,y,w,text,c='blue',size=30,h=52):
        a.rect(x,y,w,h,'white',c,5)
        a.text(x+w/2,y+h/2+size*.34,text,size,c,True,width=w-24,anchor='middle')
    def pod(a,x,y,w,text,c='blue',h=43):
        a.box(f'{x}-{y}-{text}',x,y,w,h,text,'prefill' if c=='blue' else 'mint',24,True,c,c)
    def logo(a,name):
        a.image(0,0,95,58,assets/name)
    def prune(a,predicate):
        for layer in ['bg','edges','front']:
            out=[]
            for part in getattr(a,layer):
                r=etree.fromstring(('<g>'+part+'</g>').encode())
                for e in list(r):
                    if predicate(e):r.remove(e)
                out.append(''.join(etree.tostring(e,encoding='unicode') for e in r))
            setattr(a,layer,out)
    def bottom(a,y):
        prune(a,lambda e:e.tag in ['text','rect'] and float(e.get('y','-1'))>=y)

    # Three visibly distinct workload envelopes, with their scheduling need inside.
    a=renew(4)
    for x,w,t,c in [(0,720,'Training','blue'),(760,720,'Inference','green')]:
        a.rect(x,0,w,290,'white',c,10,layer='bg');a.text(x+22,38,t,34,c,True)
    for x,t in [(20,'PP stage 0'),(398,'PP stage 1')]:
        a.rect(x,65,300,142,'white','blue',5,dash=True)
        a.text(x+150,98,t,28,'blue',True,width=270,anchor='middle')
        for j in range(2):pod(a,x+14+j*140,131,132,'TP '+str(j))
    a.path([(320,153),(398,153)],True,'blue')
    a.text(359,130,'PP',23,'blue',True,width=60,anchor='middle')
    label(a,20,225,678,'TP / PP gangs + network locality')
    for x,w,t in [(780,276,'Prefill'),(1164,296,'Decode replicas')]:
        a.rect(x,65,w,142,'white','green',5,dash=True)
        a.text(x+w/2,98,t,28,'green',True,width=w-16,anchor='middle')
        for j in range(2):pod(a,x+14+j*(w-20)/2,131,(w-36)/2,('P' if x==780 else 'D')+str(j),'green')
    a.path([(1056,153),(1164,153)],True,'green');a.text(1110,130,'KV',23,'green',True,width=70,anchor='middle')
    label(a,780,225,680,'Role gangs + P/D locality','green')
    a.rect(0,315,1480,242,'white','orange',10,layer='bg')
    a.text(22,353,'Agents',34,'orange',True);a.text(22,394,'Bursty arrivals',27,'ink',True)
    a.path([(24,465),(48,465),(48,434),(75,434),(75,414),(105,414),(105,448),(140,448),(140,465),(181,465)],False,'orange')
    a.text(22,527,'Low startup latency',27,'orange',True,width=280)
    a.box('runtime',275,421,245,66,'Agent runtime','white',28,True,stroke='orange')
    a.path([(190,454),(275,454)],True,'orange')
    a.box('warm',650,346,290,65,'Warm pool reuse','white',27,True,stroke='orange')
    a.box('capacity',650,471,290,65,'Capacity request','white',26,True,stroke='orange')
    a.path([(520,454),(565,454),(565,379),(650,379)],True,'orange')
    a.path([(565,454),(565,503),(650,503)],True,'orange')
    a.text(587,365,'hit',23,'orange');a.text(579,532,'miss',23,'orange')
    a.box('fast',1100,471,358,65,'Fast Pod scheduling','white',28,True,stroke='blue')
    a.path([(940,503),(1100,503)],True,'blue');a.text(1020,484,'scale up',23,'blue',width=140,anchor='middle')
    a.path([(1279,471),(1279,379),(940,379)],True,'blue')
    a.text(1176,360,'Pool refill',27,'blue',True,width=250,anchor='middle')

    # The original architecture remains the center. Object-local white labels
    # and foreground leaders point at its controller and dynamic node slots.
    a=renew(5)
    original(a,'china-07-unified-architecture.png',0,0,1000,560,(0,115,3129,2051))
    label(a,354,26,292,'Profiles → paths',size=28,h=52)
    label(a,1040,120,436,'Strategy-based allocation',size=29,h=62)
    a.text(1258,229,'Live cluster / node state',29,'ink',width=420,anchor='middle')
    a.path([(1040,151),(990,151),(990,135),(500,135),(500,156)],False,'blue')
    a.front.append(a.edges.pop())
    label(a,1040,412,436,'NodeShard',size=32,h=62)
    a.text(1258,523,'Dynamic node pool membership',27,'ink',width=420,anchor='middle')
    a.path([(1040,443),(990,443),(990,548),(500,548),(500,527)],False,'blue')
    a.front.append(a.edges.pop())

    a=renew(6);titles[6]='NodeShard: Strategy-Driven Node Allocation'
    original(a,'china-09-dynamic-node-sharding.png',0,0,510,555)
    label(a,530,113,430,'Node metrics + strategy',size=30)
    a.path([(530,139),(486,139),(486,240),(413,240)],False,'blue')
    label(a,530,292,430,'Recompute desired nodes',size=29)
    a.path([(960,318),(986,318),(986,99),(1005,99)],True,'blue')
    code(a,1005,0,475,477,'NodeShard','''spec:
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
  - node2''',27,('nodesDesired','nodesInUse'),filename='nodeshard.yaml')
    label(a,1005,495,475,'Desired set / current use',size=30)
    a.text(745,433,'Rebalance candidate nodes',29,'ink',True,width=430,anchor='middle')
    a.text(745,476,'as cluster conditions change',27,'muted',width=430,anchor='middle')

    # New teaching page: nested workload hierarchy, not the p4 overview layout.
    a=art(25,'workload-gangs','Whole Workloads, Complete Compute Groups',chapter=2,
          source='Conceptual workload structure. PP/TP training and disaggregated inference examples; no controller API claimed.')
    for x,w,title,c in [(0,695,'Training job','blue'),(785,695,'Serving instance','green')]:
        a.rect(x,0,w,458,'white',c,9,layer='bg');a.text(x+w/2,39,title,32,c,True,width=w-32,anchor='middle')
    for i,y in enumerate([80,255]):
        a.rect(24,y,647,145,'white','blue',7,dash=True)
        a.text(48,y+35,'PP stage '+str(i),29,'blue',True)
        for j in range(4):pod(a,48+j*150,y+67,131,'TP '+str(j))
    a.path([(348,225),(348,255)],True,'blue')
    for x,w,t in [(808,255,'Prefill role'),(1091,366,'Decode role')]:
        a.rect(x,80,w,351,'white','green',6,dash=True)
        a.text(x+w/2,115,t,28,'green',True,width=w-20,anchor='middle')
    for x,y,w,t in [(825,154,221,'Replica 0'),(1108,154,332,'Replica 0'),(1108,292,332,'Replica 1')]:
        a.rect(x,y,w,112,'white','green',5)
        a.text(x+w/2,y+31,t,25,'green',True,width=w-20,anchor='middle')
        for j in range(2):pod(a,x+11+j*(w-16)/2,y+54,(w-30)/2,'TP '+str(j),'green')
    label(a,24,488,647,'Job gang → complete TP groups',size=31)
    label(a,808,488,649,'Serving gang → complete role replicas','green',size=30)

    a=renew(8)
    original(a,'china-14-podgroup-subgroup.png',0,0,1100,550,(0,80,1920,760))
    a.box('pg-note',1145,40,330,110,'PodGroup\nWorkload gang','white',30,True,'blue','blue')
    a.box('sg-note',1145,190,330,110,'SubGroup\nComplete replica','white',30,True,'blue','blue')
    a.path([(1145,95),(1066,95)],False,'blue')
    a.front.append(a.edges.pop())
    a.path([(1145,245),(1115,245),(1115,157),(1037,157)],False,'blue')
    a.front.append(a.edges.pop())
    # Captions are located over the corresponding grouping level, not a footer.

    a=renew(9)
    original(a,'china-16-hypernode.png',0,22,435,475,(0,55,465,515))
    code(a,480,0,470,433,'Parent HyperNode.spec','''tier: 2
tierName: spine
members:
- type: HyperNode
  selector:
    exactMatch:
      name: rack-a''',29,('type: HyperNode',),filename='hypernode-parent-spec.yaml')
    code(a,985,0,495,433,'Leaf HyperNode.spec','''tier: 1
tierName: leaf
members:
- type: Node
  selector:
    labelMatch:
      matchLabels:
        rack: rack-a''',29,('type: Node',),filename='hypernode-leaf-spec.yaml')
    label(a,480,463,470,'Groups child HyperNodes',size=31,h=67)
    label(a,985,463,495,'Groups Kubernetes nodes',size=31,h=67)

    a=renew(10)
    original(a,'china-17-multilevel-topology.png',0,52,900,452)
    label(a,35,0,830,'PodGroup · whole-instance placement at core',size=31,h=48)
    label(a,10,508,425,'Prefill · leaf locality',size=30,h=48)
    label(a,450,508,440,'Decode · spine locality','green',size=30,h=48)
    code(a,940,0,540,556,'PodGroup.spec · key fields','''minMember: 8
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
    highestTierName: spine''',28,('highestTierName',),filename='multilevel-topology-spec.yaml')

    # Retain the shared fabric; attach relation explanations to its domain edges.
    a=arts[11];bottom(a,520)
    label(a,4,516,892,'PodGroup anti-affinity · separate supernodes',size=31,h=43)
    a=arts[16]
    prune(a,lambda e:e.tag in ['text','rect'] and float(e.get('x','-1'))>=940)
    label(a,958,97,518,'1  Affinity · same supernode',size=30,h=66)
    a.text(1217,207,'Prefill + Decode',31,'ink',True,width=480,anchor='middle')
    label(a,958,302,518,'2  Anti-affinity · separate leaves','green',size=29,h=66)
    a.text(1217,412,'Decode replica 0 / replica 1',30,'ink',True,width=480,anchor='middle')
    # Small white tags next to the actual domain/group boundary.
    label(a,4,123,42,'1',size=28,h=39)
    label(a,197,412,35,'2','green',size=27,h=39)
    label(a,417,412,35,'2','green',size=27,h=39)

    # HyperNode-aware gang preemption: before/after, same node slots and domain.
    a=art(26,'gang-preemption','Gang Preemption Within a HyperNode',chapter=2,
          source='China 2026 slide 12 scenario; pkg/scheduler/actions/gangpreempt/gangpreempt.go; gang-aware-eviction-design.md. One Pod uses one GPU in this illustrative example.')
    label(a,0,0,1480,'Pending serving gang · 4 GPUs in one HyperNode',size=32)
    for x,phase in [(0,'Before'),(865,'After feasible placement')]:
        a.text(x+305,108,phase,32,'ink',True,width=610,anchor='middle')
        for dx,name in [(0,'HyperNode A'),(320,'HyperNode B')]:
            xx=x+dx;a.rect(xx,140,295,280,'white','blue' if dx==0 else 'light',7,layer='bg')
            a.text(xx+147,178,name,29,'blue' if dx==0 else 'ink',True,width=270,anchor='middle')
            a.text(xx+147,219,('Training job A' if x==0 else 'Serving gang') if dx==0 else 'Training job B',26,'ink',width=270,anchor='middle')
            for j in range(4):
                row,col=divmod(j,2);px=xx+20+col*137;py=243+row*74
                t=('A'+str(j) if x==0 else 'S'+str(j)) if dx==0 else ('B'+str(j) if j<2 else 'free')
                pod(a,px,py,117,t,'blue' if dx==0 else 'green',53)
    a.path([(615,281),(865,281)],True,'blue')
    a.text(740,230,'Simulate placement',26,'blue',True,width=240,anchor='middle')
    a.text(740,333,'Evict + nominate',26,'blue',True,width=230,anchor='middle')
    label(a,0,454,615,'Select a complete victim gang',size=31,h=70)
    label(a,865,454,615,'Admit the gang in the freed domain',size=30,h=70)

    # Kthena: show the real shared rolePolicy, not per-role invented fields.
    a=renew(14);titles[14]='Kthena: Configure Group and Role Topology'
    logo(a,'kthena.svg')
    original(a,'china-22-kthena-gang.png',0,78,750,440)
    code(a,790,0,690,555,'ModelServing.spec · excerpts','''schedulerName: volcano
replicas: 1
template:
  gangPolicy:
    minRoleReplicas:
      prefill: 1
      decode: 3
  networkTopology:
    groupPolicy:
      mode: hard
      highestTierName: spine
    rolePolicy:
      mode: hard
      highestTierName: leaf''',27,('groupPolicy','rolePolicy','highestTierName'),filename='kthena-modelserving-topology-spec.yaml')
    label(a,0,8,750,'',h=48) if False else None
    a.text(435,43,'ServingGroup / role replica',31,'blue',True,width=620,anchor='middle')
    label(a,0,510,750,'Group: spine    /    Role replica: leaf',size=29,h=48)
    a=art(27,'kthena-podgroup','Kthena: Carry Role Replicas into PodGroup',chapter=3,
          source='Kthena podgroupmanager/manager.go appendSubGroupPolicy and syncPodGroupNetworkTopology, main checked 2026-10-30.')
    logo(a,'kthena.svg');a.text(130,39,'One ServingGroup → one PodGroup',33,'blue',True,width=1320)
    code(a,0,80,610,390,'ModelServing.spec.template','''roles:
- name: prefill
  replicas: 1
  workerReplicas: 1
- name: decode
  replicas: 3
  workerReplicas: 1''',29,('replicas:','workerReplicas:'),filename='kthena-roles.yaml')
    label(a,0,494,610,'1 entry + 1 worker → 2-Pod SubGroup',size=29)
    # Explicit PG excerpt, selector/role identity shown in a separate mapping band.
    code(a,820,80,660,475,'PodGroup.spec · topology / gang','''minMember: 8
networkTopology:
  mode: hard
  highestTierName: spine
subGroupPolicy:
- name: decode
  minSubGroups: 3
  subGroupSize: 2
  networkTopology:
    mode: hard
    highestTierName: leaf''',27,('minMember','minSubGroups','subGroupSize','highestTierName'),filename='kthena-generated-podgroup-spec.yaml')
    a.path([(610,297),(820,297)],True,'blue')
    a.text(715,249,'Role replica',25,'blue',True,width=194,anchor='middle')
    a.text(715,349,'SubGroup',26,'blue',True,width=190,anchor='middle')

    # Ray input + output are real YAML; host membership shown underneath.
    a=renew(15);titles[15]='KubeRay: Map Multi-Host Worker Replicas'
    logo(a,'kuberay.png');a.text(132,39,'Worker replica → complete SubGroup',32,'blue',True,width=1300)
    code(a,0,75,590,330,'RayCluster.spec · excerpt','''enableInTreeAutoscaling: true
workerGroupSpecs:
- groupName: worker
  minReplicas: 2
  replicas: 2
  maxReplicas: 4
  numOfHosts: 2''',28,('minReplicas','numOfHosts'),filename='kuberay-raycluster-spec.yaml')
    code(a,810,75,670,438,'PodGroup.spec · worker excerpt','''subGroupPolicy:
- name: worker
  minSubGroups: 2
  subGroupSize: 2
  labelSelector:
    matchLabels:
      ray.io/group: worker
  matchLabelKeys:
  - ray.io/worker-group-replica-name''',27,('minSubGroups','subGroupSize','matchLabelKeys'),filename='kuberay-subgroup-spec.yaml')
    a.path([(590,250),(810,250)],True,'blue')
    a.text(700,209,'2 replicas',27,'blue',True,width=200,anchor='middle')
    a.text(700,304,'2 hosts each',27,'blue',True,width=200,anchor='middle')
    for i,x in enumerate([0,310]):
        a.rect(x,426,280,129,'white','blue',5,dash=True)
        a.text(x+140,460,'Replica '+str(i),28,'blue',True,width=255,anchor='middle')
        pod(a,x+12,481,121,'Host 0');pod(a,x+147,481,121,'Host 1')
    a.text(1145,551,'Replica label keeps the hosts together',29,'blue',True,width=650,anchor='middle')

    a=renew(23);titles[23]='Grove: Map PodGang Groups into Volcano'
    logo(a,'dynamo-grove.svg');a.text(130,39,'PodGang → PodGroup',32,'blue',True,width=1300)
    code(a,0,80,565,360,'Grove PodGang.spec · excerpt','''podGroups:
- name: prefill
  minReplicas: 2
- name: decode
  minReplicas: 4''',30,('minReplicas',),filename='grove-podgang-spec.yaml')
    code(a,790,80,690,475,'Volcano PodGroup.spec · excerpt','''minMember: 6
subGroupPolicy:
- name: decode
  subGroupSize: 4
  minSubGroups: 1
  labelSelector:
    matchLabels:
      grove.io/podclique: decode
  matchLabelKeys:
  - grove.io/podclique''',28,('minMember','subGroupSize','minSubGroups'),filename='grove-podgroup-spec.yaml')
    a.path([(565,275),(790,275)],True,'blue')
    a.text(677,224,'Group → policy',25,'blue',True,width=213,anchor='middle')
    a.text(677,325,'Minimum Pods',25,'blue',True,width=210,anchor='middle')
    label(a,0,467,565,'2 Prefill + 4 Decode → minMember 6',size=28,h=79)

    # Future integrations: explanatory line stays aligned with its controller.
    a=arts[13]
    prune(a,lambda e:e.tag=='rect' and e.get('fill') in ['#e3edf8','#164f89'] and float(e.get('x','-1'))>=570)
    # White bounded labels replace the colored strips without changing content.
    for y in [87,256,425]:a.rect(570,y,910,63,'white','light',5,layer='bg')

    # Measurement annotations sit with their output, instead of a page-wide footer.
    a=arts[18];bottom(a,520)
    label(a,970,516,510,'Scheduling latency / throughput',size=29,h=43)
    a=arts[19];bottom(a,456)
    label(a,0,468,535,'Same arrivals, groups, resources',size=29,h=75)
    label(a,1000,468,480,'Latency / gang completion',size=29,h=75)

    a=renew(21);titles[21]='v1.17: Placement, Preemption, and Performance'
    rows=[('Preemption','Fewer unnecessary evictions','Gang admission + victim selection','Topology-aware reclaim · in review'),
          ('Group placement','SubGroup affinity / anti-affinity','Locality and replica isolation','API and integration work · planned'),
          ('Performance','Cache locks + queue status cost','Replay workloads and profile bottlenecks','Cross-scheduler / topology tests · next')]
    for i,(area,head,body,status) in enumerate(rows):
        y=i*185
        if i:a.path([(0,y-13),(1480,y-13)],False,'light')
        a.text(0,y+37,area,33,'blue',True,width=350)
        a.text(380,y+37,head,32,'ink',True,width=1080)
        a.text(380,y+86,body,29,'ink',width=1080)
        a.text(380,y+135,status,27,'muted',width=1080)
    sources[21]='v1.17 roadmap #6166 checked 2026-10-30; #5984/#5994/#5946/#5347/#5036/#5921 open; topology-aware reclaim PR #5920 open; #6066 and #6094 merged. Performance umbrella #5494. Benchmark expansion reflects maintainer intent.'

    # One closing page. Original partner pixels are cropped inside consistent frames.
    a=renew(24);titles[24]='Volcano Community';folder=assets/'community'
    items=json.loads((folder/'partners.json').read_text())
    for i,item in enumerate(items):
        x=(i%8)*185;y=(i//8)*88
        a.rect(x,y,170,76,'white','light',1)
        a.rect(x+1,y+1,168,5,'#d9dee5',None,0)
        p=folder/item['file']
        from PIL import Image
        im=Image.open(p);iw,ih=im.size
        # Existing frames are mostly monochrome perimeter pixels; retain the
        # content crop selected during asset extraction, then inset its border.
        l,t,r,b=item['crop'];cx=iw*l;cy=ih*t;cw=iw*(1-l-r);ch=ih*(1-t-b)
        # Strip only embedded card borders, then find logo ink. These are
        # viewport coordinates; the original logo image is never rewritten.
        inset=min(cw,ch)*.075 if i in [1,5,7,8,9,13,16,23,25,27,31] else 0
        cx+=inset;cy+=inset;cw-=2*inset;ch-=2*inset
        rgba=im.convert('RGBA');bounds=[]
        for yy in range(int(cy),min(ih,int(cy+ch)+1)):
            for xx in range(int(cx),min(iw,int(cx+cw)+1)):
                rr,gg,bb,aa=rgba.getpixel((xx,yy))
                if aa>80 and min(rr,gg,bb)<220:bounds.append((xx,yy))
        if bounds:
            x0=min(q[0] for q in bounds);x1=max(q[0] for q in bounds)+1
            y0=min(q[1] for q in bounds);y1=max(q[1] for q in bounds)+1
            pad=2;cx=max(0,x0-pad);cy=max(0,y0-pad);cw=min(iw,x1+pad)-cx;ch=min(ih,y1+pad)-cy
        uri='data:'+('image/jpeg' if p.suffix=='.jpg' else 'image/png')+';base64,'+base64.b64encode(p.read_bytes()).decode()
        a.front.append(f'<svg x="{x+8}" y="{y+13}" width="154" height="54" viewBox="{cx} {cy} {cw} {ch}" preserveAspectRatio="xMidYMid meet"><image width="{iw}" height="{ih}" href="{uri}"/></svg>')
    a.path([(0,364),(1480,364)],False,'light')
    a.text(0,426,'Thank you',38,'ink',True,width=450);a.text(0,482,'Questions & contributions',30,'blue',width=475)
    source=folder/'china-25-community-qr.png';uri='data:image/png;base64,'+base64.b64encode(source.read_bytes()).decode()
    for i,((cx,cy,cw,ch),lab) in enumerate(zip([(24,66,182,188),(280,62,184,192),(548,58,192,196)],['volcano.sh','GitHub','Slack'])):
        x=570+i*305;a.rect(x,378,160,160,'white',None,0)
        a.front.append(f'<svg x="{x+7}" y="385" width="146" height="146" viewBox="{cx} {cy} {cw} {ch}" preserveAspectRatio="xMidYMid meet"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="white"/><image width="818" height="256" href="{uri}"/></svg>')
        a.text(x+80,557,lab,25,'blue',True,width=270,anchor='middle')
    del arts[22]
    sources[24]='China slide 25 logos and QR assets. Single community / Q&A ending, consistent frames and gray top strips. Logos remain original image bytes in SVG viewports.'
    return [1,2,3,4,5,6,7,25,8,9,10,26,11,16,12,14,27,15,23,13,17,18,19,20,21,24]
