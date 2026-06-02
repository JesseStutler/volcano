# Volcano v1.15重磅发布！通智融合统一调度再升级

AI基础设施正在进入更复杂的混合部署阶段。一个Kubernetes集群里，可能同时运行大模型训练、推理服务、RL任务、AI Agent、HPC、大数据作业和在线业务。调度系统面对的资源也不再只有CPU、内存和GPU，还包括vGPU、DRA设备资源、网络拓扑资源以及不同资源池之间的协同调度。

在这样的集群里，调度器要解决的不只是“把Pod放到哪台节点上”。它还需要判断一个分布式任务能不能整体启动，抢占资源时会不会打散其他训练任务，队列quota是否覆盖了新的设备资源，多个调度器如何分工，性能瓶颈如何定位，以及queue quota和autoscaler之间如何避免误触发等。

v1.15.0沿着“通智融合”的统一调度平台方向继续演进。这个版本把重点放在资源竞争、异构设备、调度器扩展和性能可观测这几类更贴近生产集群的问题上，让Volcano在大规模批量计算、AI训练、推理和Agent workload混部场景下具备更稳定、更细粒度的调度能力。

## 版本亮点

本次发布主要围绕以下方向展开：

- **Gang-Aware Preemption and Resource Reclamation**：以Job/Gang为粒度组织被抢占候选，区分冗余副本与关键副本，优先驱逐冗余副本减少任务扰动，并在驱逐前模拟整体放置确认抢占方能成功启动，避免逐Pod抢占打断多个训练任务而抢占方自己也无法运行的情况。
- **DRA Queue Quota**：capacity插件将DRA `ResourceClaim`纳入Volcano现有的队列容量模型，让DRA设备资源也能通过队列配额管理。
- **Pluggable Multi-Sharding Policy**：Sharding Controller支持通过ConfigMap组合多种分片策略，并支持运行时热加载。
- **Volcano Benchmark框架**：提供一键化性能测试环境搭建和报告输出，支持Kind/KWOK及已有集群。
- **Scheduling Gates for Queue Admission**：区分"队列配额不足"和"集群资源不足"，避免autoscaler因队列限额触发不必要的扩容。

此外，v1.15.0还包含Kubernetes 1.35支持、NodeGroup preferred ordering、Agent Scheduler稳定性增强、GPU/vGPU增量增强以及安全修复。它们会在后文简要介绍，对生产可用性和生态兼容性同样重要。

## 重点特性

### 1. Gang-Aware Preemption and Resource Reclamation（Alpha）

在大模型训练、HPC等分布式任务中，一个Job往往需要多个Pod同时运行才有意义。如果抢占只按单个Pod进行决策，就可能从多个正在运行的训练任务里各抢一个Pod——表面上释放了资源，实际上既把多个任务都打断了，发起抢占的Gang也未必能凑齐`minAvailable`成功启动。

v1.15.0引入Gang-Aware Preemption and Resource Reclamation，让抢占方和被抢占方在决策时都以Gang为整体来考量，避免出现"释放了一堆Pod，但谁都没跑起来"的情况。

**在被抢占方一侧**，Volcano以Job/Gang为粒度组织被抢占候选，而不是把所有Pod看成可互换的抢占对象。每个候选Job的Pod被区分为冗余副本（超出`minAvailable`的部分）和关键副本，调度器优先选择冗余副本——驱逐它们不会打断任务——尽量避免触碰关键副本。这与原有action逐Pod选择、不区分破坏代价的方式有本质区别。

**在抢占方一侧**，调度器逐步累计可释放的资源，当累计量足以覆盖抢占方Gang的整体需求时，先做放置模拟——在释放后的资源视图上验证抢占方Gang能否整体调度成功——只有模拟通过才真正执行驱逐。这样不会出现"抢了一堆Pod结果抢占方还是起不来"的情况。

不论是否启用HyperNode拓扑，这套机制都能减少随机抢占带来的任务扰动。启用HyperNode拓扑后，Volcano还会将victim搜索限定在选定的拓扑范围内，避免跨拓扑域抢占。

该特性目前为Alpha，需要显式配置`gangPreempt`和`gangReclaim`两个新的action。后续版本会继续评估是否将Gang-Aware驱逐机制与原有`preempt`、`reclaim` action合并。

配置示例：

```yaml
actions: "enqueue, allocate, backfill, gangPreempt, gangReclaim"
tiers:
- plugins:
  - name: priority
  - name: gang
  - name: drf
  - name: predicates
  - name: nodeorder
  - name: binpack
```

相关资料：

- 相关PR：https://github.com/volcano-sh/volcano/pull/5250, https://github.com/volcano-sh/volcano/pull/4780, https://github.com/volcano-sh/volcano/pull/5170
- 设计文档：Gang-Aware Eviction Design: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/gang-aware-eviction-design.md
- 设计文档：EvictableFn Evolution for Gang Eviction: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/evictablefn-evolution-for-gang-eviction.md
- 感谢社区开发者：@vzhou-p

### 2. DRA Queue Quota

Kubernetes Dynamic Resource Allocation（DRA）为设备资源申请提供了更灵活的模型。此前版本的Volcano已经支持调度使用DRA资源的Pod，但队列quota尚未覆盖DRA `ResourceClaim`。

v1.15.0在capacity插件中补齐了这一能力，将DRA资源纳入Volcano已有的队列配额体系。用户仍然可以使用`capability`、`deserved`、`guarantee`容量模型管理队列资源，无需为DRA单独维护一套quota API。

目前支持两类资源管控：

- 基于`DeviceClass`的整卡/整设备数量配额
- 基于可消费设备维度的配额，如虚拟GPU core、显存等

当多个Pod引用同一个共享`ResourceClaim`时，Volcano会自动去重，避免同一份资源被重复计入队列用量。

这样，集群管理员可以用同一套队列容量模型统一管理CPU、内存、扩展资源以及DRA设备资源。

配置示例：

```yaml
tiers:
- plugins:
  - name: capacity
    arguments:
      capacity.DynamicResourceAllocationEnable: true
      capacity.DRAConsumableCapacityEnable: true
```

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: ml-team
spec:
  capability:
    cpu: "100"
    memory: "200Gi"
    "deviceclass/gpu.nvidia.com": "8"
    "cores.deviceclass/hami-core-gpu.project-hami.io": "800"
    "memory.deviceclass/hami-core-gpu.project-hami.io": "320Gi"
```

相关资料：

- 相关PR：https://github.com/volcano-sh/volcano/pull/5058
- 设计文档：DeviceClass Quota Support in Capacity Plugin: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/capacity-dra-support.md
- 使用文档：DeviceClass Quota User Guide: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_dra_quota.md
- 感谢社区开发者：@xu-wentao

### 3. Pluggable Multi-Sharding Policy（Alpha）

在多调度器架构下，不同调度器通常面向不同类型的工作负载，对候选节点的范围也有不同要求。v1.15.0对Sharding Controller进行了增强，支持以可插拔的策略流水线组合多种分片逻辑。

每个scheduler shard可以配置一组有序的策略，覆盖filter、score、select等阶段。内置策略包括：

- `allocation-rate`：根据节点资源利用率进行过滤和打分
- `warmup`：优先处理warmup节点
- `node-limit`：限制每个shard的节点数量范围

策略通过ConfigMap配置，支持运行时热加载。如果新配置校验失败，系统会沿用上一份有效配置，避免线上变更引入风险。

这让多调度器的节点分片能够更灵活地适配不同集群规模和业务类型，也为后续扩展更多sharding policy提供了清晰的接口。

配置示例：

```yaml
custom:
  sharding_configmap_enable: true
  sharding_configmap_data: |
    schedulerConfigs:
      - name: volcano
        type: volcano
        policies:
          - name: allocation-rate
            weight: 1
            arguments:
              minCPUUtil: 0.0
              maxCPUUtil: 0.6
          - name: node-limit
            arguments:
              minNodes: 1
              maxNodes: 100
      - name: agent-scheduler
        type: agent
        policies:
          - name: allocation-rate
            weight: 1
            arguments:
              minCPUUtil: 0.7
              maxCPUUtil: 1.0
          - name: warmup
            weight: 2
```

相关资料：

- 相关PR：https://github.com/volcano-sh/volcano/pull/5098, https://github.com/volcano-sh/volcano/pull/5132, https://github.com/volcano-sh/volcano/pull/4990
- 使用文档：How to Configure Sharding via ConfigMap: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_configure_sharding_configmap.md
- 感谢社区开发者：@lixmgl, @agrawalcodes

### 4. Volcano Benchmark框架

调度器的性能优化离不开稳定、可复现的测试基线。v1.15.0新增了Benchmark框架，支持一键部署测试环境、运行标准场景并输出性能报告。

该框架支持两类环境：

- 本地Kind + KWOK环境，用于开发者快速复现和分析调度性能问题
- 已有Kubernetes集群，用于用户在真实环境中评估Volcano的调度吞吐和延迟

测试场景覆盖VolcanoJob Gang调度、普通Pod调度、KWOK拓扑标签、HyperNode生成等，配合scheduler/controller metrics、audit-exporter报告和Grafana dashboard，可以帮助快速定位调度性能瓶颈。

对于新接触Volcano的用户，也可以借助该框架在自己的集群中运行一轮测试，快速了解实际的调度吞吐和延迟表现。

使用示例：

```bash
cd benchmark
make setup VOLCANO_VERSION=v1.15.0
make test-gang-env JOBS=10 REPLICAS=100 MIN_AVAILABLE=100
make cleanup-all
```

相关资料：

- 相关PR：https://github.com/volcano-sh/volcano/pull/5305, https://github.com/volcano-sh/volcano/pull/5215, https://github.com/volcano-sh/volcano/pull/5163, https://github.com/volcano-sh/volcano/pull/5221
- 使用文档：Benchmark README: https://github.com/volcano-sh/volcano/blob/release-1.15/benchmark/README.md
- 感谢社区开发者：@JesseStutler, @3th4novo

### 5. Scheduling Gates for Queue Admission（Alpha）

当Pod因为队列容量不足而无法调度时，Cluster Autoscaler或Karpenter可能将这些Pod误判为集群资源不足，从而触发不必要的扩容。

v1.15.0引入Scheduling Gates for Queue Admission。用户通过annotation为Pod开启后，当队列容量不足时，Volcano会通过Kubernetes原生的`schedulingGates`机制阻止Pod进入调度，使其对autoscaler不可见，从而不会触发扩容。等队列释放出容量后，Volcano再移除gate，Pod恢复正常调度流程。

这样可以有效区分"队列配额不足"和"集群资源不足"两种情况，避免因队列quota限制导致的无效扩容。

该特性目前为Alpha，需要同时在scheduler和webhook-manager中开启`SchedulingGatesQueueAdmission`。

配置示例：

```bash
helm install volcano volcano/volcano --namespace volcano-system --create-namespace \
  --set custom.scheduler_feature_gates="SchedulingGatesQueueAdmission=true" \
  --set custom.admission_feature_gates="SchedulingGatesQueueAdmission=true"
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: queue-gated-pod
  annotations:
    scheduling.volcano.sh/queue-allocation-gate: "true"
spec:
  schedulerName: volcano
  containers:
  - name: worker
    image: nginx
```

相关资料：

- 相关Issue：https://github.com/volcano-sh/volcano/issues/4710
- 相关PR：https://github.com/volcano-sh/volcano/pull/5033, https://github.com/volcano-sh/volcano/pull/4727
- 设计文档：Gate-Controlled Scheduling for Cluster Autoscalers Compatibility: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/scheduling-gates-queue-admission.md
- 使用文档：How to Use Scheduling Gates for Queue Admission: https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_scheduling_gates_queue_admission.md
- 感谢社区开发者：@devzizu

## 其他值得关注的增强

### Kubernetes 1.35支持

v1.15.0更新了Kubernetes依赖、生成代码、fake client、informer、volumebinding集成、CI/lint工具链以及兼容性文档，支持Kubernetes 1.35。

### NodeGroup preferred ordering

NodeGroup plugin新增`enablePreferredOrder`，Queue中`preferredDuringSchedulingIgnoredDuringExecution`的顺序会影响调度打分。靠前的NodeGroup会获得更高分数，适合“优先使用固定资源池，资源不足时再fallback到弹性资源池”的场景。

配置示例：

```yaml
tiers:
- plugins:
  - name: nodegroup
    arguments:
      enablePreferredOrder: true
```

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: bigdata
spec:
  affinity:
    nodeGroupAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - spark-fixed
      - spark-serverless
```

相关配置可参考：

https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_nodegroup_plugin.md#preferred-nodegroup-priority-ordering

### Agent Scheduler稳定性增强

v1.15.0修复了Agent Scheduler多worker乐观并发冲突、共享action实例复用framework/cycle state、CSI manager注册缺失、binder节点优先级处理以及E2E duration metric等问题，并补充了相关E2E覆盖。

这些修复主要提升了延迟敏感型AI Agent工作负载的调度稳定性。

### GPU/vGPU增量增强

v1.15.0对deviceshare plugin做了多项增强，包括GPU exclusive支持、vGPU preemption支持，以及在不允许共享时避免同一PodGroup内的Pod使用同一张物理vGPU设备。

### 安全修复

v1.15.0包含webhook request body size mitigation，用于修复CVE-2026-44247相关的拒绝服务风险。该修复限制admission webhook请求体大小，避免超大请求导致webhook server内存耗尽。

## 总结：Volcano v1.15.0 - 面向通智融合的统一调度平台

v1.15.0在统一调度平台方向上迈出了重要一步。Gang-Aware Preemption and Resource Reclamation让抢占决策不再局限于单个Pod，而是从Gang整体视角同时权衡抢占方能否整体启动与被抢占方的完整性。DRA Queue Quota将DRA设备资源纳入队列容量模型，使异构资源的管理方式与传统资源保持一致。Pluggable Multi-Sharding Policy、Benchmark框架和Agent Scheduler稳定性修复，则进一步提升了Volcano在大规模集群、多调度器协同和性能调优方面的工程能力。

面向AI训练、推理、RL、Agent、HPC和大数据混合部署场景，Volcano将继续完善通智融合统一调度平台。

## 升级注意事项

可以通过Helm或YAML方式升级到v1.15.0：

```bash
helm repo update
helm upgrade volcano volcano-sh/volcano --version 1.15.0
```

```bash
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/v1.15.0/installer/volcano-development.yaml
```

- Gang-Aware Preemption and Resource Reclamation为Alpha，需要显式配置`gangPreempt`和`gangReclaim`两个新的action。不要在同一个scheduler action list中同时配置新的`gangPreempt`/`gangReclaim`和旧的`preempt`/`reclaim`。
- Scheduling Gates for Queue Admission为Alpha，需要同时在scheduler和webhook-manager中开启。
- DRA scheduling integration默认开启，以对齐Kubernetes 1.34+的DRA默认行为。如需关闭，可设置`predicate.DynamicResourceAllocationEnable: false`。
- DRA Queue Quota依赖Kubernetes DRA支持和可用的DRA driver。

## 参考链接

本文重点介绍v1.15.0的主要能力。完整的API Changes、Bug Fixes、依赖更新、测试与维护项和贡献者列表，请参考正式Release Note及相关文档。

- Release Note: https://github.com/volcano-sh/volcano/releases/tag/v1.15.0
- Full Changelog: https://github.com/volcano-sh/volcano/compare/v1.14.0...v1.15.0

## 致谢

Volcano v1.15共有43位社区贡献者参与。衷心感谢每一位贡献者，是你们的努力让Volcano不断进步，成为更强大、更稳定的统一调度平台！

| | | |
|---|---|---|
| @0YHR0 | @3th4novo | @aadhil2k4 |
| @Aman-Cool | @agrawalcodes | @aniketchawardol |
| @archlitchi | @ckyuto | @dafu-wu |
| @dengaosong | @devzizu | @DSFans2014 |
| @FAUST-BENCHOU | @goyalankit | @goyalpalak18 |
| @guoqinwill | @hajnalmt | @hwdef |
| @hzxuzhonghu | @JesseStutler | @jiahuat |
| @jrbe228 | @katara-Jayprakash | @kingeasternsun |
| @kitianFresh | @kube-gopher | @lixmgl |
| @madmecodes | @ouyangshengjia | @pierluigilenoci |
| @pmady | @praveen0raj | @qi-min |
| @ruanwenjun | @Sanchit2662 | @SquareCatFirst |
| @t2wang | @Tau721 | @vzhou-p |
| @wangyang0616 | @xu-wentao | @Yashika0724 |
| @zhifei92 | | |
