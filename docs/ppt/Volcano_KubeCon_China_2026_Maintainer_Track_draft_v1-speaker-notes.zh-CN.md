# Volcano KubeCon China 2026 演讲备注

对应文件：`Volcano_KubeCon_China_2026_Maintainer_Track_draft_v1.pptx`

演讲时长按 30 分钟准备。正文约 24 分半，剩余时间用于现场停顿、翻页和问答。以下内容是提词稿，不需要逐字照读。

## 1. Volcano: A Unified Scheduling Platform for Cloud Native AI

> 建议用时：30 秒

大家好，我是来自华为的陈子聪，旁边是来自商汤的王东阳。我们都是 Volcano Maintainer。

今天分享的主题是云原生 AI 的统一调度。这里的“统一”不是让训练、推理和 Agent 走完全相同的调度逻辑，而是让它们共享同一套资源管理基础，再根据不同的工作负载语义选择合适的调度路径。

## 2. Speakers

> 建议用时：30 秒

我主要参与 Volcano 调度器、网络拓扑感知和相关社区工作。东阳长期从事云原生 AI 基础设施，也在参与 Volcano 和 Kthena 的设计与实现。

今天的内容既包含 Volcano 已经在生产环境使用的能力，也包含社区正在推进的设计。涉及演进中的部分，我们会明确说明，不把方案当成现状。

## 3. Agenda

> 建议用时：45 秒

整场分享沿着一条资源链路展开。

第一部分从工作负载变化出发，解释为什么同一个 Kubernetes 集群需要支持不同的调度语义。第二部分进入 Volcano 调度器，重点看快速调度、资源共池、Gang Reclaim 和网络拓扑。第三部分再向上走到模型服务，介绍 Kthena 如何表达 ServingGroup、Prefill、Decode，以及如何把这些语义交给 Volcano。

后面的链路会从集群里的 GPU 分配一直追到一次推理请求最终选择哪个实例。

## 4. AI Workloads Are Diverging

> 建议用时：1 分 15 秒

早期 AI 集群主要服务离线训练。作业运行时间长，优化目标通常是吞吐量，调度器可以花更多时间寻找较好的放置结果。

大模型训练把规模推到数百甚至数千张卡，Gang、队列公平性和网络拓扑开始直接决定作业能不能运行。进入大模型推理以后，Prefill 和 Decode 可以拆成不同的资源池，调度对象不再只是一个 Deployment。Agent 工作负载又带来大量短生命周期任务，它们对排队延迟非常敏感，但单个任务本身可能只运行几秒。

这些负载共享 GPU、CPU 和网络，却有完全不同的执行节奏。把每类负载做成一套独立资源池，隔离简单，但资源碎片和利用率问题会越来越严重。更合适的方向是共享资源视图，同时保留针对训练、推理和 Agent 的专用调度路径。

## 5. Volcano Overview

> 建议用时：1 分 10 秒

Volcano 的核心定位不是单一的 Batch Scheduler，而是面向云原生高性能工作负载的调度平台。

向下，它管理 GPU、NPU、NUMA 和网络拓扑等异构资源；向上，它接收 Kubernetes 原生工作负载，以及 PyTorch、TensorFlow、Spark、Ray、Flink 等框架提交的任务。中间通过 PodGroup、Queue 和一组可组合的调度插件表达 Gang、Fair Share、Binpack、DeviceShare 等策略。

多集群和混部能力解决的是资源池规模与利用率问题，队列和多种调度策略解决的是不同租户、不同负载之间如何共享资源。后面介绍的 Agent fast path、Gang-aware reclaim 和 Kthena，并不是几套互相独立的系统，它们都建立在这套资源与策略基础上。

## 6. Unified Scheduling Architecture

> 建议用时：1 分 20 秒

调度器收到的不应该只有一个待调度 Pod。工作负载类型、`schedulerName`、优先级、延迟目标、吞吐目标、Gang 结构、角色分组以及网络边界，都会改变正确的调度决策。

节点侧信息也不只是剩余多少 CPU 和 GPU。实时利用率、设备健康状态、NUMA 位置和网络拓扑都会影响一次绑定是否有效。Volcano 把这些信息汇总到统一控制面，但不会强迫所有工作负载通过同一条串行路径。

长时间运行的训练任务适合做更完整的队列与拓扑决策；短生命周期 Agent 任务更关心调度延迟。Dynamic NodeShard 在共享节点池上划出动态候选范围，让不同调度路径可以并行工作，又不需要把物理集群永久切成多个资源孤岛。

## 7. Fast-Path Agent Scheduling

> 建议用时：1 分 10 秒

Agent 任务的典型特点是突发、数量多、生命周期短。它们如果进入面向大型 Batch Job 的完整调度周期，调度开销可能已经接近任务自身的运行时间。

Fast path 使用多个 worker 并行读取共享的集群快照，各自完成候选节点筛选和放置决策。绑定阶段再做冲突检测；如果资源版本或节点状态已经变化，就放弃这次乐观结果并重新调度，而不是依赖一个全局大锁串行处理所有任务。

这条路径缩短的是短任务的排队和决策时间。它仍然需要与 Batch Scheduler 共享资源边界，否则快速调度只会把冲突推迟到绑定阶段。这个共享边界由下一页的 NodeShard 提供。

## 8. Dynamic Node Sharding

> 建议用时：1 分 5 秒

静态分池通常按照节点标签把集群长期切开。它能减少调度器之间的冲突，但一边资源空闲、另一边任务排队时，节点无法及时流动。

Sharding Controller 根据策略和实时负载计算候选节点集合，并通过 NodeShard CRD 把边界交给不同调度器。可以是 Agent Scheduler 和 Batch Scheduler 的组合，也可以是多个 Batch Scheduler 分担超大规模集群。

NodeShard 表达的是动态调度范围，不是新的物理资源池。边界可以随着负载变化而调整，调度器只在自己的候选集合内做高频决策。这样既降低单个调度器的搜索空间，也保留资源重新分配的能力。

## 9. Colocation Foundations

> 建议用时：1 分 5 秒

统一资源池不等于让在线和离线 Pod 无约束地争抢资源。混部能否落地，关键在节点侧是否有稳定、可观测、可回退的资源控制。

Volcano 已经把混部能力从特定操作系统发行版中解耦，能够在 Ubuntu、CentOS 等通用环境运行，并自动识别 cgroup v1 和 v2。CPU throttling 根据在线负载动态调整离线 Pod 的配额，CPU Burst 则允许延迟敏感任务在短时间内使用更多算力。Memory QoS 用更细粒度的回收与保护策略降低在线任务被干扰的风险。

ColocationConfiguration 把这些控制策略声明化。调度器决定工作负载放到哪里，节点侧资源管理器负责运行期间的隔离和调整。资源能够安全共池以后，下一步才是高优先级负载到来时应该从谁手里拿回资源。

## 10. Why Pod-Level Eviction Fails

> 建议用时：1 分 20 秒

这里有四个训练作业，每个作业由四个 worker 组成。Serving PodGroup 需要四张 GPU，如果按照 Pod 粒度，从每个训练作业各驱逐一个 worker，表面上正好释放四张卡。

问题是四个训练作业都只剩下三分之四的成员。分布式训练依赖所有 rank 共同推进，剩余十二个 worker 占着 GPU，却无法继续完成有效计算。调度器满足了“释放四张 GPU”这个局部目标，但集群里同时出现一个正在运行的 Serving Gang 和四个停滞的训练作业。

Reclaim 的 victim 不能只按单个 Pod 的资源值来选择，还要理解工作负载的整体结构。对 Gang Job 来说，完整驱逐一个作业通常比破坏四个作业更可控。

## 11. Gang-Aware Preempt / Reclaim

> 建议用时：1 分 10 秒

图中的结果来自专用 `gangreclaim` action。调度器在目标 HyperNode 内按 Job 构造 victim bundle；安全余量不足时，可以选择会破坏整个 Gang 的 whole bundle。这个例子最终选中了 Training Job A 的 whole bundle，A 的四个成员一起退出，Training Job B 不受影响。

释放出来的资源能够完整容纳等待中的 Serving PodGroup，因此四个 Serving Pod 可以一起进入 pipeline。目标 Job 完成放置模拟并达到 Pipelined 状态后，`Statement.Commit()` 才提交 eviction 和 nomination。

`gangreclaim` 需要在调度器 action 列表中明确配置；原有 `reclaim` action 仍然从单个 task 出发选择 victim。两条路径不能混为同一个默认行为。即使使用 whole bundle 完成资源交接，被驱逐训练任务最近一段计算进度如何保留，仍然是另一个层面的问题。

## 12. Recoverable Handover

> 建议用时：1 分 30 秒

Volcano 当前执行 Gang Reclaim 时，选定 victim 后会通过 `Statement.Commit()` 提交驱逐，完整 victim job 的成员退出，四张 GPU 随后供 Serving PodGroup 使用。这个路径能够保证资源按 Gang 交接，但训练任务最近一次持久化之后的进度仍可能丢失。

社区希望把 checkpoint 引入资源交接过程。Scheduler 仍然负责识别完整的 victim job；训练控制器协调各个 rank 保存模型、optimizer、RNG 状态以及 rank 与 shard 的对应关系。所有 checkpoint 都持久化以后，控制器再整体驱逐，后续可以从 manifest 指向的状态恢复训练。

图里的 `ReclaimIntent`、`checkpointRef` 和 `restoreFrom` 都不是 Volcano 当前已经发布的 API。`restoreFrom` 属于上游 Pod Checkpoint/Restore 的探索路径，Kubernetes Checkpoint/Restore Working Group 和 KEP-5823 面向的是更长期的 Pod 原生恢复。当前 `Statement.Commit()` 不会等待 checkpoint，Scheduler 与训练控制器之间也没有这套握手；近期更现实的实现仍然依赖训练框架和 Job Controller。

## 13. PodGroup and SubGroup

> 建议用时：1 分 25 秒

PodGroup 能表达整个作业的准入条件，例如 `minMember` 和最小资源量。它可以保证成员足够时才启动，但一个扁平 PodGroup 无法说明哪些 Pod 构成 TP group、PP stage，或者 Prefill、Decode 角色。

SubGroup 模型把作业内结构带入调度器。PodGroup 仍然是完整训练作业或 ServingGroup 的 Gang 边界；SubGroup 描述 TP、PP、DP 或推理角色内部需要共同放置的成员；Pod 最终承载具体实例。

当前 PodGroup v1beta1 已经提供 `subGroupPolicy`。实际字段包括 `subGroupSize`、`minSubGroups`、`labelSelector`、`matchLabelKeys` 和 `networkTopology`，调度器可以同时检查全局 Gang readiness 与局部角色约束。较旧版本没有这层能力，部署时需要确认 Volcano 与 CRD 版本；后续 API 仍会继续演进。

## 14. Topology Placement by Group

> 建议用时：1 分 10 秒

完整作业和内部角色对网络范围的要求通常不同。PodGroup 可以允许整个作业跨越较高层级，例如同一个 Core 域；Prefill SubGroup 对 KV 构建和高带宽通信更敏感，可以要求所有成员留在同一个 Leaf；Decode 可以优先放在一个 Leaf，资源不足时再按照策略向上放宽。

调度结果必须同时满足三类条件：完整 PodGroup 能够进入 pipeline，关键角色达到最小成员数，每个分组又处在允许的拓扑边界内。只满足总 GPU 数量不够，四张卡分散在两个 Leaf 时，要求单 Leaf 的 SubGroup 仍然不能启动。

这种分层约束让 Gang Scheduling 从“成员数量够不够”扩展到“成员能不能以正确的通信结构一起运行”。

## 15. Multi-Level Network Topology

> 建议用时：1 分 5 秒

HyperNode 把物理网络组织成可供调度器计算的层级树。Tier 1 可以对应 Leaf 或机架内高速域，Tier 2 对应 Spine 范围，Tier 3 再覆盖更大的 Core 域。具体层级名称由集群网络定义，调度器使用的是统一的 HyperNode 抽象。

图中的 PodGroup 有八个成员，允许最高跨到 Tier 3，因此完整作业可以分布在更大的域内。Prefill 分组的四个成员限制在 Tier 1；Decode 分组允许到 Tier 2。两个局部约束都满足时，八个成员才能形成有效的整体放置。

调度器要使用这棵树，控制面必须持续获得真实的网络拓扑。手工维护大量 HyperNode 对象很难适应设备和链路变化，因此需要自动发现。

## 16. HyperNode Auto-Discovery

> 建议用时：1 分 10 秒

不同数据中心的网络事实来自不同系统。NVLink 可以从 Fabric Manager 获取，InfiniBand 可以读取 OpenSM 或 UFM，RoCE 可以使用 LLDP、CDP 或交换网络数据；云环境还可能依赖 Cloud Provider API 和 DPU、SmartNIC telemetry。这些是自动发现框架可以接入的数据源，不代表当前版本已经全部内置。

当前代码内置 UFM 和 Node Label discoverer。Discoverer 把数据源相关的信息转成统一拓扑结果，Discovery Manager 负责汇聚，HyperNode Controller 再创建或更新 HyperNode 层级。调度器消费的是标准 HyperNode API，不需要直接集成每一种网络管理系统。

HyperNode Controller 独立部署以后，Controller 维护拓扑，Volcano 或其他调度器只消费 HyperNode。新的网络数据源和新的调度框架可以分别扩展，而不需要互相侵入代码。

## 17. Topology-Scoped Preemption

> 建议用时：1 分 20 秒

目标 Decode SubGroup 需要同一个 Leaf 内的四张 GPU。当前两个 Leaf 各有两张空闲卡，总数是四，但没有任何一个域可以直接容纳完整 SubGroup。

调度器需要先选择目标域，再围绕这个域扩展 victim。图中选中 Leaf B 后，reclaim 按完整 Job 释放该域内的资源，而不是在整个集群里随机找到四个 Pod。只有当目标 PodGroup、SubGroup 和 topology constraint 都能同时进入 pipeline，驱逐计划才允许提交。

Preemption 因而不只是“高优先级抢低优先级”。拓扑感知以后，它解决的是在哪个网络域内、通过最小且完整的 victim 集合，构造出真正可用的连续资源。

## 18. Kthena Serving Abstractions

> 建议用时：1 分 5 秒

传统 Deployment 只描述同构副本，难以直接表达一套完整的 PD 服务。Kthena 使用 ModelServing 管理模型版本、实例数量和发布策略；每个 ServingGroup 代表一套能够完成推理请求的服务实例；ServingGroup 内再划分 Prefill、Decode 等 Role，每个 Role 包含具体的 Entry 和 Worker Pod。

这些对象最终仍然要投影到 Kubernetes 和 Volcano。ServingGroup 对应完整的 Gang 调度边界，Role 和 Instance 提供更细的放置语义，Entry、Worker 最终成为 Pod。这样扩缩容、滚动升级和路由看到的是模型服务语义，调度器看到的是可以计算的成员与资源约束。

Kthena 0.3.0 起可以使用 PodGroup 的 `subGroupPolicy` 做多维拓扑调度，并把 Role 投影为对应策略。这要求 Volcano 版本和 CRD 已经提供 SubGroupPolicy；较旧环境只能使用 PodGroup 级约束。Kthena 统一维护 ServingGroup、Role 和 Pod 的对应关系，不需要每个推理框架自己拼装一组 Deployment。

## 19. Serving Scale-Out

> 建议用时：1 分 25 秒

Serving 扩容不是看到流量上升以后直接从训练任务抢四张卡。AutoscalingPolicy 根据流量、延迟和角色负载计算目标副本数并更新 ModelServing。角色级扩容会修改 ModelServing template 中 Prefill、Decode 的 replicas，并同步到已有 ServingGroup 的资源需求；只有 ModelServing 自身的 replicas 增加时，才会创建更多 ServingGroup。

队列系统再根据 deserved share 判断谁应该归还资源。图中低负载期间，Training Queue 借用了 Serving Queue 的四张 GPU；扩容发生后，Serving 的实际需求从二增加到六，Training 从十回到自己的 deserved 六，因此归还四张。

Volcano 选择完整的 training victim，并在满足 ServingGroup 的 Gang 和拓扑条件后完成放置。流量下降时，Serving 释放副本，训练或其他 Batch Job 可以再次借用空闲资源。资源借还由真实 workload demand 驱动，而不是长期为可能出现的推理峰值预留一块空闲 GPU 池。

## 20. Prefill–Decode Disaggregation

> 建议用时：1 分 25 秒

Prefill 和 Decode 的计算特征不同。Prefill 处理完整 prompt，计算密度高；Decode 逐 token 生成，更受显存容量、KV cache 和时延影响。拆分以后，两类角色可以使用不同的副本数和资源规格，例如一组 Prefill 对三组 Decode。

拆分不代表独立调度。ServingGroup 对应一个 PodGroup 边界；默认可以把全部 Role replica 纳入 Gang，也可以通过 `gangPolicy.minRoleReplicas` 设置各 Role 的最低准入数量。Role 内部的 Pod 仍然严格按 Gang 调度。`groupPolicy` 约束整个 PodGroup 的 HyperNode 范围，当前共享的 `rolePolicy` 会投影到每个 Role 对应的 SubGroupPolicy。

图中 Prefill 和 Decode 分别落到两个 Tier-1 HyperNode，是满足这些约束的一种示例结果，不代表当前 `rolePolicy` 会强制 P、D 分离。Prefill 生成的 KV cache 通过 LMCache、NIXL、Mooncake 等可插拔 connector 传给各 Decode replica，网络距离会直接影响端到端时延。

## 21. Kthena Intelligent Routing

> 建议用时：1 分 15 秒

实例启动以后，请求也不能简单 round-robin。相同 prompt prefix 如果已经在某个实例保留缓存，把请求路由过去可以减少重复 Prefill；LoRA 模型已经加载到某个实例时，保持 affinity 可以避免切换成本；队列长度、TTFT、TPOT 和 GPU KV cache 使用量则反映当前实例是否适合接收新请求。

Kthena 的 routing engine 把这些策略做成可插拔选择，并且在请求进入前执行 token 级流量控制。限流统计输入和输出 token，可以在本地或 Redis 中维护全局额度，也可以根据历史 token 用量实现用户公平性和加权流量切分。

在 PD disaggregation 场景中，Router 需要分别选择 Prefill 和 Decode group，再配合 KV connector 完成状态传递。Router 的选择会受到前面 GPU 共池、队列借还、Gang 和拓扑放置结果的约束。

## 22. Thank You

> 建议用时：15 秒

Volcano 负责把异构资源、队列、Gang 和网络拓扑组织成统一调度基础，Kthena 在这个基础上补充模型服务的生命周期和请求语义。

感谢大家，欢迎交流和提问。
