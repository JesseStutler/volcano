#!/usr/bin/env python3
# Copyright 2026 The Volcano Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Rebuild the offline HTML guide and standalone SVG illustrations (stdlib only)."""
from html import escape
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
C = dict(ink="#183341", muted="#64757d", line="#d9e1df", paper="#fafbf8",
         node="#3568a5", slice="#0c7b70", claim="#b66b28", cls="#8054a6", pod="#536574")


class Drawing:
    def __init__(self, title, desc, height=580):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
                      '<defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#d8e2dc"/></pattern></defs>',
                      '<style>text{font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif} .mono{font-family:"DejaVu Sans Mono",monospace}</style>',
                      f'<rect width="1160" height="{height}" rx="20" fill="{C["paper"]}"/>',
                      f'<rect width="1160" height="{height}" rx="20" fill="url(#grid)"/>']

    def rect(self, x, y, w, h, fill="white", stroke=None, radius=14):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or C["line"]}"/>')

    def text(self, x, y, content, size=16, color=None, weight=400, mono=False):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or C["ink"]}"'+(' class="mono"' if mono else '')+f'>{escape(content)}</text>')

    def line(self, points, color=None, dash=False):
        self.parts.append(f'<polyline points="{points}" fill="none" stroke="{color or C["muted"]}" stroke-width="2" stroke-linejoin="round"'+(' stroke-dasharray="6 6"' if dash else '')+'/>')
        x, y = points.split()[-1].split(',')
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color or C["muted"]}"/>')

    def card(self, x, y, w, h, kind, name, role, lines=()):
        self.parts.append(f'<g data-kind="{role}" data-name="{escape(name)}">')
        self.rect(x, y, w, h)
        self.rect(x+16, y+18, 4, 17, C[role], C[role], 2)
        self.text(x+30, y+32, kind, 13, C[role], 700)
        self.text(x+22, y+66, name, 23, weight=650)
        for i, text in enumerate(lines):
            self.text(x+22, y+94+i*24, text, 14, C["muted"])
        self.parts.append('</g>')

    def gpu(self, x, y, name, model, allocated=False, w=260):
        self.rect(x, y, w, 104, "#e7f3ec" if allocated else "#ffffff", "#64a990" if allocated else "#cbd9d4", 12)
        self.rect(x+18, y+24, 36, 38, "#d4e9e0", "#7dbaa3", 5)
        for dy in [29, 40, 51]:
            self.line(f'{x+12},{y+dy} {x+18},{y+dy}', '#7dbaa3')
        self.text(x+70, y+37, name, 21, weight=650)
        self.text(x+70, y+63, model, 14, C['muted'])
        self.text(x+18, y+88, "已分配 · 仍在库存中" if allocated else "可用设备", 13, C['slice'])

    def finish(self, name):
        svg = '\n'.join(self.parts+['</svg>'])
        (ROOT/'assets'/f'{name}.svg').write_text(svg)
        return svg


def scene_one():
    d = Drawing('本地设备：从需求找到一张 GPU', 'Pod trainer 引用 train-gpu Claim，Claim 引用 gpu-any Class；Class 匹配 ResourceSlice 中的设备。node-a-gpus 的 nodeName 为 node-a。假设分配 gpu-0，Claim status 记录 driver、pool、device。')
    d.card(32, 36, 282, 112, 'POD · default', 'trainer', 'pod', ['resourceClaimName: train-gpu'])
    d.card(32, 218, 282, 190, 'RESOURCE CLAIM · default', 'train-gpu', 'claim', ['request: accelerator', 'deviceClassName: gpu-any', 'count: 1'])
    d.card(390, 36, 378, 112, 'DEVICE CLASS · cluster', 'gpu-any', 'cls', ['CEL: driver == gpu.example.com'])
    d.line('172,148 172,218', C['claim']); d.text(186,189,'按名字引用',13,C['claim'])
    d.line('314,270 350,270 350,94 390,94',C['cls']); d.text(330,192,'引用',12,C['cls'])
    d.parts.append('<g data-kind="node">')
    d.rect(390,218,738,270,'#eff4fa','#b6c9de')
    d.text(414,252,'NODE',13,C['node'],700); d.text(483,254,'node-a',23,weight=650)
    d.text(861,251,'spec.nodeName: node-a',14,C['node'])
    d.parts.append('</g><g data-kind="slice">')
    d.rect(412,274,694,192,'#f0f7f3','#b5d6c5')
    d.text(434,301,'ResourceSlice · node-a-gpus',16,C['slice'],650)
    d.text(812,301,'pool: node-a / 1 slice',13,C['muted'])
    d.gpu(434,326,'gpu-0','A100',True,312); d.gpu(770,326,'gpu-1','A100',False,312)
    d.parts.append('</g>')
    d.line('579,148 579,180 1120,180 1120,312 590,312 590,326',C['cls'],True)
    d.line('926,312 926,326',C['cls'],True)
    d.text(664,171,'CEL 匹配设备，不是绑定节点',14,C['cls'])
    d.text(34,443,'实线：字段引用',13,C['muted']); d.text(34,470,'虚线：选择条件匹配',13,C['cls'])
    d.rect(32,512,1096,46,'#183341','#183341',10)
    d.text(52,541,'分配结果',14,'#a8c5ba',600)
    d.text(152,541,'status.allocation → (gpu.example.com, node-a, gpu-0)',16,'#ffffff',mono=True)
    return d.finish('01-node-local')


def scene_two():
    d = Drawing('DeviceClass 是可重叠的选择条件', 'gpu-any 匹配 node-a 和 node-b 的四张 GPU；gpu-a100 只匹配 node-a 的两张 A100。同一张 A100 同时属于两个匹配集合，但仍是一张物理设备。')
    d.card(32,30,526,120,'DEVICE CLASS · cluster','gpu-any','cls',['driver == gpu.example.com → 匹配 4 张卡'])
    d.card(602,30,526,120,'DEVICE CLASS · cluster','gpu-a100','cls',['相同 driver，且 model == A100 → 匹配 2 张卡'])
    d.line('180,150 180,230',C['cls'],True)
    d.line('410,150 410,184 850,184 850,230',C['cls'],True)
    d.line('760,150 760,204 300,204 300,230','#b16b9b',True)
    for x,name,model in [(32,'node-a','A100'),(602,'node-b','H100')]:
        d.parts.append(f'<g data-kind="node" data-name="{name}">');d.rect(x,230,526,262,'#eff4fa','#b6c9de')
        d.text(x+24,266,'NODE',13,C['node'],700);d.text(x+91,268,name,23,weight=650);d.parts.append(f'</g><g data-kind="slice" data-name="{name}-gpus">')
        d.rect(x+18,286,490,188,'#f0f7f3','#b5d6c5');d.text(x+36,315,f'ResourceSlice · {name}-gpus',16,C['slice'],650)
        d.text(x+36,339,f'pool: {name}',13,C['muted'])
        d.gpu(x+36,354,'gpu-0',model,False,216);d.gpu(x+274,354,'gpu-1',model,False,216);d.parts.append('</g>')
    d.rect(32,512,1096,46,'#f1ebf6','#d5c4e2',10)
    d.text(52,541,'4 张 + 2 张 ≠ 6 张物理 GPU。Class 是重叠视图，不能直接相加。',18,C['cls'],600)
    return d.finish('02-overlapping-classes')


def scene_three():
    d = Drawing('共享 Claim：两个 Pod，一份分配', 'trainer-a 与 trainer-b 都引用 shared-gpu。shared-gpu 只分配 node-a 的 gpu-0。两个 Pod 复用同一分配，used 为 1 而不是 2；两个 Pod 都必须能访问该设备。')
    d.card(32,58,260,120,'POD · default','trainer-a','pod',['第一个使用者'])
    d.card(32,270,260,120,'POD · default','trainer-b','pod',['复用已分配的 Claim'])
    d.card(384,164,330,210,'RESOURCE CLAIM · default','shared-gpu','claim',['deviceClassName: gpu-any','count: 1','status: node-a / gpu-0','reservedFor: trainer-a, trainer-b'])
    d.line('292,118 338,118 338,224 384,224',C['claim']);d.line('292,330 338,330 338,296 384,296',C['claim'])
    d.text(306,446,'两次引用',15,C['claim'],650)
    d.parts.append('<g data-kind="node">');d.rect(806,58,322,388,'#eff4fa','#b6c9de')
    d.text(830,91,'NODE',13,C['node'],700);d.text(830,124,'node-a',24,weight=650);d.parts.append('</g><g data-kind="slice">')
    d.text(830,155,'ResourceSlice: node-a-gpus',13,C['slice'])
    d.gpu(830,178,'gpu-0','A100',True,274);d.gpu(830,304,'gpu-1','A100',False,274);d.parts.append('</g>')
    d.line('714,230 830,230',C['slice']);d.text(728,215,'同一设备',13,C['slice'])
    d.text(434,414,'一份 allocation',15,C['claim'],650)
    d.rect(32,490,1096,68,'#183341','#183341',12)
    d.text(56,518,'Node / gpu-any',15,'#b0ccc2')
    d.text(56,543,'Allocatable = 2    Used = 1    第二个 Pod 的新增设备需求 = 0',19,'#ffffff',600)
    return d.finish('03-shared-claim')


def remote_inset():
    d = Drawing('跨节点可见不等于多份设备', '一个 allNodes ResourceSlice 发布一张设备。node-a 和 node-b 都可访问，但全局只有一张设备。',250)
    d.card(28,54,248,126,'NODE','node-a','node',['可以访问'])
    d.card(884,54,248,126,'NODE','node-b','node',['可以访问'])
    d.card(380,32,400,164,'RESOURCE SLICE','remote-gpus','slice',['allNodes: true','devices: [{name: gpu-0}]','全局仍然只有 1 张卡'])
    d.line('276,119 380,119',C['slice'],True);d.line('884,119 780,119',C['slice'],True)
    d.text(363,231,'可访问性是多对多关系，库存不能按节点简单求和。',16,C['muted'])
    return d.finish('04-cross-node-note')

def scene_pool():
    d=Drawing('一个 Pool，两个 ResourceSlice','同一 driver 和 pool，两个 Slice 都是第1代；各含一个唯一设备。',500)
    d.rect(28,28,1104,366,'#edf3f9','#b6c9de')
    d.text(52,66,'NODE  node-a',24,C['node'],650)
    d.rect(52,92,1056,276,'#eaf3ed','#a7cdb8')
    d.text(76,128,'POOL  (gpu.example.com, node-a)',23,C['slice'],650)
    d.text(76,155,'generation: 1   ·   resourceSliceCount: 2',16,C['muted'])
    for i,x in enumerate([76,602]):
        d.card(x,180,502,158,'RESOURCE SLICE',f'node-a-gpus-{i+1}','slice',[f'devices: [gpu-{i}]','同一代库存的一部分'])
    d.text(52,444,'两张卡，两个 Slice，一个 Pool，一个 Node。',24,weight=650)
    return d.finish('04-pool-slices')


def scene_capacity(hami=False):
    name='06-hami-native' if hami else '05-consumable-capacity'
    d=Drawing('两个 Claim 分配同一设备的容量','独立 Claim 各自消耗算力和显存，总量仍由 ResourceSlice 发布。',540)
    core,mem,total=(50,10,24) if hami else (30,12,40)
    for i,x in enumerate([28,602]):
        d.card(x,30,530,152,'RESOURCE CLAIM',('hami-' if hami else '')+f'inference-{chr(97+i)}','claim',[f'count: 1    cores: {core}    memory: {mem}Gi','每个 Pod 使用自己的 Claim'])
        d.line(f'{x+265},182 {x+265},228',C['claim'])
    d.parts.append('<g data-kind="slice">')
    d.rect(28,228,1104,278,'#eff7f1','#b5d6c5')
    d.text(52,267,('hami-gpu-0' if hami else 'gpu-0')+'  /  node-a',24,C['slice'],650)
    d.text(624,265,'allowMultipleAllocations: true',20,C['slice'],mono=True)
    for y,label,unit,used,full in [(330,'算力','',core,100),(422,'显存','Gi',mem,total)]:
        d.text(52,y-20,f'{label}：{used*2}{unit} 已分配 / {full}{unit} 总量',17,weight=600)
        d.rect(52,y,1056,38,'#dce9df','#dce9df',5)
        width=1056*used/full
        d.rect(52,y,width,38,'#157f73','#157f73',4)
        d.rect(52+width,y,width,38,'#bc702e','#bc702e',4)
        d.text(66,y+26,f'A · {used}{unit}',16,'white',600)
        d.text(66+width,y+26,f'B · {used}{unit}',16,'white',600)
        if used*2<full:d.text(66+width*2,y+26,f'剩余 {full-used*2}{unit}',16,C['ink'],600)
    d.parts.append('</g>')
    return d.finish(name)


def scene_webhook():
    d=Drawing('HAMi webhook 字段对应','Pod limits 转为 ResourceClaim capacity 并补充 Pod claim 引用。',450)
    d.card(28,32,500,268,'POD · 用户提交','inference-compatible','pod',['resources.limits:','nvidia.com/gpu: 1','nvidia.com/gpucores: 50','nvidia.com/gpumem: 10240'])
    d.card(632,32,500,268,'RESOURCE CLAIM · webhook 创建','生成的 Claim','claim',['exactly:','count: 1','capacity.requests.cores: 50','capacity.requests.memory: 10Gi'])
    for y in [174,198,222]:d.line(f'528,{y} 632,{y}',C['claim'])
    d.text(546,155,'转换',16,C['claim'],650)
    d.rect(28,332,1104,82,'#183341','#183341')
    d.text(52,365,'Pod 同时补上 Claim 引用，移除已转换的 GPU limits。',22,'white',600)
    d.text(52,393,'10240 MiB = 10 GiB  ·  这里的 Claim 名称只是示意，实际由 webhook 生成。',16,'#bed5ca')
    return d.finish('07-hami-webhook')


def documents(path):
    """Split the authored multi-document files without a runtime YAML dependency."""
    import re
    chunks=re.split(r'^---\s*$',(ROOT/path).read_text(),flags=re.M)
    result=[]
    for chunk in chunks:
        if not chunk.strip():continue
        kind=re.search(r'^kind:\s*(\S+)',chunk,re.M)
        name=re.search(r'^metadata:\s*\n\s+name:\s*(\S+)',chunk,re.M)
        if not kind or not name:raise ValueError(f'Missing kind/name in {path}')
        result.append(dict(kind=kind[1],name=name[1],yaml=chunk.strip()+'\n',file=path,observation=path.startswith('observations/')))
    return result


ROLE_NOTES={
 'Node':'这台机器提供本地设备。通常由 kubelet 注册；这里列出来是为了对照 Slice 的 nodeName。',
 'ResourceSlice':'driver 发布的设备库存。先看 driver、pool 和 nodeName，再看 devices。Pool 名不是一个独立对象的引用。',
 'DeviceClass':'管理员或驱动安装程序提供的选择规则。Claim 按名称引用它，CEL 再去匹配设备。',
 'ResourceClaim':'用户的设备需求。看 exactly 下的 Class、count；容量共享场景还要看 capacity.requests。',
 'Pod':'使用者。spec.resourceClaims 关联 Claim，容器的 resources.claims 通过本地别名选择它。'}
KIND_ROLE={'Node':'node','ResourceSlice':'slice','DeviceClass':'cls','ResourceClaim':'claim','Pod':'pod'}


def inspector(scene):
    docs=[]
    for path in scene['files']:docs.extend(documents(path))
    buttons=[]
    for i,doc in enumerate(docs):
        role=KIND_ROLE[doc['kind']]
        buttons.append(f'<button class="object-choice" data-index="{i}" data-kind="{role}" aria-pressed="{str(i==0).lower()}"><span>{escape(doc["kind"])}</span><strong>{escape(doc["name"])}</strong>{"<small>只读示意</small>" if doc["observation"] else ""}</button>')
        doc['note']=ROLE_NOTES[doc['kind']]
        if doc['observation']:doc['note']='只读示意，用来理解发布或分配后的字段；不要把它当作创建输入。'+doc['note']
    first=docs[0]
    return f'''<section class="inspect" id="resources" aria-labelledby="inspect-title">
      <div class="section-heading"><div><span class="eyebrow">对照 YAML</span><h2 id="inspect-title">选一个对象，看它具体怎么写</h2></div><span class="muted">图中的资源也可以点击</span></div>
      <div class="inspector"><div class="objects" aria-label="本页资源">{''.join(buttons)}</div>
      <div class="code-panel"><div class="code-title"><span id="object-title">{escape(first['kind']+' / '+first['name'])}</span><button id="copy-yaml" type="button">复制此对象</button></div>
      <p id="object-note">{escape(first['note'])}</p><pre tabindex="0"><code id="yaml-code">{escape(first['yaml'])}</code></pre>
      <div class="code-footer"><a id="source-file" href="{first['file']}" download>下载所在 YAML 文件</a><span id="copy-status" role="status" aria-live="polite"></span></div></div></div>
      <script type="application/json" id="yaml-data">{json.dumps(docs,ensure_ascii=False).replace('</','<\\/')}</script></section>'''


def calculator():
    return '''<section class="calculator" aria-labelledby="capacity-title"><div><span class="eyebrow">改两个数，试一试</span><h2 id="capacity-title">第三个 Claim 能放进这张卡吗？</h2><p>A 和 B 已分配：60 算力 + 24Gi 显存。<br>固定剩余：40 算力 + 16Gi 显存。</p></div><div class="inputs"><label>这次要多少算力 <output id="cores-value">20</output><input id="cores" type="range" min="1" max="100" value="20"></label><label>这次要多少显存 <output id="memory-value">8Gi</output><input id="memory" type="range" min="1" max="40" value="8"></label><p id="capacity-result" role="status" aria-live="polite">可以分配。分配后剩余 20 算力、8Gi 显存。</p><small>只计算这张设备的两个容量维度；不是一次真实调度。</small></div></section>'''


def main():
    (ROOT/'assets').mkdir(exist_ok=True)
    svgs=[scene_one(),scene_two(),scene_three(),scene_pool(),scene_capacity(),scene_capacity(True),scene_webhook()]
    remote_inset()
    data=json.loads((ROOT/'scenarios.json').read_text())
    scenes=data['scenes']
    template=(ROOT/'page.template.html').read_text()
    def render(slug,title,content):
        links=['<a class="nav-home'+(' current' if slug=='index' else '')+'" href="index.html"'+(' aria-current="page"' if slug=='index' else '')+'>场景目录</a>']
        for i,s in enumerate(scenes,1):
            links.append(f'<a href="{s["slug"]}.html"'+(' class="current" aria-current="page"' if slug==s['slug'] else '')+f'><span>{i:02}</span>{escape(s["nav"])}</a>')
        page=template.replace('{{TITLE}}',escape(title)).replace('{{NAV}}',''.join(links)).replace('{{CONTENT}}',content)
        (ROOT/f'{slug}.html').write_text(page)
    for i,(s,svg) in enumerate(zip(scenes,svgs)):
        downloads=''.join(f'<a href="{p}" download>{"只读示意" if p.startswith("observations") else "示例 YAML"} ↗</a>' for p in s['files'])
        content=f'<header class="page-heading"><span class="eyebrow">场景 {i+1:02} / {s["tag"]}</span><h1>{escape(s["title"])}</h1><p class="lead">{escape(s["intro"])}</p><div class="downloads">{downloads}<a href="assets/{s["slug"]}.svg" download>SVG ↗</a><a href="assets/{s["slug"]}.png" download>PNG ↗</a></div></header>'
        content+=f'<figure class="diagram"><div class="diagram-scroll">{svg}</div><figcaption>{escape(s["takeaway"])}</figcaption></figure>'
        content+=inspector(s)
        content+='<section class="reading" aria-label="场景说明">'+''.join(f'<article><h2>{escape(h)}</h2><p>{escape(p)}</p></article>' for h,p in s['notes'])+'</section>'
        if i==4:content+=calculator()
        content+='<section class="sources"><h2>继续查原文</h2>'+''.join(f'<a href="{data["sources"][key][1]}" target="_blank" rel="noopener">{escape(data["sources"][key][0])} ↗</a>' for key in s['sources'])+'</section>'
        content+='<nav class="page-turn" aria-label="相邻场景">'
        prev=scenes[i-1] if i else None
        content+=(f'<a href="{prev["slug"]}.html">← {escape(prev["nav"])}</a>' if prev else '<a href="index.html">← 场景目录</a>')
        nxt=scenes[i+1] if i+1<len(scenes) else None
        content+=(f'<a href="{nxt["slug"]}.html">{escape(nxt["nav"])} →</a>' if nxt else '<a href="index.html">返回目录 →</a>')+'</nav>'
        render(s['slug'],s['title']+' · DRA 图解',content)
    cards=''.join(f'<a class="scene-link" href="{s["slug"]}.html"><span class="scene-number">{i:02}</span><div><span class="eyebrow">{s["tag"]}</span><h2>{escape(s["title"])}</h2><p>{escape(s["takeaway"])}</p></div><span class="arrow">↗</span></a>' for i,s in enumerate(scenes,1))
    content='''<header class="page-heading home-heading"><span class="eyebrow">Kubernetes DRA · 看图，对照 YAML</span><h1>从一张 GPU 开始，<br>把这些对象认清楚。</h1><p class="lead">刚接触 DRA，可以先看第一个场景。想弄清共享，就从第 3 页看到第 6 页：共用 Claim、按容量分配、HAMi vGPU，差别都在里面。</p><a class="start-link" href="01-node-local.html">先看一张卡怎么分配 →</a></header>
    <section class="quick-map"><span class="eyebrow">先认识名字</span><div><p><b>Node</b>设备在哪里使用</p><p><b>ResourceSlice</b>驱动发布哪些设备</p><p><b>DeviceClass</b>用什么条件选设备</p><p><b>ResourceClaim</b>这次需要什么</p><p><b>Pod</b>谁来使用这份申请</p></div><p class="pool-note">Pool 是同一个 driver 的库存分组，写在 Slice 里面；它不是另一个要创建的 API 对象。</p></section>
    <section class="scene-directory" aria-label="选择场景">'''+cards+'''</section>
    <section class="reading"><article><h2>页面怎么用？</h2><p>每个场景有独立地址。先看图，再点资源卡片，对照旁边的 YAML。示例文件、SVG 和 PNG 都能下载。整个目录保存下来后，直接打开 index.html 就能离线阅读。</p></article><article><h2>这些 YAML 能直接装出一套集群吗？</h2><p>前五页使用教学驱动 gpu.example.com，用来解释 API。最后两页按 HAMi 的实际实现整理用户请求，但仍需要先安装驱动与运行时。只读示意单独放在 observations，不能拿来替代驱动发布库存。各场景独立，不要混合应用。</p></article><article><h2>版本基线</h2><p>Kubernetes 1.36；HAMi NVIDIA driver v0.1.1。对应源码链接放在每页末尾。页面和 API 示例已经校验，未在真实 GPU 集群执行。</p></article></section>
    <section class="deployment" id="deploy"><span class="eyebrow">自己部署</span><h2>一条命令，把这份图解放到服务器上</h2><p>在仓库根目录运行（需要 Docker）：</p><pre><code>./docs/user-guide/dra-visual-guide/serve.sh</code></pre><p>默认访问服务器的 8080 端口。也可以用 Python 本地预览，或者把整个目录复制到已有静态网站。</p><a href="README.md">查看部署、停止和维护说明 ↗</a></section>'''
    render('index','DRA 图解 · 从整卡到 vGPU 共享',content)
    print('Built 8 HTML pages and 8 SVG illustrations.')


if __name__=='__main__':
    main()
