# Volcano NA 2026 · 素材与制作源文件

22 页修订版。背景保留；讲者改为 Ricardo Aravena 和 Rainie Li，新增介绍页与四张章节引导页。技术页采用原图加 API 对照，ecosystem 改为控制器输入与分组模型对照。自画图使用更深的文字、边框与连线；分组用包含关系，测量用事件时间轴。参见[重点页前后对照](visual-review.md)。

## 这次实际复用的图

| NA 页 | 原素材 | 处理 |
|---|---|---|
| 5 | China 7：Unified Scheduling Architecture | 保留架构主体，裁掉图片内重复标题，右侧加讲解要点 |
| 6 | China 9：Dynamic Node Sharding | 保留控制器图，右侧补 NodeShard YAML |
| 8 | China 14：PodGroup / SubGroup | 整图沿用 |
| 9 | China 16：HyperNode | 保留物理网络部分，右侧换成准确、可读的 API 片段 |
| 10 | EU 16 / China 17：Multi-Level Network Topology | 两套材料使用同一网络图；保留图，重排关键 YAML |
| 14 | China 22：Kthena Hierarchical Gang Scheduling | 整图沿用，保留角色数量与 gangPolicy 的关键字段 |

原始 PPT 中这些图是 **PNG**，位于 `assets/reused/`；没有把它们重新画一遍，也不将它们称为可编辑矢量图。新增的 YAML、注释及关系图是 SVG 文本和路径。`assets/provenance.json` 记录来源和原图尺寸。

参考了 [KubeCon NA 2025 WG Serving](https://static.sched.com/hosted_files/kccncna2025/79/KubeCon%20NA%202025%20-%20WG%20Serving.pptx.pdf) 的角色、硬件层级与部署关系表达，以及 [Volcano EU 2025](https://static.sched.com/hosted_files/kccnceu2025/cc/Kubecon%20EU2025%20Volcano.pdf) 的拓扑与 API 对照。只借鉴组织方式，没有复制外部演讲图。

## 文件与细调

- `svg/`：正文组合图与背景；包含嵌入的旧 PNG、可编辑文字和路径。
- `png/`：SVG 的固定渲染结果，供 PPT 使用；连接线与图形不会因 PowerPoint 排版漂移。
- `examples/`：PPT 展示的 YAML 片段，**省略了字段，不是直接 apply 的完整 manifest**。
- `src/build_deck.py`：配色、YAML、存量图版面和 PPT 生成。
- `src/polish_figures.py`：第 4、11、13、15、16、18–22 页的自画图与排版。
- `src/render_preview.py`：生成 PDF 缩略图。
- `geometry-audit.json`：各页连接线坐标，便于检查水平 / 垂直路径。
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

## 仍需讲者补充

- Profile 页暂用公开会议头像和简介。Rainie 的 Pinterest / YuniKorn PMC 身份见 [YuniKorn 社区页](https://yunikorn.apache.org/community/people/)；Ricardo 的公开简介见 [Linux Foundation](https://events.linuxfoundation.org/archive/2026/open-source-summit-north-america/program/program-committee/)，未填写尚不确定的现任公司与正式职务。头像取自公开会议页，可替换为讲者偏好的版本。
- 第 20 页当前是测量口径，待选定一项实际 benchmark 结果后替换。不包含猜测曲线或未经核查的性能提升数字。
- KubeRay topology PR #5369 在 2026-10-29 核查时为 open，演讲前再确认。
