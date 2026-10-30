"""Emphasize the explanatory captions, rather than decorating headings."""
from lxml import etree
from PIL import ImageFont


def finish(arts, C):
    def texts(a):
        result=[]
        for part in a.front:
            root=etree.fromstring(('<g>'+part+'</g>').encode())
            result.extend(' '.join(' '.join(e.itertext()).split()) for e in root if e.tag=='text')
        return result

    captions={
        4:{'TP / PP gangs + network locality':(0,254,690,46,32,'blue'),
           'Role gangs + P/D locality':(770,254,710,46,32,'green')},
        6:{'Coordinated handoff · no Pod migration':(690,520,790,40,32,'blue')},
        8:{'Replica identity → complete SubGroups':(0,520,1480,40,32,'blue')},
        9:{'Parent: child HyperNodes · leaf: Kubernetes nodes':(0,520,1480,40,32,'blue')},
        10:{'Whole-instance placement + role-specific locality':(0,520,1480,40,32,'blue')},
        11:{'Instance-level HA across supernodes':(0,520,1480,40,32,'blue')},
        15:{'Replica label → one complete SubGroup':(750,393,730,62,32,'blue'),
            'Minimum workers = 2 replicas × 2 hosts':(0,520,1480,40,32,'blue')},
        18:{'Scheduling latency · binding throughput':(0,520,1480,40,32,'blue')},
        19:{'Latency · throughput · complete gangs · placement':(0,456,1480,58,32,'blue')},
    }
    side={
        5:{'Batch throughput / Pod latency':(1004,97,476,94,'Batch throughput /\nPod latency','blue'),
           'Parallel workers + Binder checks':(1004,272,476,94,'Parallel workers +\nBinder checks','blue'),
           'Coordinated node access':(1004,447,476,58,'Coordinated node access','blue')},
        16:{'Prefill + Decode: same supernode':(948,132,532,105,'Prefill + Decode:\nsame supernode','blue'),
            'Decode replicas: separate leaves':(948,357,532,105,'Decode replicas:\nseparate leaves','green')},
        13:{'Replica identity + gang constraints':(570,87,910,58,'Replica identity + gang constraints','blue'),
            'Trainer jobs → scheduling groups':(570,256,910,58,'Trainer jobs → scheduling groups','blue'),
            'Leader / worker roles + group relations':(570,425,910,58,'Leader / worker roles + group relations','blue')},
    }
    fontfile='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
    for n,a in arts.items():
        before=texts(a);out=[]
        for fragment in a.front:
            root=etree.fromstring(('<g>'+fragment+'</g>').encode())
            prefix=[]
            for e in root:
                if n==9 and e.tag=='svg' and e.get('y')=='55':e.set('y','30')
                if e.tag=='rect':
                    if e.get('fill')=='#f5f7fa' and float(e.get('height','0'))>350:
                        e.set('fill','#f8fafc');e.set('stroke','#91a4b8');e.set('stroke-width','1.4')
                    if e.get('height')=='47' and e.get('fill')==C['white']:e.set('fill','#e9eff6')
                    if e.get('fill')=='#dce9f8' and e.get('stroke')=='none':e.set('fill','#dce8f5')
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                if n in (5,16) and label in {'Scheduling paths','Worker coordination','NodeShard','Affinity','Anti-affinity'}:
                    e.set('font-size','30');e.set('font-weight','400')
                spec=captions.get(n,{}).get(label)
                if spec:
                    x,y,maxw,h,size,color=spec
                    font=ImageFont.truetype(fontfile,size*2)
                    w=min(maxw,font.getlength(label)/2+36)
                    assert font.getlength(label)/2 <= w-28,(n,label)
                    lines=[label];baseline=y+(h-size)/2+size*.80
                elif label in side.get(n,{}):
                    x,y,w,h,t,color=side[n][label];size=32 if n!=16 else 34
                    lines=t.split('\n');baseline=y+36
                    font=ImageFont.truetype(fontfile,size*2)
                    assert max(font.getlength(t)/2 for t in lines)<=w-28,(n,label)
                else:continue
                fill='#e3edf8' if color=='blue' else '#deeee7'
                prefix.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}"/>')
                prefix.append(f'<rect x="{x}" y="{y}" width="4" height="{h}" fill="{C[color]}"/>')
                for child in list(e):e.remove(child)
                e.text=None;e.set('x',str(x+16));e.set('y',str(baseline));e.set('font-size',str(size));e.set('font-weight','700');e.set('fill',C['ink'])
                for i,t in enumerate(lines):
                    child=etree.SubElement(e,'tspan',x=str(x+16),dy='0' if i==0 else str(size*1.27));child.text=t
            out.append(''.join(prefix)+''.join(etree.tostring(e,encoding='unicode') for e in root))
        a.front=out
        assert texts(a)==before,(n,'caption emphasis changed wording')
