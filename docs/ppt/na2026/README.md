# Volcano NA 2026 · 制作源文件

当前 26 页。[PPT](../Volcano_KubeCon_NA_2026.pptx) · [PDF](../Volcano_KubeCon_NA_2026.pdf) · [大纲](../Volcano_KubeCon_NA_2026_outline.zh-CN.md) · [逐页预览](review/latest/README.md)

## 复用素材

| NA 页 | 来源 |
|---|---|
| 5 | China 7：统一调度架构 |
| 6 | China 9：动态 Node Sharding |
| 9 | China 14：PodGroup / SubGroup |
| 10 | China 16：HyperNode 物理网络 |
| 11 | EU 16 / China 17：多级网络拓扑 |
| 16 | China 22：Kthena gang 调度 |
| 26 | China 25：社区 logo 和二维码 |

第 13、14 页沿用原拓扑的交换机符号和 fabric 布局。第 12 页参考 China 的 gang 抢占场景重新绘制。

原始图是 PNG，保存在 `assets/reused/`，来源见 `assets/provenance.json`。新增文字、YAML、分组与连线是 SVG；PNG 固定图形后嵌入 PPT，避免箭头漂移。标题、讲者和章节页使用 PowerPoint 原生文本。官方模板到手后再套版。

## 文件

- `svg/`、`png/`：当前配图的源文件和渲染结果。
- `src/build_deck.py`：生成 PPT，串联素材与版面处理。
- `src/approved_batch.py`：当前新增页、局部注释、生态映射和社区合页。
- `src/revision_notes.py`：26 页简短英文 Speaker Notes。
- `speaker-notes.md`：英文备注的阅读版。
- `slide-sources.json`：各页技术来源，与演讲提示分开保存。
- `src/mapping_examples.py`：生成配套 YAML 映射片段。
- 其他被 builder 导入的模块：存量图构建、字体、版面及社区素材加载。
- `examples/`：关键字段片段，省略了 Pod 模板等内容，不是可直接 apply 的 manifest。
- `integration-status.json`、`fact-checks.json`：2026-10-30 核查的集成状态和源码版本。
- `manifest.json`、`geometry-audit.json`：当前页码、素材来源和连线坐标。
- `review/latest/`：当前逐页预览、二维码和映射检查结果。

`*-mapping.yaml` 中的 `modelServingSpec` 等包装键用于并排阅读输入与输出，不属于 Kubernetes API。

## 重建

```bash
python3 docs/ppt/na2026/src/build_deck.py
python3 docs/ppt/na2026/src/validate_deck.py
libreoffice --headless --convert-to pdf --outdir docs/ppt docs/ppt/Volcano_KubeCon_NA_2026.pptx
python3 docs/ppt/na2026/src/render_preview.py
python3 docs/ppt/na2026/src/package_deck.py
```

手工调整 SVG 后可用 `build_deck.py --reuse-svg` 重导出 PNG/PPT。依赖 `python-pptx`、`cairosvg`、`Pillow`、`lxml`、`PyYAML`、`PyMuPDF`、`zxing-cpp`；字体为 Liberation Sans / Mono。

## 讲述口径

Ricardo：Nunchux AI 的 AI Infrastructure Lead、CNCF TOC Alternate (GB)。Rainie：Pinterest、Apache YuniKorn PMC。公开资料来源保存在 `slide-sources.json`。

Kthena anti-affinity 仍是 proposal；KubeRay worker-group topology 仍在推进；Grove 当前 backend 不支持 topologyConstraint。SubGroup 亲和/反亲和作为下一步讲。Benchmark 展示已有框架和验证计划，不填猜测结果，也不用 KWOK 推导真实 GPU 执行吞吐。

社区页保留 32 个原始 logo，统一 viewport、边框与灰条；官网、GitHub、Slack 二维码沿用原素材。未新增商业伙伴关系或生产用户数量声明。
