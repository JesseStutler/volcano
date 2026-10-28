# Volcano NA 2026：统一调度框架、多级 Gang 与拓扑的组合叙事

更新：2026-10-28。**这是当前推荐的演讲方案，替代前两版的选题和准备优先级。** 幻灯片使用英文，本稿用于中文讨论与制作。

## 1. 定调：保留标题，用两层协调串起存量与新增内容

正式标题保持不变：

> **Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

沿用已提交的摘要，不再以改题为准备工作的前提。前一版建议整体换题，收缩得过头了：**NodeShard 协同可以继续作为架构主干，多级 Gang、拓扑和生态集成则给这套架构补充具体的工作负载语义与近期进展。**

全场的一句话主线：

> **Volcano coordinates scheduling paths over shared infrastructure, and coordinates workload groups within that infrastructure.**

中文讲法：先解决不同调度路径如何协调使用集群，再解决一个分布式工作负载怎样拿到完整、位置合适的资源组合。

这两个问题互相衔接，但不是同一个实现机制。前半场讲系统如何组织调度，后半场讲工作负载需要调度器理解什么。

### 内容层次

| 层次 | 讲什么 | 本场作用 |
|---|---|---|
| Why | AI 基础设施同时面对持续服务、成组计算和突发需求 | 承接 Agentic AI 标题，提出共享集群的协调问题 |
| Framework | 不同调度路径、NodeShard 协同；简述 worker / Binder | 复用已有架构材料，给讲者保留熟悉的内容 |
| Workload semantics | PodGroup / SubGroup、多层拓扑边界、PodGroup anti-affinity | 正文重点；解释框架如何承载具体的训练和推理需求 |
| Ecosystem and next steps | Kthena、KubeRay、Grove，后续 Kubeflow / LWS 与 SubGroup 关系 | 展示 NA 相比前两场的进展，并连接实际后续投入 |

“统一”在这里表示这些能力围绕共享 Kubernetes 基础设施形成一个框架，不要求所有工作负载采用同一调度算法，也不表示所有 Agent 的执行单元都成为 Pods。

### 保留与取舍

- **保留 NodeShard 与协调架构。** 讲已经实现的机制、适用范围和设计取舍，不把它撤到备份页。
- **乐观并行简讲机制。** 可在框架页用约 30–45 秒介绍 worker / Binder 的本地冲突处理；没有证据就不宣称吞吐提升或全局一致性已经解决。
- **新增篇幅优先给组调度、拓扑关系和生态进展。** 这部分同时支撑本场差异性和后续研发方向。
- Global / 混部可作为项目已有覆盖面，在结束前用一句话带过；没有近期推进就不单开章节。已有相关图可留备份。
- Unschedulable Job Cache 不进入正文，也不为这次演讲另起 fast-path benchmark 工作。

## 2. 怎么把几个部分讲成一个故事

### 开场：Agentic AI 是背景，共享基础设施是问题

建议开场用约一分钟说明：Agent 应用依赖推理服务，平台也继续运行训练和其他成组计算；这些工作负载的资源形态、到达节奏和调度需求不同。Volcano 的切入点是底层 Kubernetes 工作负载的资源协调与放置。

不要把“Agent 调用 → 新建一个 Pod → Agent Scheduler”画成必然路径。图中可把 Agent applications 放在推理服务上方，训练放在旁边作为模型生命周期的一部分；不要暗示所有 Agent 请求都触发训练或 RL。

关于 CubeSandbox / Agent Substrate 的讨论放在讲者备注和 Q&A：这些系统可以在 Kubernetes 提供的 worker / 资源池之上自行调度 sandbox 或 actor。这说明 Agent 调用量不等于逐 Pod 调度量，但并不消除基础设施层的放置问题。[Substrate architecture][substrate] [CubeSandbox architecture][cube]

### 第一段：调度路径如何协调——复用 NodeShard

保留现有双路径架构图，依次讲：

1. 不同 workload 有不同的调度需求，框架可以保留不同执行路径。
2. NodeShard 用于表达和协调 scheduler 的候选节点范围；controller 负责分配，coordinator 与调度周期同步节点使用状态。
3. worker / Binder 的冲突处理属于一个调度路径内部的机制，与 NodeShard 的跨 scheduler 协同分开讲。

这里的演讲目标是让听众看懂组件职责和资源范围如何交接。NodeShard 调整不迁移已运行的 Pods，也不自动提供跨 scheduler 的强一致配额与全局公平性。[Agent scheduler design][agent-design]

### 核心转场：拿到候选节点，不等于工作负载已经能运行

建议讲者直接使用：

> “So far, we have discussed how scheduling paths coordinate their use of cluster nodes. But a set of available nodes is not enough for a distributed AI workload. We also need complete groups, the right topology, and placement relationships between groups.”

中文理解：前面讲的是调度路径如何协调使用节点。接下来，即使有足够的空闲资源，也可能凑不齐一个完整副本，或者这些资源分散在不合适的网络位置上。

用同一个集群底图完成转场：上一页标出 scheduler 的候选范围；下一页去掉 shard 着色，标出物理拓扑域与工作负载分组。**不要画成 NodeShard → HyperNode → SubGroup 的包含树。**

| 概念 | 回答的问题 | 不应混淆的边界 |
|---|---|---|
| NodeShard | 一个 scheduler 在当前配置和周期下可以或优先考虑哪些节点？ | `none` / `soft` / `hard` 不同，不能把所有模式都说成互斥节点池 |
| PodGroup / SubGroup | 哪些成员、哪些完整副本必须满足成组条件？ | 不是所有进程同时启动，也不是跨 Pod 原子 bind |
| HyperNode / networkTopology | 一个 group 应该落在哪个层级的拓扑范围？ | 描述基础设施拓扑，不表示 scheduler 对节点的所有权 |
| Group affinity / anti-affinity | 不同组应该靠近还是分开？ | PodGroup anti-affinity 已有，SubGroup 关系仍为后续方向 |

概念上，放置需要同时满足当前候选范围、资源条件与 workload 约束；本场不把这描述为已经交付了“拓扑感知的自动 shard 联合优化”。hard shard 如果切开有用的拓扑域，也会限制 group placement 的选择，这是可以在 Q&A 解释的取舍。

### 第二段：工作负载内部如何协调——用同一案例逐步增加约束

顺序保持简单：**完整副本 → 组内拓扑 → 组间分离 → 生态控制器传递这些语义。** Kthena 的 P/D 场景贯穿 Gang 与拓扑，KubeRay 的 multi-host replica 用来证明这一需求也来自其他生态。

未来 SubGroup affinity / anti-affinity 是这一案例自然长出来的下一问：现在可以限制组内范围、分开两个 PodGroups；下一步希望表达同一个 PodGroup 内不同 SubGroups 的靠近或分散。

### 对原摘要承诺的处理

框架、协调、多路径与 topology 都保留，实际讲解重心落在可说明的机制与近期进展。旧 benchmark 只有在版本、环境、负载和测量对象可追溯时才复用，并明确它验证的具体能力；不能用原有 batch scheduler 数据证明新的并行架构。没有适合的数据，就使用放置行为案例，不在准备期临时补一套性能故事。

Global 和混部不承诺新增成果；需要呼应摘要时，可在社区页标为已有能力，用 20–30 秒说明本场重点放在当前推进的组调度和拓扑生态。

## 3. NA 相比 EU / China 的实际增量

复用基础知识是合理的。NA 应把已讲过的原语作为基础，用近期交付、具体集成和新的组间问题推进故事。

| 基础材料 | NA 的推进 | 是否为近期新成果 |
|---|---|---|
| PodGroup / SubGroup 的概念图 | 用 KubeRay 的完整 multi-host replica 解释为什么一个总 minMember 不够 | KubeRay SubGroupPolicy PR 于 2026-09-22 合并，在 China 场之后 |
| HyperNode 树、组内拓扑边界 | 加入“每个实例内部聚拢、不同实例之间分离”的组合场景 | PodGroup anti-affinity PR 于 2026-10-09 合并，并进入 v1.16 |
| China 中“将于 v1.16 发布”的 standalone 页 | 明确独立 controller 已交付，说明 API 消费与现成 scheduler 集成的区别 | v1.16 于 2026-10-14 发布 |
| Kthena 的 ServingGroup / Role | 作为已有完整案例，与 KubeRay / Grove 的映射比较 | Kthena 是已存在能力，不能重新称为 NA 新功能 |
| Grove 的 Volcano backend | 展示已合并的 SubGroup gang 映射和仍缺少的 topology 接入 | PR 于 2026-06-15 合并，是生态证据，不是 China 后的新交付 |
| 泛化的 topology roadmap | 具体到 SubGroup affinity/anti-affinity、KubeRay group topology、Kubeflow/LWS 深化 | 一部分为在审 PR，一部分为计划；逐项标状态 |

来源：[Grove #516][grove]、[KubeRay #5249][ray-gang]、[KubeRay #5369][ray-topo]、[PodGroup anti-affinity #5349][pg-aa]、[v1.16 release][r16]。

**差异性的来源：** 以前介绍“有什么能力”，这次讲“这些能力如何组合、哪些 controller 已经使用、下一步还缺什么关系表达”。不要求所有页面都是今年首次出现的概念。

## 4. 主案例：同一个服务的角色、完整副本与多个实例

建议沿用 Kthena 的 Prefill / Decode 视觉语言，但用同一例子逐步增加约束：

1. **完整性：** 服务实例需要一定数量的完整 Prefill 和 Decode 副本。一个角色多出来的 Pods 不能弥补另一个角色缺失的完整副本。
2. **局部性：** 一个 multi-Pod replica 在较低层 HyperNode 内；整个实例在更大的拓扑范围内。
3. **可用性：** 服务有两个实例，对应两个 PodGroups；每个实例保持内部局部性，实例之间通过 PodGroup anti-affinity 分散到不同 supernode。
4. **下一步：** 在同一 PodGroup 内，选择哪些 SubGroups 必须靠近，哪些应分散。这一步明确标为 Proposed。

图中始终用相同颜色表示角色，用边框表示副本组，用背景区域表示 HyperNode；颜色不要同时承担角色、状态和版本三个含义。

一个重要术语区别：**一个 `subGroupPolicy` 可以生成多个实际 SubGroups。** 比如 KubeRay 的 WorkerGroup 可以有多个 logical replicas，每个 multi-host replica 对应一个 SubGroup。不能把 WorkerGroup、policy 和一个实际 SubGroup 全都画成同一个对象。

Kthena 的角色也可有多个完整副本。因此，讲“Role maps to SubGroup”时需要补足“policy 定义角色选择与副本划分”的含义，避免误导为整个角色永远只有一个 gang。

## 5. 全场结构：四章，16 页正文 + Q&A

25 分钟正文 + 5 分钟问答。架构部分约 6 分钟，保留 NodeShard 的讲解空间；工作负载语义约 10 分钟，是正文重点；生态与后续方向共 9 分钟。

| 章节 | 页码 | 时间 | 回答的问题 |
|---|---|---:|---|
| 1. Coordinating scheduling paths | 1–5 | 6:00 | 不同路径如何使用同一集群？协调完节点范围之后还缺什么？ |
| 2. Coordinating workload groups | 6–10 | 10:00 | 如何获得完整副本、合适拓扑与实例分离？ |
| 3. Bringing workload semantics into the ecosystem | 11–13 | 4:00 | 哪些 controller 已经传递这些语义？哪些能力可独立复用？ |
| 4. What comes next | 14–16 | 5:00 | 怎样补齐 SubGroup 关系和生态接入？社区可以参与什么？ |

### 逐页内容

| 页 | 英文标题 | 时间 | 上屏内容 / 核心结论 | 旧资料与新增处理 |
|---|---|---:|---|---|
| 1 | Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents | 0:30 | 原标题、讲者；用两层协调组织整场 | 保留登记标题，采用简洁封面 |
| 2 | Different Workloads, Shared Infrastructure | 1:00 | Agent applications 依赖 inference；旁列 training / grouped compute；落到共享 Kubernetes 资源 | 复用生命周期素材，删去每个 Agent 都对应一个 Pod 的暗示 |
| 3 | A Coordinated Scheduling Framework | 1:30 | 双路径框架；worker / Binder 内部机制用 30–45 秒，主要说明组件职责 | China 第 7–8 页 / EU 第 9 页合并；不放未经验证的性能数字 |
| 4 | NodeShard: Coordinating Node Access | 2:00 | controller → NodeShard → coordinator；以一次节点范围调整解释调度周期同步 | China 第 9 页 / EU 第 10–11 页；CRD 全文留备份 |
| 5 | Available Nodes Are Only the Beginning | 1:00 | 空闲资源足够，仍可能缺完整副本或局部拓扑容量；区分 NodeShard 与 HyperNode | 新增转场图，沿用同一集群底图 |
| 6 | PodGroup and SubGroup: Preserving Complete Replicas | 2:30 | 从总 minMember 的不足切入；用 Kthena P/D 角色与多 Pod 副本解释两级 gang | China 第 14、22 页合并；policy 与实际 SubGroup 分开标注 |
| 7 | HyperNode: Expressing Topology Domains | 2:00 | supernode / rack / node 树；域与层级，hard / soft topology constraint | China 第 16 页；一棵树取代多套网络与代码截图 |
| 8 | Place Groups at Different Topology Levels | 2:00 | 整个 P/D 实例在较大域内，每个完整副本在较小域内 | China 第 17 页 / 中文实践稿第 21 页，延续第 6 页角色颜色 |
| 9 | Keep Each Instance Together, Separate Different Instances | 2:00 | 复制为两个服务实例；组内 networkTopology 与组间 PodGroup anti-affinity 组合 | China 第 15 页更新为 v1.16 已发布能力，这是 NA 的新增重点 |
| 10 | When Placement Rules Cannot Be Satisfied | 1:30 | required 无合法域时 Pending，preferred 可退化；一组成功 / 失败放置对照 | 新增静态案例；可用 45–60 秒录屏代替部分讲解 |
| 11 | Controllers Bring Workload Structure to Scheduling | 2:00 | Kthena / KubeRay / Grove 已有能力与在推进能力；Kubeflow / LWS 已有基础及深化方向 | 新做能力矩阵，使用第 6 节核查结果 |
| 12 | KubeRay: A Replica Can Span Multiple Pods | 1:00 | `minReplicas=2, numOfHosts=2` 需要两个完整双 Pod 副本；gang 已合并，topology 在推进 | #5249 / #5369；不再重新解释整套 SubGroup API |
| 13 | HyperNode Beyond a Single Scheduler | 1:00 | standalone discovery/controller → HyperNode API → consumers | China 第 19 页从“将发布”改为“已交付”；adapter 状态单独标注 |
| 14 | Next: Relationships Between SubGroups | 2:00 | 回到主案例，展示同一 PodGroup 内的 colocate / separate；明确 Proposed | 新增两幅小图；与第 9 页已交付能力区分 |
| 15 | From Placement Primitives to Ecosystem Adoption | 1:30 | SubGroup 关系语义 → controller 映射 → 真实场景验证；拓扑 adapter / xPU 等只选一行中期方向 | 摘取 v1.17 roadmap 中与主线相符的事项，标状态，不承诺全部按期交付 |
| 16 | One Framework, Workload-Aware Placement | 1:30 | 回顾路径协调、成组与拓扑、生态；贡献入口与真实场景征集 | 可用 20–30 秒提及 Global / 混部已有覆盖面，其余聚焦当前推进 |
| 17 | Questions? | 5:00 | Q&A，保留两层协调的小图 | 简洁收尾 |

### 讲者衔接

熟悉 NodeShard 的讲者负责第 1–5 页，交接句直接使用第 2 节的转场。下一位讲者从“候选节点足够为什么还不能运行”开始讲第 6–10 页，不再重新介绍 Volcano。若三位讲者分工，第三位接第 11–16 页，围绕生态采用与未来关系展开；具体人选由团队按熟悉程度安排。

时间不足时先合并第 11–12 页，把 KubeRay 例子放进能力矩阵的讲者备注；再将第 10 页录屏改成静态图。保留第 5 页的转场与第 14 页的未来方向，它们负责把各部分连起来。

## 6. 生态矩阵：需要区分语义映射与交付状态

截至 2026-10-28 核对。PR 已合并不自动表示某个下游稳定发行版已经包含该功能；正式 slide 的版本号在演讲前再次核对。

| 社区 | 已有 / 已合并 | 当前明确的边界 | NA 要表达的下一步 |
|---|---|---|---|
| Kthena | 已有 ServingGroup / Role gang 映射；已有 group / role network topology 文档 | SubGroup 之间的新 affinity 规则不能由已有组内 topology 推导出来 | 继续作为完整角色语义的实例，按具体需求接新组间关系 |
| KubeRay | #5249 已合并，从 replica identity、`numOfHosts`、`minReplicas` 生成 SubGroupPolicy | 每个 logical replica 对应实际 SubGroup；不是任意四个 Pods 就等于两个完整副本 | #5369 的 replica topology 仍 open；之后再结合真实需求处理组间关系 |
| Grove | #516 已合并，最终代码生成 SubGroupPolicy，要求支持对应字段的 Volcano CRD | 当前 backend 显式拒绝 Grove topology constraints | 推进 topology 语义映射；不把 gang backend 宣称为完整拓扑集成 |
| Kubeflow Trainer | 已有 Volcano plugin / PodGroup 接入 | “推进集成”不代表此前完全没有集成 | 扩展 TrainJob 的更细分组与拓扑表达，列为计划 |
| LWS / DisaggregatedSet | LWS 的 gang scheduling + Volcano 实现 #498 已于 2025 年合并 | LWS 自身的 subgroup 概念与 Volcano SubGroup 不因同名就自动等价 | 探索 roles / slices / leader-worker 单元如何映射多级 Gang 与组间拓扑关系 |

核查说明：Grove #516 的 PR 初始说明仍有较早的 API 版本措辞，因此上述判断同时核对了最终 merged diff 中的 `subGroupPoliciesForPodGang`、CRD 能力检查和 topology 校验代码，不能只引用 PR 标题。

来源：[Kthena gang][kthena-gang]、[Kthena topology][kthena-topo]、[Grove][grove]、[KubeRay gang][ray-gang]、[KubeRay topology][ray-topo]、[Kubeflow Trainer][trainer]、[LWS gang PR][lws-gang]、[DisaggregatedSet][dset]。

## 7. 演讲中的未来方向，应与真正准备投入的研发一致

### 近期主线 A：补齐组间关系表达

从已交付的 PodGroup anti-affinity，向同一 PodGroup 内的 SubGroup affinity / anti-affinity 推进。

需要明确：关系作用于哪些实际 SubGroups、指定哪个 HyperNode tier、required / preferred 的语义、多个 policy 生成多个副本时怎样匹配、规则不可满足时怎样解释。不要先增加字段再寻找需求。

**推荐可展示的成果：** 一套清楚的语义、两个真实场景、可复现的成功/失败行为。对应 [#5347][group-issue]。

### 近期主线 B：让生态控制器完整传递这些语义

优先选择已经有合作基础的 controller，把“角色/副本身份 → SubGroupPolicy → 拓扑边界 → 组间关系”串起来。

- KubeRay：继续现有 replica topology 工作，确认粒度与用户需求一致。
- Grove：从 gang backend 扩展到正确的 topology mapping。
- Kubeflow / LWS：在已有接入上扩展，不另起一个泛化“从零支持”项目。
- Kthena：作为现有参考实现和验证场景，但不把其 API 强制映射为其他项目的模型。

**推荐可展示的成果：** 每个集成都有能力矩阵、版本条件、一个可跑例子，以及保留语义的测试。新增 logo 数量不是验收标准。

### 中期主线 C：扩展拓扑能力的复用和设备表达

HyperNode standalone 已经提供可复用的基础；后续关注 scheduler adapter 和发现源，以及与 xPU / DRA / GPU-NIC locality 的具体协作场景。

这条线放在 roadmap 的后半部分。先以一个现实互联场景验证，不把 arbitrary topology、multi-rail、全设备协同都包装为 v1.17 一次交付。

### 资源回收与重整的位置

Gang-aware reclaim / defragmentation 与“让工作负载获得完整、合适的资源组合”相关，可以在有人持续推进、已有证据时作为后续扩展。**它们不是本场必须凑满的一条平行主线。** checkpoint、跨集群、混部同理，不因旧材料里出现过就继续占用正文。

上述是根据用户确认的实际推进方向与 [v1.17 roadmap][r17]整理的优先级建议，不是新增的社区交付承诺。

## 8. 剩余约十天：复用架构，集中准备转场和新增证据

### 必做

1. **D1：** 保留原标题和摘要，确定 16 页正文与讲者分工；先由熟悉 NodeShard 的讲者确认第 3–5 页。当天写好两段交接话，不再扩展选题。
2. **D2–D3：** 固定一套已发布组件版本，验证 PodGroup anti-affinity 的两个行为：资源足够时分域；required 无合法域时 Pending。已有环境可以加 preferred 对照。
3. **D3–D5：** 完成整套粗稿。复用双路径 / NodeShard / Gang / HyperNode 图，统一字体、线条和颜色；重点新做转场、anti-affinity 组合图、生态矩阵和 SubGroup 关系展望。
4. **D6：** 计时排练；检查架构段能否收在 6 分钟、交接是否自然，以及 NodeShard / HyperNode、policy / 实际 SubGroup 是否讲清。
5. **D7–D8：** 修图、录短演示、联合排练；重新核对在审 PR 状态。
6. **D9–D10：** 内容冻结，准备 PDF、离线录像、静态截图和问答，预留差旅时间。

### 小演示建议

以 [PodGroup anti-affinity 用户指南][aa-guide]为基础，使用 CPU 请求与少量测试 Pods 即可验证调度语义。明确这是逻辑 HyperNode 拓扑上的放置演示，不证明真实网络通信性能或硬件故障恢复效果。

固定同一拓扑，呈现三步：

- 两个 PodGroups 各自约束在一个 supernode 内，并设置相互分离规则。
- 查看成员实际节点和 HyperNode 归属，确认组内聚拢、组间分离。
- 在隔离测试配置中制造无合法域的情况，展示 required 的 Pending 与解释；可再用独立案例展示 preferred 退化。

如果没有现成环境，先用准确的逐步图完成内容；演示是增强项，不让整套 PPT 被环境搭建拖住。不需要在剩余时间里跑一套新的乐观并行性能论证。

### 备份页

- NodeShard CRD、`none` / `soft` / `hard` 模式、节点范围交接细节；worker / Binder 冲突处理。
- 已有 benchmark 的原始环境、版本和结果（仅在能准确解释测量对象时复用）；Global / 混部存量图。
- 关键 API 与 plugin 启用要求；required/preferred；allocate/backfill 的执行范围。
- 生态项目版本条件与 source links。
- SubGroup 关系提案尚未实现的字段和开放语义问题。
- 按需准备 fairshare / NamespaceQueue 等其他更新一页，仅回答问答。

## 9. 图和措辞的准确性

- NodeShard 的候选范围协调、worker / Binder 的本地冲突处理、PodGroup 的成组约束是不同机制；不因它们出现在同一架构图上就宣称全局事务一致性。
- NodeShard 与 HyperNode 分开编码：前者用 scheduler 范围边框，后者用基础设施区域；不绘制虚构的固定父子层级。
- 架构目标与测量结果分开：可以解释为何采用并行或协调设计，不能把设计动机写成已经验证的吞吐、延迟收益。
- `networkTopology` 回答一个 group 的拓扑边界；PodGroup anti-affinity 回答不同 PodGroups 的分离关系；未来 SubGroup affinity/anti-affinity 回答同一 PodGroup 内的组间关系。三者分开画，再展示组合。
- 不将 gang scheduling 描述为所有进程在同一时刻启动，或 Kubernetes 提供跨 Pod 原子 bind；重点是调度中的成组条件与完整成员要求。
- 当前 PodGroup anti-affinity 需要启用 plugin，主要通过 allocate 执行；不承诺 backfill 放置的 BestEffort Pods 同样受约束。
- 规则选择 PodGroup labels；相互隔离的每个 PodGroup 都需要配置对应规则。controller 接入时需确认字段被保留。
- topology domain 只有在基础设施映射正确时才代表相应故障域；分散放置不自动提供应用 failover 或可用性 SLO。
- 后续 SubGroup 规则属于 Proposed；不把设计文档中的示例当作当前可执行配置。
- 使用用户指定 SVG 的白底、浅蓝灰边框与真实 logo。主场图保留可编辑矢量，一页只增加一层新语义。

## 10. 主要来源

[agent-design]: https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/design/agent-scheduler.md
[shard-config]: https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/user-guide/how_to_configure_sharding_configmap.md
[r16]: https://github.com/volcano-sh/volcano/releases/tag/v1.16.0
[r17]: https://github.com/volcano-sh/volcano/issues/6166
[pg-aa]: https://github.com/volcano-sh/volcano/pull/5349
[group-issue]: https://github.com/volcano-sh/volcano/issues/5347
[aa-guide]: https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/user-guide/how_to_use_podgroup_anti_affinity.md
[kthena-gang]: https://github.com/volcano-sh/kthena/blob/main/docs/kthena/versioned_docs/version-v1.0.0/user-guide/gang-scheduling.md
[kthena-topo]: https://github.com/volcano-sh/kthena/blob/main/docs/kthena/versioned_docs/version-v1.0.0/user-guide/network-topology.md
[grove]: https://github.com/ai-dynamo/grove/pull/516
[ray-gang]: https://github.com/kuberay-project/kuberay/pull/5249
[ray-topo]: https://github.com/kuberay-project/kuberay/pull/5369
[trainer]: https://trainer.kubeflow.org/en/latest/operator-guides/job-scheduling/volcano.html
[lws-gang]: https://github.com/kubernetes-sigs/lws/pull/498
[dset]: https://lws.sigs.k8s.io/stable/docs/concepts/disaggregatedset/
[substrate]: https://github.com/agent-substrate/substrate/blob/main/docs/architecture.md
[cube]: https://github.com/TencentCloud/CubeSandbox/blob/master/docs/guide/kubernetes/architecture.md

- [Agent scheduler / NodeShard 设计][agent-design]与[sharding 配置][shard-config]
- [官方场次](https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/program/schedule/?id=1289640)
- [旧 PPT 素材目录](https://github.com/JesseStutler/volcano/tree/docs/kubecon-na-2026-assets/docs/ppt)
- [PodGroup / SubGroup 关系设计](https://github.com/volcano-sh/volcano/blob/v1.16.0/docs/design/group-topology-affinity.md)
- [v1.16 release][r16]、[v1.17 roadmap][r17]
- [Grove][grove]、[KubeRay gang][ray-gang]、[KubeRay topology][ray-topo]
- [Kthena gang][kthena-gang]、[Kthena topology][kthena-topo]
- [PodGroup anti-affinity 实现][pg-aa]与[用户指南][aa-guide]
- [Kubeflow Trainer][trainer]、[LWS][lws-gang]、[DisaggregatedSet][dset]
- [Agent Substrate][substrate]、[CubeSandbox][cube]
