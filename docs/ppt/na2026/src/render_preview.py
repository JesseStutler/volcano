"""Create overview PNG from the exported PDF. Requires PyMuPDF and Pillow."""
from pathlib import Path
from PIL import Image,ImageDraw
import fitz
PPT=Path(__file__).resolve().parents[2]
doc=fitz.open(PPT/'Volcano_KubeCon_NA_2026.pdf')
cols=3;w=640;h=360;stepx=660;stepy=390
out=Image.new('RGB',(cols*stepx+20,((len(doc)+cols-1)//cols)*stepy+20),'#e8edf2');draw=ImageDraw.Draw(out)
for i,page in enumerate(doc):
 pix=page.get_pixmap(matrix=fitz.Matrix(w/page.rect.width,w/page.rect.width),alpha=False)
 im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 x=20+i%cols*stepx;y=20+i//cols*stepy;out.paste(im,(x,y));draw.text((x+5,y+h+8),f'{i+1:02d}',fill='#202d3c')
out.save(PPT/'Volcano_KubeCon_NA_2026_preview.png')
print('Preview:',len(doc),'pages')
