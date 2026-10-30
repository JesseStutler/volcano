# Volcano KubeCon NA 2026：演讲大纲

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

Ricardo Aravena · Rainie Li。Latest，共 26 页。[PPT](Volcano_KubeCon_NA_2026.pptx) · [PDF](Volcano_KubeCon_NA_2026.pdf)

从工作负载的不同诉求讲统一调度，再讲完整分组、拓扑放置和抢占。生态案例展示这些意图如何传到 Volcano，最后用 benchmark 和 v1.17 路线收尾。

| 页 | 内容 | 重点 |
|---|---|---|
| 1–2 | 标题、讲者 | Ricardo Aravena / Rainie Li |
| 3 | 第一章：统一调度 | 不同调度路径共享集群 |
| 4 | Training / Inference / Agents | TP/PP、P/D、突发低延迟与预热池复用 |
| 5 | 协同框架 | profile → 路径，实时状态 → 节点池分配 |
| 6 | NodeShard | 策略动态计算 desired nodes，对照实际使用集合 |
| 7 | 第二章：多级 Gang 与网络拓扑 | 完整分组和放置域 |
| 8 | 工作负载内部结构（新增） | PP stage / TP ranks；serving roles / replicas |
| 9 | PodGroup / SubGroup | 整体 admission 与内部完整组 |
| 10 | HyperNode | parent 管子 HyperNode，leaf 管节点 |
| 11 | 多级拓扑放置 | PG 在 core，Prefill 在 leaf，Decode 在 spine |
| 12 | HyperNode 内 gang 抢占（新增） | 选择 victim gang，模拟放置后再驱逐和 nominate |
| 13 | 实例 HA | 完整 PodGroup 分开放在不同 Supernode |
| 14 | SubGroup 关系 | P/D 亲和，Decode 副本反亲和；下一步能力 |
| 15 | 第三章：Ecosystem | 控制器传递分组和拓扑意图 |
| 16 | Kthena 配置 | groupPolicy / rolePolicy 与原图对照 |
| 17 | Kthena 映射（新增） | entry + worker → SG，角色副本数 → minSubGroups |
| 18 | KubeRay | RayCluster 多 host 配置与 PG policy 对照 |
| 19 | Grove | PodGang 内部 groups → Volcano SG policies |
| 20 | 后续生态 | RBG 推进中，Kubeflow / LWS 后续多组与拓扑支持 |
| 21 | 第四章：Benchmark | 从框架到可重复验证 |
| 22 | 已有框架 | 场景、API 事件、指标和报告 |
| 23 | 横向对照 | 固定环境重放相同 workload，逐个比较调度器 |
| 24 | 场景矩阵 | 突发、gang 大小与碎片、网络拓扑 |
| 25 | v1.17 | 抢占质量、SubGroup 关系、性能定位与验证 |
| 26 | Volcano Community / Q&A | 社区 logo，官网、GitHub、Slack 二维码 |

Kthena 的 rolePolicy 当前统一作用于各角色的 SubGroup；anti-affinity 接入仍是 proposal。KubeRay 的 worker-group topology 仍在推进，Grove 当前 backend 不支持 topologyConstraint。状态按 2026-10-30 源码核对，细节和链接在讲者备注。

Benchmark 不填猜测结果。横向比较匹配各调度器支持的语义，寻找适用场景；KWOK 调度测试与真实 GPU 执行性能分开验证。

保留 Volcano 背景及好的 China/EU 原图。新增内容保存 SVG，并将 PNG 固定嵌入 PPT；官方模板到手后再套版。
