# Volcano KubeCon NA 2026：演讲大纲

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

Ricardo Aravena 和 Rainie Li。Latest，共 26 页。[PPT](Volcano_KubeCon_NA_2026.pptx) · [PDF](Volcano_KubeCon_NA_2026.pdf)

从工作负载的不同诉求讲统一调度，再讲完整分组、拓扑放置和抢占。生态案例展示这些意图如何传到 Volcano，最后用 benchmark 和 v1.17 路线收尾。

| 页 | 内容 | 重点 |
|---|---|---|
| 1–2 | 标题、讲者 | Ricardo Aravena / Rainie Li |
| 3 | 第一章：统一调度 | 不同调度路径共享集群 |
| 4 | Training / Inference / Agents | TP/PP、P/D、突发低延迟与预热池复用 |
| 5 | 协同框架 | profile 选择路径，节点状态决定池分配 |
| 6 | NodeShard | 策略动态计算 desired nodes，对照实际使用集合 |
| 7 | 第二章：多级 Gang 与网络拓扑 | 完整分组和放置域 |
| 8 | 工作负载内部结构（新增） | PP stage / TP ranks；serving roles / replicas |
| 9 | PodGroup / SubGroup | 整体 admission 与内部完整组 |
| 10 | HyperNode | parent 管子 HyperNode，leaf 管节点 |
| 11 | 多级拓扑放置 | 不同 SubGroup 可用不同 tier 约束，图中仅为放置示例 |
| 12 | Gang-aware 抢占 | 多个 victim job，优先级与 gang 选择，HyperNode 内模拟可行才提交 |
| 13 | 实例 HA | 完整 PodGroup 分开放在不同 Supernode |
| 14 | SubGroup 关系 | P/D 亲和，Decode 副本反亲和；下一步能力 |
| 15 | 第三章：Ecosystem | 控制器传递分组和拓扑意图 |
| 16 | Kthena 配置 | groupPolicy / rolePolicy 与原图对照 |
| 17 | Kthena 映射（新增） | 图与 YAML 对照：4 个角色副本，4 个 SubGroup，共 8 Pods |
| 18 | KubeRay | head 和两个双 host replica 映射为 3 个 SubGroup，共 5 Pods |
| 19 | Grove | 2 个命名 group 映射为 2 个 SubGroup，共 6 Pods |
| 20 | 后续生态 | RBG 的 PodGroup、SubGroup 和 HyperNode 树查询集成中 |
| 21 | 第四章：Benchmark | 从框架到可重复验证 |
| 22 | 已有框架 | 场景、API 事件、指标和报告 |
| 23 | 横向比较流程 | 固定输入、逐个运行、统一报告、重置重放 |
| 24 | 场景矩阵 | 突发、gang 大小与碎片、网络拓扑 |
| 25 | v1.17 Roadmap | 资源碎片整理、HyperNode/SubGroup、xPU/DRA、生态扩展 |
| 26 | Volcano Users / Q&A | 用户与平台 logo，官网、GitHub、Slack 二维码 |

Kthena 的 rolePolicy 当前统一作用于各角色的 SubGroup；anti-affinity 接入仍是 proposal。KubeRay 的 worker-group topology 仍在推进，Grove 当前 backend 不支持 topologyConstraint。状态按 2026-10-30 源码核对，技术来源在 slide-sources.json。

Benchmark 不填猜测结果。横向比较匹配各调度器支持的语义，寻找适用场景；KWOK 调度测试与真实 GPU 执行性能分开验证。

已使用 NA 2026 官方模板背景。China/EU 原图、SVG 配图及固定 PNG 沿用，26 页英文 Speaker Notes 已调整为无圆点段落并补充例子。
