"""r7: short explanations next to the diagram element they describe."""
from lxml import etree


def add_context(arts):
    def replace(n,old,new,x,y,w,size=26):
        a=arts[n]
        for i,fragment in enumerate(a.front):
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag=='text' and ' '.join(' '.join(e.itertext()).split())==old:
                    wrapper.remove(e)
            a.front[i]=''.join(etree.tostring(e,encoding='unicode') for e in wrapper)
        a.text(x,y,new,size,'ink',width=w)

    replace(4,'TP / PP gangs','Place complete TP / PP groups.',0,280,710,26)
    replace(4,'Role groups and network locality','Keep P/D communication local.',770,280,710,26)
    replace(4,'Reuse','Reuse ready capacity',772.5,392.5,260,22)
    # The warm-pool caption is centered inside the component.
    el=etree.fromstring(arts[4].front[-1]);el.set('text-anchor','middle')
    arts[4].front[-1]=etree.tostring(el,encoding='unicode')

    captions={
      5:[(1020,145,450,'Batch jobs and latency-sensitive Pods use separate paths.',26),
         (1020,325,450,'Reject conflicting placements before binding.',26),
         (1020,505,450,'Hand off nodes without migrating running Pods.',26)],
      6:[(710,510,750,'Desired nodes become usable after handoff.',27)],
      8:[(0,549,1475,'PodGroup sets the workload minimum. SubGroups keep each replica complete.',26)],
      9:[(500,549,975,'A parent groups HyperNodes. A leaf groups Nodes.',26)],
      10:[(0,550,920,'Prefill stays under one leaf. Decode can span leaves.',25)],
      11:[(0,549,910,'A supernode failure leaves the other instance available.',25)],
      16:[(958,205,510,'Keep KV transfers local.',27),
          (958,425,510,'A leaf failure affects one Decode replica.',26)],
      14:[(1010,540,470,'Each role replica is one SubGroup.',24)],
      15:[(770,421,690,'One replica label identifies one SubGroup.\nAll hosts join the gang together.',26)],
      13:[(585,119,880,'Keep each role instance runnable.',26),
          (585,288,880,'Place distributed workers as complete groups.',26),
          (585,457,880,'Express relationships across role groups.',26)],
      18:[(430,546,1040,'Use API events to measure scheduling latency and throughput.',26)],
      19:[(0,449,510,'Replay identical workload arrivals.',26),
          (1090,475,390,'Compare latency, throughput\nand placement.',26)],
      20:[(630,157,440,'Burst above the available capacity.',24),
          (630,312,440,'Try small and large SubGroups.',24),
          (630,467,440,'Vary tier limits and free domains.',24)],
    }
    for n,items in captions.items():
        for x,y,w,t,size in items:arts[n].text(x,y,t,size,'ink',width=w)
    replace(15,'Topology support in progress','Topology support in progress',770,515,690,25)
    replace(23,'6 Pods','Each group becomes a complete SubGroup.',0,463,790,27)
