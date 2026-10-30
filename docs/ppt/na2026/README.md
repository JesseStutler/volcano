# Volcano NA 2026 · 素材与制作源文件

24 页，当前为 r9。配图使用短标签，完整解释保留在演讲者备注。放大副标题、图旁要点和 YAML。[与 r8 对照](review/r9/README.md)。

## 这次实际复用的图

| NA 页 | 原素材 | 处理 |
|---|---|---|
| 5 | China 7：Unified Scheduling Architecture | 保留架构主体，裁掉图片内重复标题，右侧加讲解要点 |
| 6 | China 9：Dynamic Node Sharding | 保留控制器图，右侧补 NodeShard YAML |
| 8 | China 14：PodGroup / SubGroup | 整图沿用 |
| 9 | China 16：HyperNode | 保留物理网络部分，右侧换成准确、可读的 API 片段 |
| 10 | EU 16 / China 17：Multi-Level Network Topology | 两套材料使用同一网络图；保留图，重排关键 YAML |
| 14 | China 22：Kthena Hierarchical Gang Scheduling | 整图沿用，保留角色数量与 gangPolicy 的关键字段 |

第 11、12 页沿用第 10 页的两层交换网络布局与原交换机符号，在同一 fabric 上重新标注实例及 SubGroup 放置。物理连线不加箭头；调度流程使用水平 / 垂直箭头。交换机是嵌入的旧图裁片，连线、分组和文字可在 SVG 中编辑。

原始 PPT 中这些图是 **PNG**，位于 `assets/reused/`；没有把它们重新画一遍，也不将它们称为可编辑矢量图。新增的 YAML、注释及关系图是 SVG 文本和路径。`assets/provenance.json` 记录来源和原图尺寸。

参考了 [KubeCon NA 2025 WG Serving](https://static.sched.com/hosted_files/kccncna2025/79/KubeCon%20NA%202025%20-%20WG%20Serving.pptx.pdf) 的角色、硬件层级与部署关系表达，以及 [Volcano EU 2025](https://static.sched.com/hosted_files/kccnceu2025/cc/Kubecon%20EU2025%20Volcano.pdf) 的拓扑与 API 对照。只借鉴组织方式，没有复制外部演讲图。

## 文件与细调

- `svg/`：正文组合图与背景；包含嵌入的旧 PNG、可编辑文字和路径。
- `png/`：SVG 的固定渲染结果，供 PPT 使用；连接线与图形不会因 PowerPoint 排版漂移。
- `examples/`：PPT 展示的 YAML 片段，**省略了字段，不是直接 apply 的完整 manifest**。
- `src/build_deck.py`：配色、YAML、存量图版面和 PPT 生成。
- `src/polish_figures.py`：KubeRay、benchmark 框架与收尾页。
- `src/approved_revision.py`：workload、共享拓扑、Grove、社区计划和横向测试图。
- `src/light_edit.py`：r8 的外围评论清理。
- `src/speaker_labels.py`：r9 的短标签、图旁文字层级、路线页布局；完整解释移入备注。
- `src/community_slides.py`：沿用社区用户 logo 和二维码页。
- `src/simplify_deck.py`、`src/diagram_context.py`：历史 r6/r7 处理，不参与当前生成。
- `integration-status.json`：本轮核查的生态状态及固定版本来源。
- `src/render_preview.py`：生成 PDF 缩略图。
- `src/validate_deck.py`：检查文字边界、连线避让、箭头几何、YAML 及 PPT 页数 / 备注。
- `geometry-audit.json`：各页连接线坐标；流程箭头为正交路径，物理 fabric 的直连线另作标记。
- `assets/icons/`：Kubernetes 官方资源图标，附来源与许可证。
- `manifest.json`：页码、素材和原草稿备注页的对应关系。
- `references.json`：各页技术来源。

```bash
# 修改脚本中的版面、文字后，重新生成
python3 docs/ppt/na2026/src/build_deck.py

# 手工细调 SVG 后，保留 SVG 并重新导出 PNG / PPT
python3 docs/ppt/na2026/src/build_deck.py --reuse-svg

# 导出 PDF 后生成缩略图
python3 docs/ppt/na2026/src/render_preview.py
```

依赖：`python-pptx`、`cairosvg`、`Pillow`、`lxml`；预览另需 `PyMuPDF`。字体为 Liberation Sans / Mono。可用 LibreOffice 导出 PDF。标题、讲者资料和章节引导页为 PowerPoint 原生文本；套官方模板时可直接调整。

## 社区素材

第 23 页的 32 个用户 logo、第 24 页的三个二维码均取自 China 第 25 页。原始图片位于 `assets/community/`，提取时保留字节和原裁剪信息。未沿用旧页的 60+ 数字，也未新增伙伴关系声明。二维码原图与最终 PDF 均已解码核对，结果见 `assets/community/qr-targets.json` 和 `review/r6/qr-check.json`。

## 状态与讲者资料

- Ricardo 的职务依据 [NA 2026 会议资料](https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/program/schedule/?id=1289640)：AI Infrastructure Lead, Nunchux AI；CNCF 身份是 [TOC Alternate (GB)](https://www.cncf.io/people/technical-oversight-committee/)，不写 Governing Board 成员或 Founder。Rainie 的 Pinterest / YuniKorn PMC 身份见 [YuniKorn 社区页](https://yunikorn.apache.org/community/people/)。照片来自公开会议页。
- [Kthena #1478](https://github.com/volcano-sh/kthena/pull/1478) 是开放中的 topology affinity 文档 proposal，第 11 页只借 ServingGroup → PodGroup 关系讲场景，不声称 Kthena 已实现 anti-affinity。
- [KubeRay #5369](https://github.com/ray-project/kuberay/pull/5369) 仍为 open；Grove 当前 main 已实现 SubGroup 映射，仍拒绝 topologyConstraint。来源见 `integration-status.json`。
- 第 20、21 页讲横向测试与场景计划。对照集合和结果尚未定稿；不填模拟性能结果，不用 KWOK 推导实际 GPU / 模型吞吐。

上述状态于 2026-10-29 核查，演讲前再复核。按当前备注计时约 25 分钟，另留 5 分钟问答。
