"""r13 visual-only polish of the approved r12 content.

Keep all wording and original images. Use small tinted labels for identity,
quiet code panels, and consistent type hierarchy; avoid decorative cards.
"""
from lxml import etree


def finish(arts, C):
    def texts(a):
        result=[]
        for part in a.front:
            root=etree.fromstring(('<g>'+part+'</g>').encode())
            result.extend(' '.join(' '.join(e.itertext()).split()) for e in root if e.tag=='text')
        return result

    def tint(x,y,w,h,fill):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}"/>'

    captions={
        6:{'Coordinated handoff · no Pod migration'},
        8:{'Replica identity → complete SubGroups'},
        9:{'Parent: child HyperNodes · leaf: Kubernetes nodes'},
        10:{'Whole-instance placement + role-specific locality'},
        11:{'Instance-level HA across supernodes'},
        18:{'Scheduling latency · binding throughput'},
        19:{'Latency · throughput · complete gangs · placement'},
    }
    for n,a in arts.items():
        before=texts(a);out=[]
        for fragment in a.front:
            root=etree.fromstring(('<g>'+fragment+'</g>').encode())
            prefix=[]
            for e in root:
                if e.tag=='rect':
                    # API panels only; source figures stay byte-for-byte intact.
                    if e.get('fill')=='#f5f7fa' and float(e.get('height','0'))>350:
                        e.set('fill','#f8fafc');e.set('stroke','#91a4b8');e.set('stroke-width','1.4')
                    if e.get('height')=='47' and e.get('fill')==C['white']:
                        e.set('fill','#e9eff6')
                    if e.get('fill')=='#dce9f8' and e.get('stroke')=='none':
                        e.set('fill','#dce8f5')
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                if label in captions.get(n,set()):
                    e.set('font-size','30');e.set('font-weight','400');e.set('fill',C['ink'])
                if n==5 and label in {'Scheduling paths','Worker coordination','NodeShard'}:
                    e.set('font-size','34');e.set('fill',C['ink'])
                if n==4 and label in {'Training','Inference','Agents'}:
                    x={'Training':0,'Inference':770,'Agents':0}[label]
                    y=0 if label!='Agents' else 316
                    fill={'Training':'#e2ecf7','Inference':'#e0eee8','Agents':'#f8e7df'}[label]
                    prefix.append(tint(x,y,185 if label!='Agents' else 150,41,fill))
                    e.set('x',str(x+14));e.set('y',str(y+29));e.set('font-size','30')
                    for child in e:child.set('x',str(x+14))
                if n==16 and label in {'Affinity','Anti-affinity'}:
                    y=76 if label=='Affinity' else 301
                    prefix.append(tint(958,y,180 if label=='Affinity' else 246,46,'#e2ecf7' if label=='Affinity' else '#e0eee8'))
                    e.set('x','972');e.set('font-size','34')
                    for child in e:child.set('x','972')
                if n==16 and label in {'Prefill + Decode: same supernode','Decode replicas: separate leaves'}:
                    e.set('font-size','30')
                if n==13 and label in {'In progress','Planned'}:
                    y=float(e.get('y'))
                    prefix.append(tint(163,y-28,166,38,'#e2ecf7' if label=='In progress' else '#edf1f5'))
                    e.set('x','176');e.set('font-size','26');e.set('fill',C['blue'] if label=='In progress' else C['muted'])
                    for child in e:child.set('x','176')
                if n==23 and label=='SubGroup policy':
                    y=float(e.get('y'))
                    prefix.append(tint(619,y-28,242,38,'#e2ecf7'))
                    e.set('font-size','25')
                if n==23 and label=='minMember: 6':
                    prefix.append(tint(880,449,285,57,'#e0eee8'))
                if n==23 and label=='Minimum Pods per role':
                    e.set('fill',C['muted']);e.set('font-weight','400')
            out.append(''.join(prefix)+''.join(etree.tostring(e,encoding='unicode') for e in root))
        a.front=out
        if n==23:
            # Header strips stay behind the scope text and above white panels.
            strips=[tint(2,96,606,35,'#e2ecf7'),tint(872,96,606,35,'#e0eee8')]
            a.front=strips+a.front
            # Align the header arrow to the optical center of the two headings.
            for route in a.routes:
                if route['points']==[(610,43),(870,43)]:
                    route['points']=[(610,32),(870,32)]
                    route['head']=[(x,y-11) for x,y in route['head']]
            a.edges=[part.replace('M610,43 L870,43','M610,32 L870,32').replace('M860.0,48.0 L870,43 L860.0,38.0','M860.0,37.0 L870,32 L860.0,27.0') for part in a.edges]
        assert texts(a)==before,(n,'visual polish changed slide wording')
