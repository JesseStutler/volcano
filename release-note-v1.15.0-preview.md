# v1.15.0

## Summary

Volcano v1.15.0 further strengthens Volcano as a unified scheduling platform for converged general-purpose and AI computing at scale. As clusters increasingly run batch training, inference, AI Agent, HPC, big-data, and heterogeneous accelerator workloads together, the scheduler must make higher-quality decisions under resource contention while preserving workload-level semantics, queue fairness, topology locality, and operational stability.

The most important addition is **Gang-Aware Preemption and Resource Reclamation**. It makes eviction decisions gang-aware on both sides: the incoming gang is placed as a unit, and victim jobs are ordered and selected at job/gang granularity to avoid arbitrary partial disruption. v1.15.0 also introduces DRA queue quota in the capacity plugin, pluggable multi-sharding policies, benchmark and performance observability tooling, Kubernetes 1.35 support, NodeGroup preference ordering, Agent Scheduler stability improvements, incremental GPU/vGPU improvements, and opt-in scheduling gates for queue admission control.

## What's New

### Key Features Overview

- **Gang-Aware Preemption and Resource Reclamation (Alpha)**: Makes eviction decisions gang-aware on both sides. Volcano evaluates the preemptor as a whole gang and selects victims at job/gang granularity, reducing random partial disruption across training jobs and supporting HyperNode-scoped victim search when topology is enabled.
- **DRA Queue Quota in Capacity Plugin**: Adds queue quota accounting for Pods that request DRA resources, bringing `ResourceClaim` usage into the existing `capability`, `deserved`, and `guarantee` model.
- **Pluggable Multi-Sharding Policy Support (Alpha)**: Moves sharding configuration from fixed shard parameters to a pluggable policy framework with composable filter, score, and select phases, built-in `allocation-rate`, `warmup`, and `node-limit` policies, and ConfigMap live reload.
- **Volcano Benchmark and Performance Observability**: Provides a benchmark framework for one-click environment setup and performance report collection on Kind/KWOK or existing clusters, helping users establish baseline data and identify scheduler bottlenecks.
- **Scheduling Gates for Queue Admission (Alpha)**: Uses opt-in scheduling gates to hold pods blocked by queue capacity, so Cluster Autoscaler and Karpenter do not scale up for quota-only blockers.

### Key Feature Details

### Gang-Aware Preemption and Resource Reclamation (Alpha)

**Background and Motivation**:

Volcano's legacy `preempt` and `reclaim` actions are task-centric. For gang-style jobs, evicting individual tasks from many different victim jobs can create wide disruption without guaranteeing that the pending gang can be scheduled afterward. Some scheduling systems only make the preemptor gang-aware: they try to place the incoming gang as a unit, but still choose victims task by task. That can protect the incoming job while randomly breaking multiple victim gangs.

Volcano v1.15.0 makes both sides of the eviction decision gang-aware. Victim jobs are ordered and selected at job/gang granularity, so the scheduler can reason about the disruption cost of breaking a victim gang instead of treating every task as an interchangeable victim. This distinction is important even when HyperNode topology is not used, because the scheduler still avoids spreading arbitrary partial evictions across unrelated jobs.

This matters especially for training-style workloads. A task-by-task victim loop can evict one replica from many different jobs. If each job depends on gang semantics, one scheduling cycle may break every victim job while still failing to place the incoming gang. Volcano now groups candidate victim tasks by job and evaluates victim bundles. When bundle splitting is available, the scheduler treats resources above the gang requirement, such as `replicas - minAvailable`, as lower-cost safe bundles before considering whole-job disruption. Bundle ordering then follows the action policy first. `gangPreempt` is priority-driven, and `gangReclaim` is fairness-driven. Efficiency based on local gain inside the selected HyperNode versus global disruption is only used after those policy constraints are satisfied.

When HyperNode topology is configured, the new actions additionally scope victim search to HyperNode candidates. Volcano evaluates preemption and reclaim inside a selected topology scope rather than freely preempting across topology domains. The scheduler then runs plugin filtering and placement simulation before committing evictions and nominations, so eviction and placement are evaluated as one scheduling decision.

**Alpha Feature Notice**: Gang-aware preemption and reclamation is alpha and must be enabled explicitly through `gangPreempt` and `gangReclaim`. Future releases may merge these dedicated actions with the legacy `preempt` and `reclaim` actions after the rollout is validated.

**Key Capabilities**:

- **Preemptor-gang placement**: Evaluates whether the incoming gang can be placed as a whole before eviction is selected.
- **Victim-gang awareness**: Groups victim candidates by job/gang, prioritizes lower-cost victim bundles such as replicas above `minAvailable`, and avoids spreading partial disruption across many jobs.
- **Topology-scoped eviction**: When HyperNode topology is enabled, searches victims inside the selected topology scope instead of freely preempting across topology domains.
- **Policy-aware victim ordering**: Uses priority for `gangPreempt` and queue fairness for `gangReclaim`, with efficiency used as a secondary ordering signal.

**Configuration**:

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

**Note**: Do not configure `gangPreempt`/`gangReclaim` together with the legacy `preempt`/`reclaim` actions in the same scheduler action list.

Related:
- PRs: [#5250](https://github.com/volcano-sh/volcano/pull/5250), [#4780](https://github.com/volcano-sh/volcano/pull/4780), [#5170](https://github.com/volcano-sh/volcano/pull/5170)
- Design Docs: [Gang-Aware Eviction Design](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/gang-aware-eviction-design.md), [EvictableFn Evolution for Gang Eviction](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/evictablefn-evolution-for-gang-eviction.md)
- Contributors: [@vzhou-p](https://github.com/vzhou-p)

### DRA Queue Quota in Capacity Plugin

**Background and Motivation**:

Previous Volcano releases already supported scheduling Pods that request Kubernetes Dynamic Resource Allocation resources. The missing part was queue quota: DRA `ResourceClaim` requests were not accounted against `capability`, `deserved`, or `guarantee`, so queues could not control DRA resource usage the same way they control CPU, memory, and extended resources.

Kubernetes DRA introduces `DeviceClass`, `ResourceClaim`, `ResourceClaimTemplate`, and `ResourceSlice`, while Volcano queues already manage quota through `capability`, `deserved`, and `guarantee`. v1.15.0 brings DRA resources into that queue quota model instead of requiring a separate DRA-only quota API.

The capacity plugin now accounts DRA resource requests for queue enqueue and allocation decisions. Operators can limit whole devices or consumable device dimensions such as virtual GPU cores and memory. Shared ResourceClaims are deduplicated so multiple pods referencing the same logical claim do not inflate queue usage.

**Compatibility Note**: DRA quota requires Kubernetes DRA support and a DRA-capable driver. Some DRA allocation modes remain outside the first quota-accounting scope.

**Key Capabilities**:

- **Whole-device quota**: Controls DRA `DeviceClass` device counts at queue level.
- **Consumable-capacity quota**: Controls device dimensions such as cores or memory through queue quota.
- **Existing queue semantics**: Applies the same `capability`, `deserved`, and `guarantee` model used by other queue resources.
- **ResourceClaim-aware accounting**: Accounts direct claims, template-created claims, and shared claims without inflating queue usage.

**Configuration**:

```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: volcano-scheduler-configmap
  namespace: volcano-system
data:
  volcano-scheduler.conf: |
    actions: "enqueue, allocate, backfill, reclaim"
    tiers:
    - plugins:
      - name: priority
      - name: gang
      - name: conformance
    - plugins:
      - name: drf
      - name: predicates
      - name: capacity
        arguments:
          capacity.DynamicResourceAllocationEnable: true
          capacity.DRAConsumableCapacityEnable: true
      - name: nodeorder
```

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: ml-team
spec:
  reclaimable: true
  capability:
    cpu: "100"
    memory: "200Gi"
    "nvidia.com/gpu": "4"
    "deviceclass/gpu.nvidia.com": "8"
    "cores.deviceclass/hami-core-gpu.project-hami.io": "800"
    "memory.deviceclass/hami-core-gpu.project-hami.io": "320Gi"
```

Related:
- PRs: [#5058](https://github.com/volcano-sh/volcano/pull/5058)
- Design Doc: [DeviceClass Quota Support in Capacity Plugin](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/capacity-dra-support.md)
- User Guide: [DeviceClass Quota User Guide](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_dra_quota.md)
- Contributors: [@xu-wentao](https://github.com/xu-wentao)

### Pluggable Multi-Sharding Policy Support (Alpha)

**Background and Motivation**:

The v1.14.0 Sharding Controller introduced dynamic node scheduling shards for multi-scheduler deployments. v1.15.0 builds on that architecture by adding pluggable multi-sharding policy support. Instead of relying only on fixed scheduler-level shard parameters, operators can configure an ordered policy pipeline per scheduler shard.

The policy framework runs `filter`, `sort`, and `select` phases per scheduler. Built-in policies support allocation-rate filtering/scoring, warmup-node preference, and node count limiting. Policy configuration can be supplied through a ConfigMap and hot-reloaded at runtime. Invalid updates are rejected while the previous valid configuration remains active.

**Alpha Feature Notice**: The multi-sharding policy framework is still evolving. Future sharding policy extensions are expected to follow this pluggable multi-policy model. Existing top-level sharding fields remain supported for compatibility, while new configurations should use the policy-based format.

**Key Capabilities**:

- **Composable shard policies**: Supports filter, scorer, and selector policies in one ordered pipeline.
- **Built-in policy set**: Provides `allocation-rate`, `warmup`, and `node-limit` policies.
- **Per-scheduler shard profiles**: Allows Volcano and Agent Scheduler shards to use different policy chains and utilization ranges.
- **ConfigMap live reload**: Applies valid sharding policy updates without restarting the controller.

**Configuration**:

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
          - name: node-limit
            arguments:
              minNodes: 1
              maxNodes: 100
    shardSyncPeriod: "60s"
    enableNodeEventTrigger: true
```

Related:
- PRs: [#5098](https://github.com/volcano-sh/volcano/pull/5098), [#5132](https://github.com/volcano-sh/volcano/pull/5132), [#4990](https://github.com/volcano-sh/volcano/pull/4990)
- User Guide: [How to Configure Sharding via ConfigMap](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_configure_sharding_configmap.md)
- Contributors: [@lixmgl](https://github.com/lixmgl), [@agrawalcodes](https://github.com/agrawalcodes)

### Volcano Benchmark and Performance Observability

**Background and Motivation**:

Scheduler performance work needs more than ad hoc test scripts. Contributors and operators need a framework that can set up the environment, run standard workloads, collect performance data, and produce comparable reports with minimal manual steps.

v1.15.0 introduces a benchmark framework for one-click deployment and one-click performance output. It supports local Kind + KWOK environments as well as existing Kubernetes clusters, so contributors can reproduce scheduler performance cases locally and operators can evaluate Volcano in real cluster environments. The framework can deploy monitoring components, run gang and pod scheduling scenarios, collect reports, and help identify scheduling bottlenecks. It also gives new users a baseline for understanding Volcano's practical scheduling throughput and latency before production rollout.

**Key Capabilities**:

- **Local benchmark environment**: Runs repeatable benchmark scenarios with Kind and KWOK.
- **Existing-cluster benchmark mode**: Runs the same framework against bare-metal, cloud-managed, or self-hosted Kubernetes clusters.
- **Gang, pod, and topology scenarios**: Covers VolcanoJob gang scheduling, bare pod scheduling, KWOK topology labels, and HyperNode generation.
- **Metrics and reports**: Collects audit-exporter reports, pod timestamp fallback reports, test logs, and Grafana dashboards.
- **Scheduler performance metrics**: Expands scheduler/controller metrics for throughput and latency analysis.

**Quick Start**:

```bash
cd benchmark
make setup VOLCANO_VERSION=v1.15.0
make test-gang-env JOBS=10 REPLICAS=100 MIN_AVAILABLE=100
make cleanup-all
```

Related:
- PRs: [#5305](https://github.com/volcano-sh/volcano/pull/5305), [#5215](https://github.com/volcano-sh/volcano/pull/5215), [#5163](https://github.com/volcano-sh/volcano/pull/5163), [#5221](https://github.com/volcano-sh/volcano/pull/5221)
- User Guide: [Benchmark README](https://github.com/volcano-sh/volcano/blob/release-1.15/benchmark/README.md)
- Contributors: [@JesseStutler](https://github.com/JesseStutler), [@3th4novo](https://github.com/3th4novo)

### Scheduling Gates for Queue Admission (Alpha)

**Background and Motivation**:

Volcano can mark pods as `Unschedulable` when they are blocked by queue capacity rather than cluster capacity. Cluster Autoscaler and Karpenter commonly interpret `Unschedulable` pods as a signal to add nodes, which can cause unnecessary scale-ups when the actual blocker is queue admission.

Scheduling Gates for Queue Admission uses Kubernetes `schedulingGates` to hold opted-in pods until Volcano determines that the queue has capacity. While gated, pods are invisible to autoscaler scale-up logic. After the gate is removed, normal scheduling proceeds. If the pod still cannot fit any node, autoscalers receive a legitimate scale-up signal.

**Alpha Feature Notice**: Scheduling Gates for Queue Admission is disabled by default and must be enabled on both the scheduler and webhook-manager.

**Key Capabilities**:

- **Per-pod opt-in**: Uses the `scheduling.volcano.sh/queue-allocation-gate: "true"` annotation.
- **Autoscaler-friendly queue admission**: Keeps queue-blocked pods gated so autoscalers do not scale up for quota-only blockers.
- **Queue capacity protection**: Tracks ungated-but-not-yet-bound pods in the capacity plugin to avoid queue over-admission.
- **External gate coexistence**: Keeps the Volcano gate in place while other scheduling gates remain.

**Configuration**:

```bash
helm install volcano volcano/volcano --namespace volcano-system --create-namespace \
  --set custom.scheduler_feature_gates="SchedulingGatesQueueAdmission=true" \
  --set custom.admission_feature_gates="SchedulingGatesQueueAdmission=true"
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  annotations:
    scheduling.volcano.sh/queue-allocation-gate: "true"
spec:
  schedulerName: volcano
  containers:
  - name: worker
    image: nginx
    resources:
      requests:
        cpu: "1"
        memory: "1Gi"
```

Related:
- Issue: [#4710](https://github.com/volcano-sh/volcano/issues/4710)
- PRs: [#5033](https://github.com/volcano-sh/volcano/pull/5033), [#4727](https://github.com/volcano-sh/volcano/pull/4727)
- Design Doc: [Gate-Controlled Scheduling for Cluster Autoscalers Compatibility](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/design/scheduling-gates-queue-admission.md)
- User Guide: [How to Use Scheduling Gates for Queue Admission](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_scheduling_gates_queue_admission.md)
- Contributors: [@devzizu](https://github.com/devzizu)

## Other Notable Changes

### Features and Enhancements

- **Core scheduler stability and capacity correctness**: Improves transaction rollback, preemption/reclaim correctness, queue and inqueue accounting, victim ordering, event-handler synchronization, and scheduler cache safety. The Bug Fixes section lists the individual fixes. Together, they improve scheduler stability under high contention and concurrent event processing. ([#5073](https://github.com/volcano-sh/volcano/pull/5073), [#5180](https://github.com/volcano-sh/volcano/pull/5180), [#5010](https://github.com/volcano-sh/volcano/pull/5010), [#5011](https://github.com/volcano-sh/volcano/pull/5011), [#5067](https://github.com/volcano-sh/volcano/pull/5067), [#5141](https://github.com/volcano-sh/volcano/pull/5141), [#5142](https://github.com/volcano-sh/volcano/pull/5142), [#5113](https://github.com/volcano-sh/volcano/pull/5113), [#5100](https://github.com/volcano-sh/volcano/pull/5100), [#5130](https://github.com/volcano-sh/volcano/pull/5130), [#5176](https://github.com/volcano-sh/volcano/pull/5176), [#5091](https://github.com/volcano-sh/volcano/pull/5091), [#4973](https://github.com/volcano-sh/volcano/pull/4973), [#5172](https://github.com/volcano-sh/volcano/pull/5172), [#5178](https://github.com/volcano-sh/volcano/pull/5178), [#5086](https://github.com/volcano-sh/volcano/pull/5086), @hzxuzhonghu, @Sanchit2662, @Aman-Cool, @hajnalmt, @goyalpalak18, @guoqinwill, @qi-min, @zhifei92)
- **Agent Scheduler stability enhancements**: Fixes multi-worker optimistic concurrency conflicts, prevents a shared action instance from reusing different framework/cycle state, registers the missing CSI manager, improves binder node priority behavior when nodes are waiting to be checked, fixes inaccurate E2E duration metrics, and adds e2e coverage. ([#5154](https://github.com/volcano-sh/volcano/pull/5154), [#5153](https://github.com/volcano-sh/volcano/pull/5153), [#5221](https://github.com/volcano-sh/volcano/pull/5221), [#5163](https://github.com/volcano-sh/volcano/pull/5163), [#4991](https://github.com/volcano-sh/volcano/pull/4991), @JesseStutler, @qi-min, @agrawalcodes)
- **Kubernetes 1.35 support**: Updates Kubernetes dependencies, generated APIs, fake clients, informers, volumebinding integration, CI/lint tooling, Dockerfile Kubernetes version, and compatibility documentation for Kubernetes 1.35. ([#5000](https://github.com/volcano-sh/volcano/pull/5000), [#5039](https://github.com/volcano-sh/volcano/pull/5039), [#5062](https://github.com/volcano-sh/volcano/pull/5062), @guoqinwill, @hajnalmt)
- **NodeGroup preferred ordering for queues**: Adds `enablePreferredOrder` to the NodeGroup plugin so the order of `preferredDuringSchedulingIgnoredDuringExecution` in queue affinity is meaningful. Earlier nodegroups receive higher scores, allowing queues to prefer fixed resource pools before fallback pools. See the [Preferred Nodegroup Priority Ordering](https://github.com/volcano-sh/volcano/blob/release-1.15/docs/user-guide/how_to_use_nodegroup_plugin.md#preferred-nodegroup-priority-ordering) user guide section for configuration details. ([#5110](https://github.com/volcano-sh/volcano/pull/5110), @ruanwenjun)

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

- **Capacity ancestor reclaim level**: Adds `ancestorReclaimLevel` configuration and documents hierarchical queue reclaim behavior. ([#5115](https://github.com/volcano-sh/volcano/pull/5115), @hajnalmt)
- **GPU/vGPU incremental improvements**: Adds GPU exclusivity support to the deviceshare plugin, adds vGPU preemption support, and prevents pods in the same PodGroup from using the same physical vGPU device when disallowed. ([#5213](https://github.com/volcano-sh/volcano/pull/5213), [#5235](https://github.com/volcano-sh/volcano/pull/5235), [#5049](https://github.com/volcano-sh/volcano/pull/5049), @ckyuto, @archlitchi, @goyalankit)
- **Pod-level resource request and limit settings**: Supports pod-level resource request and limit configuration in Volcano Job pod templates. ([#5020](https://github.com/volcano-sh/volcano/pull/5020), @Tau721)
- **MPI validation and Argo MPI examples**: Relaxes MPI validation for single-master MPI jobs and adds Argo MPI workflow examples. ([#4956](https://github.com/volcano-sh/volcano/pull/4956), [#5117](https://github.com/volcano-sh/volcano/pull/5117), @kingeasternsun, @jrbe228)
- **DRA granular status authorization**: Adds ResourceClaim binding RBAC for granular DRA status authorization. ([#5151](https://github.com/volcano-sh/volcano/pull/5151), @praveen0raj)
- **DRA feature gate alignment**: Enables Volcano's DRA scheduling integration by default to align with Kubernetes 1.34+ DRA defaults. Operators can still disable it with `predicate.DynamicResourceAllocationEnable: false`. ([#5198](https://github.com/volcano-sh/volcano/pull/5198), @t2wang)

### Security Fixes Included

v1.15.0 includes the webhook request body size mitigation for [CVE-2026-44247](https://github.com/volcano-sh/volcano/security/advisories/GHSA-8wxp-xxp2-rcgx). This limits admission webhook request bodies and fixes a denial-of-service risk where an oversized request body could cause the webhook server to run out of memory.

### API Changes

New API, scheduler extension point, and user-facing configuration changes in v1.15.0:

**1. QueueAllocationGate annotation and scheduling gate (Alpha)** (@devzizu)

Adds `scheduling.volcano.sh/queue-allocation-gate` as the opt-in annotation and scheduling gate name for gate-controlled queue admission. The scheduler also adds `--gate-removal-worker-num` to control asynchronous gate-removal workers.

**2. Gang-aware eviction actions and scheduler extension points (Alpha)** (@vzhou-p)

Adds the scheduler actions `gangPreempt` and `gangReclaim`. Both actions support the `allowWholeBundle` argument to control whether whole-job victim bundles may be selected. The default is `true`. The scheduler framework also adds gang-aware eviction support through `UnifiedEvictableFn`, `EvictionContext`, and eviction kinds that allow plugins to distinguish task-level preempt/reclaim from gang-level preempt/reclaim. HyperNode gradient callbacks now take a `SearchPurpose` argument:

```go
type HyperNodeGradientForJobFn func(job *JobInfo, hyperNode *HyperNodeInfo, purpose SearchPurpose) [][]*HyperNodeInfo
type HyperNodeGradientForSubJobFn func(subJob *SubJobInfo, hyperNode *HyperNodeInfo, purpose SearchPurpose) [][]*HyperNodeInfo
```

`PurposeAllocate` and `PurposeEvict` let topology plugins return different search gradients for placement and eviction.

The `Preemptive` extension path is also candidate-list aware in v1.15.0:

```go
type ValidateWithCandidateFn func(interface{}, []*TaskInfo) bool
func (ssn *Session) Preemptive(queue *QueueInfo, candidates []*TaskInfo) bool
```

Plugins can now evaluate reclaim/preempt decisions against a batch of candidate tasks instead of a single task.

**3. DRA quota resource keys and capacity plugin arguments** (@xu-wentao)

Adds reserved key formats for DRA quota in Queue `capability`, `deserved`, and `guarantee`:

- `deviceclass/<DeviceClass>` for whole-device count quota
- `<dim>.deviceclass/<DeviceClass>` for consumable-capacity quota

Adds capacity plugin arguments:

- `capacity.DynamicResourceAllocationEnable`
- `capacity.DRAConsumableCapacityEnable`

**4. Capacity reclaim scope configuration** ([#5115](https://github.com/volcano-sh/volcano/pull/5115), @hajnalmt)

Adds the `ancestorReclaimLevel` capacity plugin argument to control how many ancestor levels are considered when hierarchical queues reclaim resources.

**5. Pod-level resource request and limit settings** ([#5020](https://github.com/volcano-sh/volcano/pull/5020), @Tau721)

Supports pod-level resource request and limit settings in Volcano Job pod templates.

**6. Pluggable sharding ConfigMap policy format (Alpha)** (@agrawalcodes, @lixmgl)

Adds ConfigMap-driven `schedulerConfigs`, `policies`, `shardSyncPeriod`, and `enableNodeEventTrigger` configuration for live-reloadable sharding policies.

**7. NodeGroup preferred-order scoring** ([#5110](https://github.com/volcano-sh/volcano/pull/5110), @ruanwenjun)

Adds the NodeGroup plugin argument `enablePreferredOrder`. When enabled, earlier entries in `preferredDuringSchedulingIgnoredDuringExecution` receive higher scores.

**8. GPU exclusivity rules** ([#5213](https://github.com/volcano-sh/volcano/pull/5213), @ckyuto)

Adds the deviceshare plugin argument `deviceshare.GPUExclusiveRules` for label-based exclusive physical GPU use on supported HAMi-core nodes.

**9. Scheduler and webhook flags**

Adds or exposes user-facing operational flags:

- Scheduler `--resource-sync-timeout` waits for initial resource handler synchronization before scheduling starts.
- Scheduler `--gate-removal-worker-num` controls scheduling-gate removal workers.
- Webhook-manager `--enable-queue-allocated-pods-check` rejects queue deletion when allocated pods still exist.
- Webhook-manager `--max-queue-depth` controls maximum hierarchical queue depth.
- Webhook-manager `--enable-root-queue-protection` protects root queue resource attributes.

**10. Helm chart values**

Adds per-component image tag overrides, `scheduler_percentage_nodes_to_find`, and sharding ConfigMap values:

- `custom.controller_image_tag_version`
- `custom.scheduler_image_tag_version`
- `custom.agent_scheduler_image_tag_version`
- `custom.admission_image_tag_version`
- `custom.agent_image_tag_version`
- `custom.scheduler_percentage_nodes_to_find`
- `custom.sharding_configmap_enable`
- `custom.sharding_configmap_data`

### Bug Fixes

- **Queue capability and root queue validation**: Sets root queue capability as infinity, adds validations for queue capability, adds queue deletion controls while pods are allocated, and enhances queue validation logic. ([#4973](https://github.com/volcano-sh/volcano/pull/4973), @guoqinwill)
- **DRF nil checks**: Adds nil checks in DRF plugin event handlers. ([#5014](https://github.com/volcano-sh/volcano/pull/5014), @goyalpalak18)
- **Preemptable/reclaimable nil checks**: Restores queue nil checks and adds nil checks in preemptable/reclaimable plugin functions. ([#4982](https://github.com/volcano-sh/volcano/pull/4982), @goyalpalak18)
- **PodGroup cache consistency**: Validates PodGroup before eviction to prevent cache inconsistency. ([#5002](https://github.com/volcano-sh/volcano/pull/5002), @Yashika0724)
- **AllocatedHyperNode recovery**: Fixes SubJob AllocatedHyperNode recovery after scheduler restart. ([#5008](https://github.com/volcano-sh/volcano/pull/5008), @ouyangshengjia)
- **Network QoS typo**: Fixes a typo in Network QoS handler. ([#5009](https://github.com/volcano-sh/volcano/pull/5009), @ouyangshengjia)
- **Preemption rollback**: Refactors preemption to use transactional statement semantics, adds unevict handling for failed cleanup, and prevents within-job preemption from committing evictions when the preemptor is not assigned. ([#5010](https://github.com/volcano-sh/volcano/pull/5010), [#5011](https://github.com/volcano-sh/volcano/pull/5011), @Aman-Cool)
- **Preempt action queue order and victim ordering**: Honors `QueueOrderFn`, scopes intra-job under-request processing by queue, and improves same-priority victim tie-break behavior. ([#5142](https://github.com/volcano-sh/volcano/pull/5142), [#5113](https://github.com/volcano-sh/volcano/pull/5113), @hajnalmt)
- **Subgroup scheduling without hard topology mode**: Fixes jobs with subgroups but without hard `networkTopology.mode` failing to schedule. ([#5038](https://github.com/volcano-sh/volcano/pull/5038), @JesseStutler)
- **Real capability guarded preemptive reclaim**: Guards preemptive reclaim by `realCapability`. ([#5053](https://github.com/volcano-sh/volcano/pull/5053), @FAUST-BENCHOU)
- **E2E failure context dump**: Fixes `DumpTestContextIfFailed` ordering so failure context is captured. ([#5054](https://github.com/volcano-sh/volcano/pull/5054), @katara-Jayprakash)
- **Duplicate session close**: Removes duplicated session close call. ([#5055](https://github.com/volcano-sh/volcano/pull/5055), @qi-min)
- **Reclaim spurious evictions**: Prevents committing evictions from nodes that the scheduler ends up not using. ([#5067](https://github.com/volcano-sh/volcano/pull/5067), @Aman-Cool)
- **Scheduler install panic**: Fixes panic and restart of scheduler pods during install, including concurrent root/default queue creation behavior. ([#5077](https://github.com/volcano-sh/volcano/pull/5077), @Tau721)
- **Snapshot shared mutable objects**: Fixes shared mutable objects in scheduler snapshot clones. ([#5086](https://github.com/volcano-sh/volcano/pull/5086), @zhifei92)
- **Capacity hierarchical nil panic**: Prevents nil panic in hierarchical queue mode. ([#5091](https://github.com/volcano-sh/volcano/pull/5091), @Aman-Cool)
- **Proportion inqueue double-counting**: Avoids double-counting inqueue resources for jobs with binding tasks. ([#5100](https://github.com/volcano-sh/volcano/pull/5100), @Aman-Cool)
- **Capacity inqueue double-counting**: Avoids double-counting inqueue resources for jobs with tasks in Binding state. ([#5130](https://github.com/volcano-sh/volcano/pull/5130), @Aman-Cool)
- **Multi-queue preemptor overwrite**: Prevents preemptorTasks overwrite in multi-queue preemption. ([#5141](https://github.com/volcano-sh/volcano/pull/5141), @hajnalmt)
- **Agent Scheduler DRA manager**: Registers the missing CSI manager in `vc-agent-scheduler`. ([#5153](https://github.com/volcano-sh/volcano/pull/5153), @JesseStutler)
- **Agent Scheduler multi-worker conflicts**: Fixes optimistic parallel scheduling concurrent conflict behavior. ([#5154](https://github.com/volcano-sh/volcano/pull/5154), @JesseStutler)
- **E2E duration metric**: Moves schedule start time to exclude queue wait time from E2E duration metric. ([#5163](https://github.com/volcano-sh/volcano/pull/5163))
- **Capacity missing parent scalar keys**: Avoids false exceeds when parent scalar resource keys are missing. ([#5176](https://github.com/volcano-sh/volcano/pull/5176), @hajnalmt)
- **Snapshot deepcopy rollback**: Rolls back unnecessary deepcopy in scheduler snapshot. ([#5177](https://github.com/volcano-sh/volcano/pull/5177), @zhifei92)
- **Concurrent map writes**: Fixes process panic caused by concurrent map writes. ([#5178](https://github.com/volcano-sh/volcano/pull/5178), @zhifei92)
- **Statement double-finalize**: Clears operations after `Discard()` and `Commit()` to prevent queue accounting corruption. ([#5180](https://github.com/volcano-sh/volcano/pull/5180), @Sanchit2662)
- **Event handler cache**: Records event handlers and waits for handlers before scheduling. ([#5172](https://github.com/volcano-sh/volcano/pull/5172), [#5184](https://github.com/volcano-sh/volcano/pull/5184), @qi-min)
- **Highest tier restrictions**: Fixes `highestTierName` in `partitionPolicy` or `subGroupPolicy` failing to restrict scheduling to specified HyperNode tiers. ([#5190](https://github.com/volcano-sh/volcano/pull/5190), [#5234](https://github.com/volcano-sh/volcano/pull/5234), @Tau721)
- **Network topology soft affinity placement**: Fixes suboptimal placement in soft affinity mode, where pods could be placed outside the best available HyperNode in some cluster states. The scheduler now converts soft topology constraints to the hard-mode scheduling path with the top HyperNode tier, and also fixes network-topology-aware scheduling for SubJobs. ([#5205](https://github.com/volcano-sh/volcano/issues/5205), [#5206](https://github.com/volcano-sh/volcano/pull/5206), @3th4novo)
- **Victim reprieve order**: Reverses potentialVictims order to reprieve higher-priority pods first. ([#5214](https://github.com/volcano-sh/volcano/pull/5214), @dengaosong)
- **cgroup unit test permission errors**: Fixes permission denied errors in cgroup handler unit tests. ([#5231](https://github.com/volcano-sh/volcano/pull/5231), @kube-gopher)
- **Admission webhook log level**: Adjusts the log level of Volcano admission webhook. ([#5245](https://github.com/volcano-sh/volcano/pull/5245), @0YHR0)
- **vGPU SchedulePolicy**: Makes deviceshare `SchedulePolicy` drive per-device pick. ([#5252](https://github.com/volcano-sh/volcano/pull/5252), @ckyuto)
- **vGPU cache double-counting**: Fixes HAMi core factory double-counting and stale PodMap handling. ([#5253](https://github.com/volcano-sh/volcano/pull/5253), @ckyuto)
- **Typed-nil devices clone**: Preserves typed-nil devices through `CloneOthers`. ([#5290](https://github.com/volcano-sh/volcano/pull/5290), @ckyuto)
- **Queue annotation patch operation**: Uses JSON Patch `add` instead of `replace` in `updateQueueAnnotation`. ([#5303](https://github.com/volcano-sh/volcano/pull/5303), @Aman-Cool)
- **Queue overused metric**: Computes queue overused metrics from final session share instead of per-task preemptive checks, so the metric reflects actual queue overuse. ([#5051](https://github.com/volcano-sh/volcano/pull/5051), @aadhil2k4)
- **Predicate plugin execution and allocation error handling**: Stabilizes predicate plugin execution order and rollback semantics, and sets `event.Err` when predicate allocation fails to prevent further node allocation. ([#5259](https://github.com/volcano-sh/volcano/pull/5259), [#5116](https://github.com/volcano-sh/volcano/pull/5116), @wangyang0616, @jiahuat)
- **MIG template matching**: Fixes incorrect MIG template matching when `gpuMemoryFactor` is greater than 1. ([#5318](https://github.com/volcano-sh/volcano/pull/5318), @DSFans2014)
- **Flaky preempt anti-affinity e2e**: Fixes flaky preempt anti-affinity e2e behavior. ([#5319](https://github.com/volcano-sh/volcano/pull/5319), @JesseStutler)
- **Scheduler comments and API comments**: Fixes typos in scheduler, Job, and CronJobSpec comments. ([#5237](https://github.com/volcano-sh/volcano/pull/5237), [#5328](https://github.com/volcano-sh/volcano/pull/5328), @FAUST-BENCHOU, @pmady)
- **ImageLocality scoring**: Restores `ImageStates` propagation in `GenerateNodeMapAndSlice` so the Kubernetes `ImageLocality` scoring plugin can prefer nodes that already have the required container images. ([#5343](https://github.com/volcano-sh/volcano/pull/5343), @kitianFresh)
- **Helm Chart API v2 and jobflow path**: Upgrades Helm `Chart.yaml` to API v2 and fixes jobflow path. ([#5301](https://github.com/volcano-sh/volcano/pull/5301), @madmecodes)
- **Website typo fixes**: Fixes typos and YAML syntax in website examples. ([#5024](https://github.com/volcano-sh/volcano/pull/5024), @aniketchawardol)

### Other

- **Helm and deployment refinements**: Adds per-component image tag overrides, `scheduler_percentage_nodes_to_find`, Helm chart API v2 updates, and jobflow path fixes. ([#5194](https://github.com/volcano-sh/volcano/pull/5194), [#5254](https://github.com/volcano-sh/volcano/pull/5254), [#5301](https://github.com/volcano-sh/volcano/pull/5301), @kingeasternsun, @madmecodes)
- **Scheduler metrics refinements**: Refactors scheduler/controller metrics and adds throughput output. ([#5215](https://github.com/volcano-sh/volcano/pull/5215), @JesseStutler)
- **SSH plugin custom port**: Allows custom SSH port configuration. ([#5047](https://github.com/volcano-sh/volcano/pull/5047), @aadhil2k4)
- **Logging behavior**: Honors `-stderrthreshold` when `-logtostderr` is enabled. ([#5134](https://github.com/volcano-sh/volcano/pull/5134), @pierluigilenoci)

### Dependencies

- **Kubernetes 1.35**: Updates Kubernetes dependencies and generated API clients for Kubernetes 1.35 support. ([#5000](https://github.com/volcano-sh/volcano/pull/5000), @guoqinwill)
- **OpenTelemetry**: Updates OpenTelemetry dependencies in the main module and staged APIs. ([#5088](https://github.com/volcano-sh/volcano/pull/5088), [#5169](https://github.com/volcano-sh/volcano/pull/5169), [#5241](https://github.com/volcano-sh/volcano/pull/5241), @dependabot)
- **moby/spdystream**: Bumps `github.com/moby/spdystream` from 0.5.0 to 0.5.1. ([#5220](https://github.com/volcano-sh/volcano/pull/5220), [@dependabot](https://github.com/dependabot))
- **Prometheus security update**: Updates `github.com/prometheus/prometheus` to address stored XSS advisory GHSA-vffh-x6r8-xx99. ([#5246](https://github.com/volcano-sh/volcano/pull/5246))

### Testing, CI, and Maintenance

- **Sharding Controller e2e**: Adds Sharding Controller setup, helpers, base e2e tests, and Volcano Scheduler Sharding e2e coverage. ([#4990](https://github.com/volcano-sh/volcano/pull/4990), [#4992](https://github.com/volcano-sh/volcano/pull/4992), @agrawalcodes)
- **Agent Scheduler e2e**: Adds Agent Scheduler e2e tests, CI workflow, and Helm plumbing. ([#4991](https://github.com/volcano-sh/volcano/pull/4991), @agrawalcodes)
- **DRA e2e**: Adds DRA quota e2e setup and tests. ([#5058](https://github.com/volcano-sh/volcano/pull/5058), @xu-wentao)
- **Gang eviction e2e**: Adds gang eviction e2e workflow and test coverage. ([#5250](https://github.com/volcano-sh/volcano/pull/5250), @vzhou-p)
- **Scheduling gates e2e**: Adds scheduling gates e2e workflow and tests. ([#5033](https://github.com/volcano-sh/volcano/pull/5033), @devzizu)
- **Reusable CI image workflow**: Optimizes CI image builds and adds skip-rebuild support. ([#5081](https://github.com/volcano-sh/volcano/pull/5081), @hajnalmt)
- **Ginkgo CLI pinning**: Pins the Ginkgo CLI version to the `go.mod` dependency. ([#5065](https://github.com/volcano-sh/volcano/pull/5065), @hajnalmt)
- **golangci-lint version check**: Improves golangci-lint version checking with an interactive upgrade prompt. ([#5061](https://github.com/volcano-sh/volcano/pull/5061), @hajnalmt)
- **Webhook-manager Dockerfile**: Updates `KUBE_VERSION` to 1.35.0. ([#5062](https://github.com/volcano-sh/volcano/pull/5062), @hajnalmt)
- **PR template guidance**: Adds AI guidance to the PR template. ([#5096](https://github.com/volcano-sh/volcano/pull/5096), @hwdef)
- **OWNERS update**: Adds `dafu-wu` to reviewers and approvers. ([#5121](https://github.com/volcano-sh/volcano/pull/5121), @dafu-wu)
- **Preempt function cleanup**: Reformats preempt function signatures. ([#5340](https://github.com/volcano-sh/volcano/pull/5340), @SquareCatFirst)
- **E2E queue cleanup**: Waits for queue deletion instead of forcing `Closed` state during e2e cleanup. ([#5350](https://github.com/volcano-sh/volcano/pull/5350), @FAUST-BENCHOU)
- **Cleanup return values**: Removes unnecessary error return values. ([#5043](https://github.com/volcano-sh/volcano/pull/5043), @hzxuzhonghu)

## Upgrade Instructions

To upgrade to Volcano v1.15.0 after the release is published:

```bash
# Using Helm
helm repo update
helm upgrade volcano volcano-sh/volcano --version 1.15.0

# Using kubectl
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/v1.15.0/installer/volcano-development.yaml
```

**Upgrade Notes**:

- Gang-aware preemption and reclamation is opt-in. Configure `gangPreempt` and `gangReclaim` explicitly, and do not use them together with legacy `preempt` and `reclaim` actions in the same scheduler action list.
- `SchedulingGatesQueueAdmission` is opt-in and must be enabled on both scheduler and webhook-manager.
- DRA queue quota requires Kubernetes DRA support and a DRA-capable driver.

## Contributors

Thank you to all contributors who made this release possible:

[@0YHR0](https://github.com/0YHR0), [@3th4novo](https://github.com/3th4novo), [@aadhil2k4](https://github.com/aadhil2k4), [@Aman-Cool](https://github.com/Aman-Cool), [@agrawalcodes](https://github.com/agrawalcodes), [@aniketchawardol](https://github.com/aniketchawardol), [@archlitchi](https://github.com/archlitchi), [@ckyuto](https://github.com/ckyuto), [@dafu-wu](https://github.com/dafu-wu), [@dengaosong](https://github.com/dengaosong), [@devzizu](https://github.com/devzizu), [@DSFans2014](https://github.com/DSFans2014), [@FAUST-BENCHOU](https://github.com/FAUST-BENCHOU), [@goyalankit](https://github.com/goyalankit), [@goyalpalak18](https://github.com/goyalpalak18), [@guoqinwill](https://github.com/guoqinwill), [@hajnalmt](https://github.com/hajnalmt), [@hwdef](https://github.com/hwdef), [@hzxuzhonghu](https://github.com/hzxuzhonghu), [@JesseStutler](https://github.com/JesseStutler), [@jiahuat](https://github.com/jiahuat), [@jrbe228](https://github.com/jrbe228), [@katara-Jayprakash](https://github.com/katara-Jayprakash), [@kingeasternsun](https://github.com/kingeasternsun), [@kitianFresh](https://github.com/kitianFresh), [@kube-gopher](https://github.com/kube-gopher), [@lixmgl](https://github.com/lixmgl), [@madmecodes](https://github.com/madmecodes), [@ouyangshengjia](https://github.com/ouyangshengjia), [@pierluigilenoci](https://github.com/pierluigilenoci), [@pmady](https://github.com/pmady), [@praveen0raj](https://github.com/praveen0raj), [@qi-min](https://github.com/qi-min), [@ruanwenjun](https://github.com/ruanwenjun), [@Sanchit2662](https://github.com/Sanchit2662), [@SquareCatFirst](https://github.com/SquareCatFirst), [@t2wang](https://github.com/t2wang), [@Tau721](https://github.com/Tau721), [@vzhou-p](https://github.com/vzhou-p), [@wangyang0616](https://github.com/wangyang0616), [@xu-wentao](https://github.com/xu-wentao), [@Yashika0724](https://github.com/Yashika0724), [@zhifei92](https://github.com/zhifei92)

## Full Changelog

[https://github.com/volcano-sh/volcano/compare/v1.14.0...v1.15.0](https://github.com/volcano-sh/volcano/compare/v1.14.0...v1.15.0)
