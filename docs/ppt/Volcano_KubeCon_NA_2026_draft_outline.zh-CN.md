# Volcano KubeCon NA 2026：演讲大纲

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

Ricardo Aravena · Rainie Li。24 页，约 25 分钟正文 + 5 分钟问答。[PPT](Volcano_KubeCon_NA_2026_r6.pptx) · [PDF](Volcano_KubeCon_NA_2026_r6.pdf)

从不同工作负载的调度诉求切入，讲双路径如何协调资源，再落到完整分组、拓扑和组间关系。通过生态案例说明这些需求怎样传给 Volcano，最后讲 benchmark 已有基础与接下来要验证的问题。

| 页 | 内容 | 讲法 / 素材 |
|---|---|---|
| 1–2 | 标题、讲者 | Ricardo：Nunchux AI 的 AI Infrastructure Lead、CNCF TOC Alternate (GB)；Rainie：Pinterest、YuniKorn PMC |
| 3 | 第一章：统一调度 | 不同工作负载怎样共享集群 |
| 4 | Training / Inference / Agents | TP/PP 完整分组、P/D 拓扑、突发与低延迟；agent 先复用预热池，缺容量再调度补池 |
| 5–6 | 双路径、NodeShard | 沿用 China 架构和控制器图；对照 desired / in-use YAML |
| 7 | 第二章：多级 Gang 与网络拓扑 | 分组与放置一起讲 |
| 8–9 | PodGroup / SubGroup、HyperNode | 沿用原图，对照父、叶 HyperNode YAML |
| 10 | 多级拓扑放置 | 沿用 EU / China 网络图，以 highestTierName 表达不同层级 |
| 11 | 实例 HA | 同一 fabric 内，两份完整实例分开放在两个 Supernode；展示 PG anti-affinity YAML |
| 12 | SubGroup 关系 | 沿用同一拓扑：P/D 在 Supernode 内亲和，Decode 副本跨 Leaf 分离；标为 Proposed |
| 13 | 第三章：Ecosystem | 控制器传递角色和副本身份 |
| 14 | Kthena | 沿用 ServingGroup / role replica 映射图和 YAML |
| 15 | KubeRay | 双 host 副本与 SubGroup policy 对照；拓扑接入仍在推进 |
| 16 | Grove | PodGang → PG、内部 PodGroups → SG policies；当前不支持 topologyConstraint |
| 17 | 下一步社区工作 | 带 logo 的 RBG、Kubeflow、LWS；分别讲推进中、后续分组与拓扑、多组支持 |
| 18 | 第四章：Benchmark | 可重复地比较不同调度器 |
| 19 | 已有框架 | 场景、集群、API 事件与报告链路 |
| 20 | 横向对照 | 同环境重放同一 workload，逐个运行调度器，比较延迟、吞吐、完整 gang 和放置 |
| 21 | 场景选择 | 突发、gang 大小与碎片、拓扑约束；找适用场景及其代价 |
| 22 | 后续工作 | SubGroup 关系、社区推进、横向与拓扑测试 |
| 23 | Volcano community | 复用 China 的社区用户 logo |
| 24 | Thank you / Q&A | 官网、GitHub、Slack 二维码；5 分钟讨论 |

PodGroup anti-affinity 是 Volcano 已有能力；Kthena 的对应接入仍是开放 proposal，不能写成已交付。SubGroup affinity / anti-affinity 也明确作为下一步。

Benchmark 讲框架与测试计划，不填猜测结果。横向比较要匹配支持的语义、固定配置并重复运行；KWOK 能验证调度行为，实际 GPU / KV 性能需另测。正文尽量用图，口径、命令和来源放讲者备注。

保留 Volcano 背景，拿到官方模板后再套版。好的旧图继续用；新图保存 SVG，PPT 内嵌固定 PNG。演讲前复核生态状态，并留两次计时排练。

r6 只在页面上保留图、关键标签和必要状态。副标题、重复解释与总结句移到备注，减少全大写和颜色。
