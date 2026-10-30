"""r11: short captions that connect a workload object to a scheduling effect.

Retain useful explanations instead of selecting solely for fewest words.
Object names stay in the diagram. Captions add a constraint or mechanism.
"""
from lxml import etree


def balance_captions(arts, subtitles, removed, titles):
    drop={
        4:{'Gang + locality'},
        5:{'Batch / fast path','Binder checks','Shared node pools'},
        9:{'Standalone HyperNode'},
        15:{'Gang: merged · Topology: in progress'},
        23:{'minMember: 6'},
        16:{'Affinity','Supernode · KV locality','Anti-affinity','Leaf · replica isolation'},
    }
    for n,targets in drop.items():
        a=arts[n];seen=set();out=[]
        for fragment in a.front:
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                if label in targets:
                    seen.add(label);removed.setdefault(n,[]).append(label);wrapper.remove(e)
            out.append(''.join(etree.tostring(e,encoding='unicode') for e in wrapper))
        a.front=out
        assert seen==targets,(n,targets-seen)

    a=arts[4]
    a.text(0,280,'TP / PP gangs + network locality',32,'blue',True,width=720)
    a.text(770,280,'Role gangs + P/D locality',32,'green',True,width=710)

    a=arts[5]
    for y,heading,caption in [
        (75,'Scheduling paths','Batch throughput / Pod latency'),
        (250,'Worker coordination','Parallel workers + Binder checks'),
        (425,'NodeShard','Coordinated node access'),
    ]:
        a.text(1020,y,heading,35,'blue',True,width=445)
        a.text(1020,y+48,caption,30,'ink',width=445)

    a=arts[6]
    a.text(710,550,'Coordinated handoff · no Pod migration',30,'blue',True,width=760)

    a=arts[8]
    a.text(0,552,'Replica identity → complete SubGroups',32,'blue',True,width=1480)

    a=arts[9]
    a.text(0,552,'Parent: child HyperNodes · leaf: Kubernetes nodes',30,'blue',True,width=1480)

    a=arts[10]
    a.text(0,550,'Whole-instance placement + role-specific locality',32,'blue',True,width=1480)

    a=arts[11]
    a.text(0,550,'Instance-level HA across supernodes',32,'blue',True,width=1480)

    a=arts[16]
    for y,heading,caption,c in [
        (110,'Affinity','Prefill + Decode: same supernode','blue'),
        (335,'Anti-affinity','Decode replicas: separate leaves','green'),
    ]:
        a.text(958,y,heading,38,c,True,width=515)
        a.text(958,y+55,caption,32,'ink',width=515)

    subtitles[14]='ServingGroup → PodGroup · role replica → SubGroup'

    a=arts[15]
    a.text(770,433,'Replica label → one complete SubGroup',32,'blue',True,width=690)
    a.text(0,550,'Minimum workers = 2 replicas × 2 hosts',30,'blue',True,width=1480)

    a=arts[23]
    # Explain each arrow where the two APIs meet.
    a.path([(610,43),(870,43)],True,'blue')
    for y in [167,297]:
        a.text(740,y,'SubGroup policy',25,'blue',True,width=250,anchor='middle')
    a.text(0,438,'Minimum Pods per role',27,'ink',True,width=610)
    a.text(0,487,'2 Prefill + 4 Decode Pods',32,'blue',True,width=610)
    a.path([(610,479),(870,479)],True,'blue')
    a.text(894,487,'minMember: 6',32,'green',True,width=570,mono=True)


    a=arts[13]
    for y,caption in [
        (119,'Replica identity + gang constraints'),
        (288,'Trainer jobs → scheduling groups'),
        (457,'Leader / worker roles + group relations'),
    ]:
        a.text(585,y,caption,30,'ink',width=880)

    a=arts[18]
    a.text(0,252,'Workload parameters',28,'ink',True,width=330)
    a.text(0,550,'Scheduling latency · binding throughput',32,'blue',True,width=1480)

    a=arts[19]
    a.text(0,490,'Latency · throughput · complete gangs · placement',32,'blue',True,width=1480)

    # Implementation status belongs in notes, not in the figure explanation.
    for n in [11,16,19,20,23]:
        if subtitles[n]:removed.setdefault(n,[]).append(subtitles[n])
        subtitles[n]=''
    subtitles[11]='Same-label PodGroups → separate supernodes'
    titles[19]='Next: Cross-Scheduler Comparisons'
    titles[20]='Next: Workload and Topology Test Matrix'
