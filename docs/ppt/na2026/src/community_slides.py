"""Community logos and original QR codes retained from r6."""
from pathlib import Path
import base64,json

def add_community_slides(arts,art,titles,assets):
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
    titles[22]='Thank you'
