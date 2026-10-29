"""r6 editorial pass: diagrams and short labels, with explanation in notes."""
from pathlib import Path
from lxml import etree
import base64,json


def simplify(arts,art,titles,C,assets):
    removed={}
    drop={
      4:{'Schedule complete groups and their locality; keep latency-sensitive capacity ready.'},
      5:{'01','02','03','Workload paths','Local coordination','Shared node access',
         'Batch-oriented scheduling and a Pod-oriented fast path.','Parallel workers use Binder conflict checks.','NodeShard coordinates candidate-node pools.'},
      6:{'Desired membership ≠ immediate use','Coordinators reconcile node access.'},
      9:{'PHYSICAL FABRIC'},
      14:{'Pod templates omitted.'},
      15:{'One replica label → one complete SubGroup','Two replicas × two hosts = four worker Pods','worker registration / RPC'},
      16:{'Keep KV exchange inside the same supernode.','Keep complete replicas on separate leaf domains.'},
      13:{'Extend the existing gang integration.','Build on the Volcano scheduler plugin.','Connect group relationships to scheduling.'},
      18:{'SCENARIO','CLUSTER UNDER TEST','OBSERVATION','Version + resources + topology'},
      19:{'ONE WORKLOAD, REPLAYED','Same arrivals · groups · resources','Pin versions + config',
          'Compare latency · binding throughput · completed gangs · placement',
          '¹ Planned comparison set; match workload semantics and record unsupported constraints.'},
      20:{'Warm-pool capacity requests','Backlog recovery','Few large vs. many small groups','Binding throughput',
          'Locality + gang + anti-affinity','Gang completion + latency'},
    }
    edits={
      'TRAINING':'Training','INFERENCE':'Inference','AGENTS':'Agents',
      'PodGroup · pipeline stages':'PodGroup','PodGroup · disaggregated serving':'PodGroup',
      'Complete TP / PP gangs + network locality':'TP / PP gangs','Role groups + topology-aware placement':'Role groups and network locality',
      'reuse ready capacity':'Reuse','replenish the pool':'Replenish',
      'PROPOSED · SUBGROUP RELATIONSHIPS':'Proposed',
      'Affinity · supernode':'Affinity at supernode level','Anti-affinity · leaf':'Anti-affinity at leaf level',
      'Prefill + Decode':'Prefill and Decode','Decode replica 0 + replica 1':'Decode replicas',
      'IN PROGRESS':'In progress','PLANNED':'Planned',
      'Training groups + topology':'Training groups and topology',
      'Multi-role / multi-group support':'Multi-group support',
      'CROSS-SCHEDULER TESTING':'Planned',
      'Kubernetes scheduler¹':'kube-scheduler','Other schedulers¹':'Other schedulers',
      'TEST SHAPE':'Scenario','WHAT TO VARY':'Vary','WHAT TO OBSERVE':'Measure',
      'Arrival rate / spare capacity':'Arrival rate','SubGroup size / fragmentation':'Group size and fragmentation',
      'Tier limits / available domains':'Topology constraints',
      'NodeShard · spec / status excerpt':'NodeShard',
      'Parent · HyperNode.spec':'Parent HyperNode','Leaf · HyperNode.spec':'Leaf HyperNode',
      'PodGroup.spec · key fields':'PodGroup.spec',
      'ModelServing.spec · excerpt':'ModelServing.spec',
      'PodGroup.spec · generated grouping':'PodGroup.spec',
      'RayCluster · worker group':'Ray worker group',
      'JOBS':'Jobs','REPLICAS':'Replicas','MIN_AVAILABLE':'Minimum gang size',
      'Kind + KWOK / existing cluster':'Kind / KWOK or a real cluster',
      'Pods · PodGroups · HyperNodes':'Pods, PodGroups, HyperNodes',
      'PodGang minimum = 2 + 4 = 6 Pods':'6 Pods',
    }
    for n,a in arts.items():
        removed[n]=[];front=[]
        for fragment in a.front:
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                y=float(e.get('y','0'));mono='Mono' in e.get('font-family','')
                if label in drop.get(n,set()) or (y>=530 and not mono):
                    removed[n].append(label);wrapper.remove(e);continue
                if label in edits:
                    removed[n].append(label)
                    for child in list(e):e.remove(child)
                    e.text=edits[label]
                    if label in ['JOBS','REPLICAS','MIN_AVAILABLE']:e.set('font-family','Liberation Sans')
                if e.get('fill') not in ['#ffffff','white']:e.set('fill',C['ink'])
            front.append(''.join(etree.tostring(e,encoding='unicode') for e in wrapper))
        a.front=front
        # Remove the standard footer rule and its duplicate summary sentence.
        a.routes=[r for r in a.routes if not (r['points'][0][0]==0 and r['points'][-1][0]==1480 and r['points'][0][1]>=510)]
        a.edges=[s for s in a.edges if not any(f'M0,{y} L1480,{y}' in s for y in [511,513])]
    # The saved China architecture carries the detail. Three labels are enough.
    for y,t in [(100,'Batch and fast paths'),(280,'Binder conflict checks'),(460,'NodeShard coordination')]:
        arts[5].text(1020,y,t,30,'ink',True,width=450)
    # Keep status qualifications close to the feature, without a paragraph.
    arts[11].text(954,545,'Kthena integration proposed',24,'muted',width=520)
    arts[15].text(770,458,'Topology support in progress',25,'muted',width=690)
    arts[23].text(0,537,'Topology constraints not supported yet',25,'muted',width=1400)

    # A short closing list replaces the three-column workstream table.
    a=type(arts[21])(arts[21].name);arts[21]=a
    for y,t in [(110,'SubGroup affinity and anti-affinity'),(270,'RBG, Kubeflow and LWS integration'),(430,'Cross-scheduler and topology benchmarks')]:
        a.text(45,y,'•',38,'ink',width=70)
        a.text(105,y,t,37,'ink',width=1350)

    # Reuse the 32 original community logos. Preserve image bytes and order.
    a=art(24,'community-users','Volcano community',chapter=0,
          source='China 2026 slide 25. Original user logos, rearranged into eight columns; no new adopter count or partnership claims.')
    folder=assets/'community';items=json.loads((folder/'partners.json').read_text())
    for i,item in enumerate(items):
        x=10+(i%8)*185;y=15+(i//8)*130
        path=folder/item['file']
        if any(item['crop']):
            from PIL import Image
            iw,ih=Image.open(path).size;l,t,r,b=item['crop']
            uri='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
            a.front.append(f'<svg x="{x}" y="{y}" width="165" height="95" viewBox="{iw*l} {ih*t} {iw*(1-l-r)} {ih*(1-t-b)}" preserveAspectRatio="xMidYMid meet"><image width="{iw}" height="{ih}" href="{uri}"/></svg>')
        else:a.image(x,y,165,95,path)

    # Crop the three existing QR codes through SVG viewports. No new QR artwork.
    a=type(arts[22])(arts[22].name);arts[22]=a
    source=folder/'china-25-community-qr.png';uri='data:image/png;base64,'+base64.b64encode(source.read_bytes()).decode()
    crops=[(24,66,182,188),(280,62,184,192),(548,58,192,196)]
    labels=['volcano.sh','GitHub','Slack']
    for i,((cx,cy,cw,ch),label) in enumerate(zip(crops,labels)):
        x=80+i*495
        a.rect(x,40,300,300,'white',None,0)
        a.front.append(f'<svg x="{x+25}" y="65" width="250" height="250" viewBox="{cx} {cy} {cw} {ch}" preserveAspectRatio="xMidYMid meet"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="white"/><image width="818" height="256" href="{uri}"/></svg>')
        a.text(x+150,395,label,32,'ink',True,width=360,anchor='middle')
    a.text(740,505,'Questions?',35,'ink',width=800,anchor='middle')
    titles.update({
      4:'Different workloads, shared infrastructure',5:'Unified scheduling',6:'NodeShard coordination',
      8:'PodGroup and SubGroup',9:'HyperNode',10:'Place groups at different topology levels',
      11:'PodGroup anti-affinity',16:'SubGroup affinity and anti-affinity',
      14:'Kthena',15:'KubeRay',23:'Grove',13:'Next integrations',
      18:'Benchmark framework',19:'Comparing schedulers',20:'Benchmark scenarios',21:'What’s next',22:'Thank you',
    })
    from diagram_context import add_context
    add_context(arts)
    return removed
