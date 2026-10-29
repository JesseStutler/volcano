# Volcano KubeCon NA 2026

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

Ricardo Aravena · Rainie Li。23 页，约 25 分钟正文 + 5 分钟问答。

- [r5 PDF 预览](Volcano_KubeCon_NA_2026_r5.pdf)
- [r5 PowerPoint](Volcano_KubeCon_NA_2026_r5.pptx?raw=true)
- [r5 重点页大图与修改记录](na2026/review/r5/README.md)
- [逐页大纲](Volcano_KubeCon_NA_2026_draft_outline.zh-CN.md)
- [素材与制作源文件](na2026/)
- [下载 SVG / PNG / 源文件包](Volcano_KubeCon_NA_2026_sources.zip?raw=true)

这轮补全第 4 页 Training / Inference / Agents 的调度诉求，用第 10 页的网络结构串起实例 HA 与 SubGroup 关系。SubGroup 页移入第二章；生态按 Kthena、KubeRay、Grove 案例展开，再讲 RBG / Kubeflow / LWS。Benchmark 改为横向比较与代表性场景测试。Ricardo 简介已按 NA 会议与 CNCF 资料更新。

Kthena topology anti-affinity 接入目前仍是 proposal；Grove 当前 backend 已有 SubGroup 映射，但不支持 topologyConstraint。已交付能力和后续计划在页内或讲者备注中区分，不展示未经测量的 benchmark 数字。

![r5 整套预览](Volcano_KubeCon_NA_2026_preview.png)

前版留存：[r4 PDF](Volcano_KubeCon_NA_2026_r4.pdf) · [r4 修改记录](na2026/review/r4/README.md) · [早期研究](Volcano_KubeCon_NA_2026_group_topology_outline.zh-CN.md)
