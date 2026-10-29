# Volcano KubeCon NA 2026：演讲大纲

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

Ricardo Aravena · Rainie Li。约 24–25 分钟正文，5 分钟问答。[PPT](Volcano_KubeCon_NA_2026.pptx) · [PDF](Volcano_KubeCon_NA_2026.pdf)

主线不变：先讲不同调度路径如何协调资源，再讲完整分组与拓扑放置，接着看生态控制器如何传递这些需求，最后用 benchmark 验证调度表现。Agentic AI 是背景，不把每次 agent 调用都等同于创建 Pod，也不预设双路径一定更快。

## 逐页安排

| 页 | 内容 | 讲法 / 素材 |
|---|---|---|
| 1 | 封面 | 原标题，两位讲者 |
| 2 | Speaker profiles | 照片与简短介绍，正式职务可再调整 |
| 3 | 第一章：统一调度 | 不同路径如何共享集群 |
| 4 | Workload demands | 训练、推理、agent 应用的需求 |
| 5 | Unified architecture | 沿用 China 架构图，讲双路径与协同 |
| 6 | NodeShard | 沿用控制器图，对照 desired / in-use YAML |
| 7 | 第二章：多级 Gang 与网络拓扑 | 有节点，还要有完整副本和局部性 |
| 8 | PodGroup / SubGroup | 沿用训练与 serving 分组图 |
| 9 | HyperNode | 物理网络与父、叶节点 YAML 对照 |
| 10 | 多级拓扑放置 | 沿用 EU / China 网络图，对照不同层级约束 |
| 11 | PodGroup anti-affinity | 实例内聚拢，实例间分离；展示关键 YAML |
| 12 | 第三章：Ecosystem | 控制器怎样传递角色与副本身份 |
| 13 | 接入关系 | Kthena、KubeRay、Grove、Kubeflow、LWS；区分已有与推进中 |
| 14 | Kthena | 沿用 China 映射图与 gangPolicy / roles YAML |
| 15 | KubeRay | 两个完整的双 Pod 副本；replica label 对照 SubGroup policy |
| 16 | 后续分组关系 | 同一 PodGroup 内的 SubGroup affinity / anti-affinity，标为 Proposed |
| 17 | 第四章：Benchmark | 更多 workload，需要可重复的比较 |
| 18 | 框架 | 场景输入、API 与调度器、audit / metrics、报告 |
| 19 | 进展与验证 | 已有入口和采集能力；继续扩展场景、比较优化、重复测试 |
| 20 | 测量口径 | 延迟分布、吞吐窗口与对照条件；后续可换成一项实际结果 |
| 21 | 收尾 | 回扣四部分，邀请集成与测试反馈 |
| 22 | Q&A | 5 分钟 |

## 准备重点

前三章以旧图复用和 API 对照为主，避免引入新故事。PodGroup anti-affinity 是当前能力，SubGroup 关系是后续方向；生态接入深度不同，不能把 gang 接入等同于完整 topology 支持。

Benchmark 先讲已有框架与正在推进的测试。结果只选一个有版本、环境、规模和重复次数的例子；尚未选定前保留测量口径页，不填猜测数字。KWOK 说明调度行为，不证明 GPU 或模型吞吐。

当前保留 Volcano 背景，拿到官方模板后再套版。旧图本身是 PNG，直接复用；新增图、YAML 和注释保存 SVG，再导出固定 PNG。讲者介绍依据公开资料，待讲者偏好补充。最后留两次计时排练，并复核生态 PR 状态。
