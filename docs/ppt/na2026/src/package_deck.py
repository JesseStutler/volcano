"""Package the current deck only; verify QR codes and integration mappings."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import fitz,shutil,json,hashlib,zipfile,zxingcpp,yaml
root=Path(__file__).resolve().parents[1];ppt=root.parent;review=root/'review/latest';review.mkdir(parents=True,exist_ok=True)
doc=fitz.open(ppt/'Volcano_KubeCon_NA_2026.pdf')
assert len(doc)==26
for n,page in enumerate(doc,1):page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(review/f'slide-{n:02d}.png')
# Current review focus: victim selection, RBG scope, comparisons and roadmap.
focus=Image.new('RGB',(2000,1155),'#e8edf2')
for i,n in enumerate([12,20,23,25]):
 page=doc[n-1];pix=page.get_pixmap(matrix=fitz.Matrix(970/page.rect.width,970/page.rect.width),alpha=False)
 focus.paste(Image.frombytes('RGB',(pix.width,pix.height),pix.samples),(20+(i%2)*990,20+(i//2)*575))
focus.save(review/'refinement.png')
qr_im=Image.open(review/'slide-26.png');urls=sorted(b.text for b in zxingcpp.read_barcodes(qr_im))
assert urls==sorted(['https://volcano.sh','https://github.com/volcano-sh/volcano','https://cloud-native.slack.com/archives/C011GJDQS0N']),urls
(review/'qr-check.json').write_text(json.dumps({'pdf_page':26,'render_width':qr_im.width,'decoded':urls},indent=2)+'\n')
def read(f):return yaml.safe_load((root/'examples'/f).read_text())
k=read('kthena-mapping.yaml');r=read('kuberay-mapping.yaml');g=read('grove-mapping.yaml')
# Verify screen excerpts agree with the full companion mapping and the source rules.
assert k['podGroupSpec']['minMember']==sum(x['subGroupSize']*x['minSubGroups'] for x in k['podGroupSpec']['subGroupPolicy'])==8
for role,sg in zip(k['modelServingSpec']['template']['roles'],k['podGroupSpec']['subGroupPolicy']):
 assert sg['name']==role['name'] and sg['subGroupSize']==role['workerReplicas']+1
 assert sg['networkTopology']==k['modelServingSpec']['template']['networkTopology']['rolePolicy']
assert k['podGroupSpec']['networkTopology']==k['modelServingSpec']['template']['networkTopology']['groupPolicy']
assert read('kthena-generated-podgroup-spec.yaml')['subGroupPolicy'][0]['subGroupSize']==2
assert r['rayClusterSpec']['enableInTreeAutoscaling'] is True
rw=r['rayClusterSpec']['workerGroupSpecs'][0];rs=r['podGroupSpec']['subGroupPolicy'][1]
assert (rw['minReplicas'],rw['numOfHosts'])==(rs['minSubGroups'],rs['subGroupSize'])==(2,2)
assert r['podGroupSpec']['minMember']==1+rs['minSubGroups']*rs['subGroupSize']==5
assert rs['matchLabelKeys']==['ray.io/worker-group-replica-name']
assert g['podGroupSpec']['minMember']==sum(x['minReplicas'] for x in g['podGangSpec']['podGroups'])==6
for gg,gs in zip(g['podGangSpec']['podGroups'],g['podGroupSpec']['subGroupPolicy']):
 assert gs['name']==gg['name'] and gs['subGroupSize']==max(gg['minReplicas'],1) and gs['minSubGroups']==1
 assert gs['labelSelector']['matchLabels']=={'grove.io/podclique':gg['name']}
assert read('grove-podgroup-spec.yaml')['subGroupPolicy'][0]==g['podGroupSpec']['subGroupPolicy'][1]
# The new on-slide summaries must agree with the full selector/topology mappings.
for filename,full in [('kthena-podgroup-overview.yaml',k['podGroupSpec']),('kuberay-podgroup-overview.yaml',r['podGroupSpec']),('grove-podgroup-overview.yaml',g['podGroupSpec'])]:
 overview=read(filename)
 assert overview['minMember']==full['minMember']
 policies={p['name']:p for p in full['subGroupPolicy']}
 for p in overview['subGroupPolicy']:
  assert all(policies[p['name']][key]==value for key,value in p.items()),(filename,p)
(report:=review/'mapping-check.json').write_text(json.dumps({'Kthena':'8 Pods = 1 prefill replica × 2 + 3 decode replicas × 2; groupPolicy/rolePolicy mapped','KubeRay':'autoscaling: 2 replicas × 2 hosts + 1 head; replica-name selector grouping','Grove':'2 + 4 minimum Pods; one SubGroup per group; grove.io/podclique selector','scope':'Excerpts and mapping arithmetic checked; not cluster integration tests.'},indent=2)+'\n')
checks={}
for ext in ['pptx','pdf']:
 path=ppt/f'Volcano_KubeCon_NA_2026.{ext}';checks[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
(review/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
with zipfile.ZipFile(ppt/'Volcano_KubeCon_NA_2026_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
  if rel.parts[0]=='review' and len(rel.parts)>1 and rel.parts[1]!='latest':continue
  z.write(p,p.relative_to(ppt))
print('Latest: 26 pages, 3 decoded QR codes, all three source-based mappings checked.')
print('Source zip MB:',round((ppt/'Volcano_KubeCon_NA_2026_sources.zip').stat().st_size/1e6,2))
