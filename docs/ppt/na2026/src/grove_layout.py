"""Grove: aligned fields and explicit SubGroup membership on the Volcano side."""

def layout_grove(arts):
    old=arts[23]
    logo=[part for part in old.front if '<image ' in part]
    assert len(logo)==1
    a=type(old)(old.name);arts[23]=a
    a.front.extend(logo)
    a.text(106,43,'Grove PodGang',31,'ink',True,width=530)
    a.text(870,43,'Volcano PodGroup',31,'blue',True,width=600)
    a.path([(610,32),(850,32)],True,'blue')
    for x,w,title,c,fill in [
        (0,610,'PodGang.spec.podGroups','blue','#e3edf8'),
        (850,630,'PodGroup.spec.subGroupPolicy','green','#deeee7'),
    ]:
        a.rect(x,90,w,335,'white',c,7,layer='bg',dash=True)
        a.rect(x+2,92,w-4,36,fill,None,2)
        a.text(x+16,117,title,23,c,True,width=w-32)

    def pods(x,y,count,color):
        for j in range(count):
            xx=x+j*138
            a.rect(xx,y,126,36,'prefill' if color=='blue' else 'mint',color,3)
            a.text(xx+63,y+25,'Pod '+str(j),22,color,True,width=118,anchor='middle')

    for y,name,count,c in [(140,'prefill',2,'blue'),(282,'decode',4,'green')]:
        a.rect(18,y,574,119,'white','light',5,layer='bg')
        a.rect(868,y,594,119,'#f7fafc' if c=='blue' else '#f6faf8',c,5,layer='bg',dash=True)
        a.text(32,y+29,name,28,c,True,width=220)
        a.text(280,y+29,'minReplicas: '+str(count),25,'ink',width=300,mono=True)
        pods(32,y+75,count,c)
        # Both fields share one x coordinate and one monospace column.
        a.text(884,y+29,name+'\nSubGroup',26,c,True,width=235)
        a.text(1126,y+29,'subGroupSize: '+str(count),25,'ink',width=330,mono=True)
        a.text(1126,y+61,'minSubGroups: 1',25,'ink',width=330,mono=True)
        pods(884,y+75,count,c)
        a.path([(592,y+59),(864,y+59)],True,c)
        a.text(728,y+40,'SubGroup policy',25,c,True,width=250,anchor='middle')

    a.text(0,453,'Minimum Pods per role',27,'muted',False,width=610)
    a.rect(0,471,590,54,'#e3edf8',None,4)
    a.text(16,507,'2 Prefill + 4 Decode Pods',32,'ink',True,width=560)
    a.path([(610,495),(1106,495)],True,'blue')
    a.rect(1110,471,354,54,'#deeee7',None,4)
    a.text(1126,507,'minMember: 6',32,'green',True,width=330,mono=True)
