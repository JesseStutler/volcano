# Volcano NA 2026 · 图与制作源文件

正式视觉版采用 Volcano 水印，未套用会议模板。正文 17 页；标题、说明和讲者信息保留为 PowerPoint 文本，图表由 SVG 导出为 2 倍分辨率 PNG 后嵌入。

- `svg/`：16 张正文图，以及封面与正文背景。
- `png/`：PPT 使用的固定图片；箭头、文字和边框在同一张图内。
- `assets/`：Volcano 原始标志及从 `volcano-new-architecture.svg` 复用的生态 logo。
- `src/build_deck.py`：生成 SVG、PNG 和 PPT。
- `manifest.json`：页码与素材对应关系。

## 细调方式

直接编辑对应 SVG，然后运行：

```bash
python3 docs/ppt/na2026/src/build_deck.py --reuse-svg
```

`--reuse-svg` 保留已有 SVG，只重新导出图片与 PPT。若修改的是生成脚本中的布局，去掉该参数会重新生成所有 SVG。不要在 PowerPoint 里把 PNG 拆成独立连接线。

依赖为 `python-pptx`、`cairosvg`、`Pillow`、`lxml`，字体使用 Liberation Sans / Mono。脚本从前一版 draft PPT 继承讲者备注，因此请保留同目录的 `Volcano_KubeCon_NA_2026_draft.pptx`。

套用官方模板时，可直接复用这些 PNG；复杂图的比例保持不变，标题与页脚单独调整。

## 内容与来源

双路径、NodeShard、Gang、HyperNode 和 Kthena 的讲解逻辑沿用 EU / China 材料，图形按 `docs/images/volcano-new-architecture.svg` 重画。生态 logo 复用该文件中的原始素材，不重新生成标志。各页技术来源放在 PPT 讲者备注中。

讲者姓名采用官方议程顺序：Kevin Wang、Ricardo Aravena、Chen Zicong。生态状态见各页备注；KubeRay topology PR #5369 于 2026-10-29 再次核对为 open。

Benchmark 结果尚未选定。正式版第 15 页以测量口径和比较方法替代草稿的结果占位，不包含模拟的曲线或未经验证的提升数字；后续可以原位换成一项经过核查的结果。
