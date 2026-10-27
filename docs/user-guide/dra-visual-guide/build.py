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
        self.parts.append(f'<g data-kind="{role}">')
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
        d.parts.append('<g data-kind="node">');d.rect(x,230,526,262,'#eff4fa','#b6c9de')
        d.text(x+24,266,'NODE',13,C['node'],700);d.text(x+91,268,name,23,weight=650);d.parts.append('</g><g data-kind="slice">')
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


def main():
    (ROOT/'assets').mkdir(exist_ok=True)
    scenes=[scene_one(),scene_two(),scene_three()]
    inset=remote_inset()
    files=['examples/01-node-local.yaml','examples/02-overlapping-classes.yaml','examples/03-shared-claim.yaml','observations/01-allocation.yaml']
    sources={name:(ROOT/name).read_text() for name in files}
    page=(ROOT/'page.template.html').read_text()
    for i, svg in enumerate(scenes,1):
        # Prefix IDs so multiple inline SVGs do not share title/gradient identifiers.
        for old in ['title','desc','grid']:
            svg=svg.replace(f'id="{old}"',f'id="s{i}-{old}"').replace(f'url(#{old})',f'url(#s{i}-{old})')
        svg=svg.replace('aria-labelledby="title desc"',f'aria-labelledby="s{i}-title s{i}-desc"')
        page=page.replace(f'{{{{SCENE{i}}}}}',svg)
    inset=inset.replace('id="title"','id="cross-title"').replace('id="desc"','id="cross-desc"').replace('id="grid"','id="cross-grid"').replace('url(#grid)','url(#cross-grid)').replace('aria-labelledby="title desc"','aria-labelledby="cross-title cross-desc"')
    page=page.replace('{{CROSS_NODE}}',inset)
    page=page.replace('{{YAML_DATA}}',json.dumps(sources,ensure_ascii=False).replace('</','<\\/'))
    page=page.replace('{{INITIAL_YAML}}',escape(sources[files[0]]))
    (ROOT/'index.html').write_text(page)
    print('Built index.html and 4 standalone SVGs.')


if __name__ == '__main__':
    main()
