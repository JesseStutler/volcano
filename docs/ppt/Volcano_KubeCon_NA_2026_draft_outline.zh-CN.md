# Volcano KubeCon NA 2026：演讲草稿

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

标题与摘要沿用已提交版本。正文 25 分钟，问答 5 分钟；对应 [PPT 草稿](Volcano_KubeCon_NA_2026_draft.pptx)。

## 主线

先讲不同调度路径如何协调使用集群，再讲分布式工作负载如何拿到完整、位置合适的资源组合。NodeShard 保留为架构基础，多级 Gang、拓扑和生态进展是这次的重点。

转场可以这样讲：

> 前面解决了调度路径如何协调使用节点。但有了可用节点，还不等于工作负载能够运行。我们还需要完整的副本、合适的网络位置，以及组与组之间的放置关系。

Agentic AI 用来交代背景，不把每次 Agent 调用都解释成新建一个 Pod。乐观并行讲机制，不承诺未经验证的性能收益。

## 逐页安排

| 页 | 标题 / 内容 | 时间 | 素材 |
|---|---|---:|---|
| **第一章** | **调度路径如何协调** | **6 分钟** | |
| 1 | 原标题、讲者，简述今天要讲的两层协调 | 0:30 | 封面 |
| 2 | Different Workloads, Shared Infrastructure：Agent 应用、推理服务与训练共享基础设施 | 1:00 | 生命周期图精简 |
| 3 | A Coordinated Scheduling Framework：双路径架构，简述 worker / Binder 职责 | 1:30 | China 7–8 / EU 9 |
| 4 | NodeShard: Coordinating Node Access：用一次节点范围调整解释协调过程 | 2:00 | China 9 / EU 10–11 |
| 5 | Available Nodes Are Only the Beginning：资源总量够，仍可能缺完整副本或合适拓扑 | 1:00 | 新增转场 |
| **第二章** | **工作负载内部如何协调** | **10 分钟** | |
| 6 | PodGroup and SubGroup：用 Kthena P/D 场景解释完整副本与两级 Gang | 2:30 | China 14、22 |
| 7 | HyperNode：一棵拓扑树，说明域、层级和约束 | 2:00 | China 16 |
| 8 | Multi-Level Placement：实例位于较大域，副本位于较小域 | 2:00 | China 17 |
| 9 | PodGroup Anti-Affinity：实例内部聚拢，两个实例之间分离 | 2:00 | China 15，更新为已发布 |
| 10 | Placement Rules：required 无合法域时 Pending；preferred 可退化 | 1:30 | 静态案例或短录屏 |
| **第三章** | **生态如何接入** | **4 分钟** | |
| 11 | Ecosystem Progress：Kthena、KubeRay、Grove 的能力与状态，Kubeflow / LWS 的深化方向 | 2:00 | 新增能力表 |
| 12 | KubeRay：两个双 Pod 副本，不等于任意四个 Pods | 1:00 | 新增具体案例 |
| 13 | Standalone HyperNode：独立 controller 已交付，外部 adapter 分开标状态 | 1:00 | China 19 |
| **第四章** | **接下来做什么** | **5 分钟** | |
| 14 | SubGroup Relationships：同一 PodGroup 内的 affinity / anti-affinity，标为 Proposed | 2:00 | 新增关系图 |
| 15 | Roadmap：补齐组间语义，深化 controller 映射，用真实场景验证 | 1:30 | v1.17 主线摘录 |
| 16 | Takeaways & Community：回顾两层协调，邀请提供场景与参与集成 | 1:30 | 社区入口 |
| 17 | Q&A | 5:00 | |

## 这次的新内容

Kthena 的 P/D 案例贯穿第二章：先凑齐完整副本，再约束组内拓扑，最后增加第二个实例，通过 PodGroup anti-affinity 分散放置。第三章用 KubeRay 说明类似需求也来自其他生态。

NA 的增量集中在 PodGroup anti-affinity、KubeRay 的 SubGroup 接入、standalone HyperNode 已交付，以及下一步的 SubGroup 关系。Global、混部保留为已有覆盖面，不单开章节。

截至 2026-10-28：KubeRay SubGroup PR 已合并，replica topology PR 仍在推进；Grove 已合并 gang / SubGroup backend，topology 尚未接通；Kubeflow 与 LWS 已有 Volcano 集成，后续是深化。正式演讲前再核对版本与 PR 状态。

## 草稿怎么读

- **深蓝标题、白底正文**：拟上屏内容，英文。
- **浅蓝图框、等宽小字**：图示草稿或旧素材复用位置，形状可编辑。
- **浅黄备注条、中文字体**：制作提示与待确认事项，正式版移入讲者备注。
- **紫色 Proposed 标记**：未来能力，不表示已发布。

当前使用简洁的 16:9 工作版式，未套用未经确认的 NA 官方模板。来源和讲解边界放在每页的讲者备注中。

## 剩余时间怎么用

前两天定分工、串好转场，验证一个 anti-affinity 放置案例；接着三天把复用图和新增页补齐。最后留两次计时排练，核对生态状态，导出 PDF 与离线演示。没有现成环境就用准确的静态图，不让演示拖住整套材料。

讲者分工可按第 1–5、6–10、11–16 页划分。详尽核查与来源保留在[研究大纲](Volcano_KubeCon_NA_2026_group_topology_outline.zh-CN.md)，本稿只用于制作与排练。
