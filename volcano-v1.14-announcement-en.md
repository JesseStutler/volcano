# Volcano v1.14 Released: Unified Scheduling Platform for Diverse Workloads at Scale

On January 2026, Volcano v1.14 was officially released. This update marks a significant milestone as Volcano evolves into a **unified scheduling platform** capable of handling diverse workloads—from batch AI training to latency-sensitive AI Agent applications—at massive scale.

## Release Highlights

The v1.14.0 release includes the following major updates:

**Unified Scheduling Platform Architecture**

* Scalable Multi-Scheduler with Dynamic Node Scheduling Shard (Alpha)
* Fast Scheduling for AI Agent Workloads (Alpha)

**Network Topology Aware Scheduling Enhancements**

* HyperNode-Level Binpacking
* SubGroup Level Topology Awareness
* Multi-Level Gang Scheduling across PodGroup and SubGroup Scopes
* Volcano Job Partitioning

**Colocation Enhancements**

* Support Generic Operating Systems (Ubuntu, CentOS, etc.)
* CPU Throttling for Dynamic Resource Isolation
* Memory QoS with Cgroup V2
* CPU Burst for Generic OS

**Heterogeneous Hardware Support**

* Ascend vNPU Scheduling with MindCluster and HAMi Modes

**Volcano Global Enhancements**

* HyperJob for Multi-Cluster Job Splitting
* Data Dependency Scheduling Framework

**Volcano Dashboard v0.2.0**

* PodGroup Dashboard Support
* Job and Queue Create/Delete Operations
* Security Hardening

## Scalable Multi-Scheduler with Dynamic Node Scheduling Shard (Alpha)

As Volcano evolves to support diverse scheduling workloads at massive scale, the single scheduler architecture faces significant challenges. Different workload types (batch training, AI agents, microservices) have distinct scheduling requirements and resource utilization patterns. A single scheduler becomes a bottleneck, and static resource allocation leads to inefficient cluster utilization.

The new Sharding Controller introduces a scalable multi-scheduler architecture that dynamically computes candidate node pools for each scheduler. Unlike strict partitioning, the Sharding Controller calculates dynamic candidate node pools rather than enforcing hard isolation between schedulers. This flexible approach enables Volcano to serve as a unified scheduling platform for diverse workloads while maintaining high throughput and low latency.

**Key Capabilities**:

* **Dynamic Node Scheduling Shard Strategies**: Compute dynamic candidate node pools based on various policies. Currently supports scheduling shard by CPU utilization, with an extensible design to support more policies in the future.
* **Node Pool Management**: Introduces NodeShard CRD to manage dynamic candidate node pools for specific schedulers.
* **Large-scale Cluster Support**: Architecture designed to support large-scale clusters by distributing load across multiple schedulers.
* **Scheduler Coordination**: Enable seamless coordination among various scheduler combinations (e.g., multiple Batch Schedulers, or a mix of Agent and Batch Schedulers).

Configuration example:

```bash
# Sharding Controller startup flags
--scheduler-configs="volcano:volcano:0.0:0.6:false:2:100,agent-scheduler:agent:0.7:1.0:true:2:100"
--shard-sync-period=60s
--enable-node-event-trigger=true

# Config format: name:type:min_util:max_util:prefer_warmup:min_nodes:max_nodes
```

Related PRs: https://github.com/volcano-sh/volcano/pull/4777

Design Doc: [Sharding Controller Design](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/design/sharding_controller.md)

Sincerely thanks to community developers: @ssfffss, @Haoran, @qi-min

## Fast Scheduling for AI Agent Workloads (Alpha)

AI Agent workloads are latency-sensitive with frequent task creation, requiring ultra-fast scheduling with high throughput. The Volcano batch scheduler is optimized for batch workloads and processes pods at fixed intervals, which cannot guarantee low latency for Agent workloads. To establish Volcano as a unified scheduling platform for both batch and latency-sensitive workloads, we introduce a dedicated Agent Scheduler.

The Agent Scheduler works in coordination with the Volcano batch scheduler through the Sharding Controller. This architecture positions Volcano as a unified scheduling platform capable of handling diverse workload types.

**Key Capabilities**:

* **Fast-Path Scheduling**: Independent scheduler optimized for latency-sensitive workloads such as AI Agent workloads
* **Multi-Worker Parallel Scheduling**: Multiple workers process pods concurrently from the scheduling queue, increasing throughput
* **Optimistic Concurrency Control**: Conflict-Aware Binder resolves scheduling conflicts before executing real binding
* **Optimized Scheduling Queue**: Enhanced queue mechanism with urgent retry support
* **Unified Platform Integration**: Seamless coordination with Volcano batch scheduler via Sharding Controller

Related PRs: https://github.com/volcano-sh/volcano/pull/4804, https://github.com/volcano-sh/volcano/pull/4801, https://github.com/volcano-sh/volcano/pull/4805

Design Doc: [Agent Scheduler Design](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/design/agent-scheduler.md)

Sincerely thanks to community developers: @qi-min, @JesseStutler, @handan-yxh

## Network Topology Aware Scheduling Enhancements

Volcano v1.14.0 brings significant enhancements to network topology aware scheduling, addressing the growing demands of distributed workloads including LLM training, HPC, and other network-intensive applications.

**Key Enhancements**:

* **SubGroup Level Topology Awareness**: Support fine-grained network topology constraints at the SubGroup/Partition level.
* **Flexible Network Tier Configuration**: Support `highestTierName` for specifying maximum network tier constraints by name.
* **Multi-Level Gang Scheduling**: Improved gang scheduling to support both PodGroup-level and SubGroup-level consistency.
* **Volcano Job Partitioning**: Enable partitioning of Volcano Jobs to better support parallel strategies (TP/PP/DP) and optimize network affinity.
* **HyperNode-Level Binpacking**: Resource packing at the HyperNode level (e.g., switches, racks) to reduce network fragmentation and improve communication efficiency.

Configuration Example - Volcano Job:

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: llm-training-job
spec:
  networkTopology:
    mode: hard
    highestTierAllowed: 2  # Job can cross up to Tier 2 HyperNodes
  tasks:
  - name: trainer
    replicas: 8
    partitionPolicy:
      totalPartitions: 2    # Split into 2 partitions
      partitionSize: 4      # 4 pods per partition
      minPartitions: 2      # Minimum 2 partitions required
      networkTopology:
        mode: hard
        highestTierAllowed: 1  # Each partition must stay within Tier 1
    template:
      spec:
        containers:
        - name: trainer
          image: training-image:v1
          resources:
            requests:
              nvidia.com/gpu: 8
```

Related PRs: https://github.com/volcano-sh/volcano/pull/4721, https://github.com/volcano-sh/volcano/pull/4810, https://github.com/volcano-sh/volcano/pull/4795, https://github.com/volcano-sh/volcano/pull/4785, https://github.com/volcano-sh/volcano/pull/4889

Design Doc: [Network Topology Aware Scheduling](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/design/Network%20Topology%20Aware%20Scheduling.md)

Sincerely thanks to community developers: @ouyangshengjia, @3sunny, @zhaoqi, @wangyang0616, @MondayCha, @Tau721

## Colocation for Generic OS

This release brings comprehensive improvements to Volcano's colocation capabilities, with a major milestone: **support for generic operating systems** (Ubuntu, CentOS, etc.) in addition to OpenEuler. This enables broader adoption of Volcano Agent for resource sharing between online and offline workloads.

### CPU Throttling (CPU Suppression)

The CPU usage of online pods dynamically changes. To better isolate online and offline workloads, the CPU quota allocated to offline pods needs to change dynamically according to the actual usage of online pods. When offline pods consume more CPU than their quota, CPU suppression is triggered; if not exceeded, their quota can gradually recover, enabling adaptive resource allocation.

Key design:
- Dynamically adjusts BestEffort root cgroup CPU quota based on node allocatable CPU and real-time usage
- Follows a "monitor-event-handler" architecture with conservative updates to avoid jitter

Configuration:

```yaml
cpuThrottlingConfig:
  enable: true
  cpuThrottlingThreshold: 80      # Allow BE quota up to 80% of allocatable CPU
  cpuJitterLimitPercent: 1        # Emit updates when quota changes by >=1%
  cpuRecoverLimitPercent: 10      # Cap quota increases to 10% per update
```

### Memory QoS (Cgroup V2)

Cgroup V2 based memory isolation for colocation environments. This feature introduces the `ColocationConfiguration` CRD, which allows users to define memory QoS policies for specific workloads.

Key capabilities:
- **New API**: `ColocationConfiguration` CRD for defining memory isolation policies via label selectors
- **Dynamic Calculation**: 
  - `memory.high` = `pod.limits.memory` * `highRatio` %
  - `memory.low` = `pod.requests.memory` * `lowRatio` %
  - `memory.min` = `pod.requests.memory` * `minRatio` %
- **Unified Interface**: Robust detection and support for Cgroup V2 environment

Usage Example:

```yaml
apiVersion: config.volcano.sh/v1alpha1
kind: ColocationConfiguration
metadata:
  name: colo-config1
spec:
  selector:
    matchLabels:
      app: offline-test
  memoryQos:
    highRatio: 100  # memory.high = memory.limits * 100%
    lowRatio: 50    # memory.low = memory.requests * 50%
    minRatio: 0     # memory.min = memory.requests * 0%
```

### CPU Burst and Cgroup V2 Full Support

Extended CPU Burst support to generic operating systems, and Volcano Agent now fully supports Cgroup V2 environments with automatic detection.

Related PRs: https://github.com/volcano-sh/volcano/pull/4632, https://github.com/volcano-sh/volcano/pull/4945, https://github.com/volcano-sh/volcano/pull/4913, https://github.com/volcano-sh/volcano/pull/4984

Design Docs: [CPU Throttle Design](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/design/cpu-throttle-design.md), [Agent Cgroup V2 Adaptation](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/design/agent-cgroup-v2-adaptation.md)

Sincerely thanks to community developers: @Haibara-Ai97, @JesseStutler, @ouyangshengjia

## Ascend vNPU Scheduling

Volcano v1.14.0 introduces integrated support for Ascend vNPU (virtual NPU) scheduling, enabling efficient sharing of Ascend AI processors across multiple workloads. This feature supports two modes to accommodate different deployment scenarios.

**Supported Modes**:

1. **MindCluster Mode**
   - Integrated from the Ascend MindCluster scheduling plugin: https://gitcode.com/Ascend/mind-cluster
   - Supports Ascend 310P series with dynamic virtualization

2. **HAMi Mode**
   - Developed by the HAMi community
   - Supports both Ascend 310 and 910 series
   - Supports heterogeneous Ascend clusters (910A, 910B2, 910B3, 310P)

Scheduler Configuration:

```yaml
# MindCluster Mode
- name: deviceshare
  arguments:
    deviceshare.AscendMindClusterVNPUEnable: true

# HAMi Mode
- name: deviceshare
  arguments:
    deviceshare.AscendHAMiVNPUEnable: true
    deviceshare.SchedulePolicy: binpack  # or spread
```

Related PRs: https://github.com/volcano-sh/volcano/pull/4656, https://github.com/volcano-sh/volcano/pull/4717

User Guide: [How to Use vNPU](https://github.com/volcano-sh/volcano/blob/v1.14.0/docs/user-guide/how_to_use_vnpu.md)

Sincerely thanks to community developers: @JackyTYang, @DSFans2014

## Volcano Global Enhancements

Volcano Global v0.3.0 introduces two major features that significantly expand Volcano Global's capabilities for AI/ML and Big Data workloads by enabling intelligent scheduling based on both compute resources and data locality.

### HyperJob for Multi-Cluster Job Splitting

As AI training workloads grow in scale and complexity, organizations increasingly face the challenge of managing large-scale training jobs across multiple heterogeneous clusters. HyperJob is a higher-level abstraction built on top of Volcano Job. It composes multiple Volcano Job templates and extends training capabilities beyond single cluster boundaries, while preserving the full capabilities of existing Volcano Jobs within each cluster.

**Key Capabilities**:

* **Karmada Integration**: Generates PropagationPolicies with proper cluster affinity and replica scheduling settings
* **Status Aggregation**: Aggregates status from all child VCJobs into a unified HyperJob status
* **Automatic Resource Generation**: Creates VCJobs and PropagationPolicies for each ReplicatedJob definition

Example HyperJob resource (Large-scale Training Job Splitting across 2 clusters with 256 GPUs total):

```yaml
apiVersion: training.volcano.sh/v1alpha1
kind: HyperJob
metadata:
  name: llm-training
spec:
  replicatedJobs:
  - name: trainer
    replicas: 2
    templateSpec:
      tasks:
      - name: worker
        replicas: 128
        template:
          spec:
            containers:
            - name: trainer
              image: training-image:v1
              resources:
                requests:
                  nvidia.com/gpu: 1
```

### Data Dependency Scheduling

In High-Performance Computing scenarios such as AI training and Big Data analysis, task execution depends heavily on data resources, not just compute resources. In multi-cluster environments, the scheduler might dispatch tasks to clusters physically distant from their data sources, resulting in prohibitive cross-region bandwidth costs and high I/O latency.

The Data Dependency Scheduling framework introduces a dedicated DataDependencyController that bridges the gap between logical data requirements and physical cluster placement. By utilizing external dependency detection plugins (such as Amoro), the controller queries real-time physical data distribution and translates this information into scheduling constraints. This achieves a fully automated "Compute-to-Data" (Data Gravity) workflow without manual intervention.

**Key Capabilities**:

* **Plugin Architecture**: Extensible framework supporting multiple data systems (Amoro, Hive, S3)
* **DataSourceClaim/DataSource CRDs**: Declarative API for data dependency management with a "Declaration - Cache" pattern
* **Automatic Affinity Injection**: Injects ClusterAffinity constraints into Karmada ResourceBindings

For detailed information, please refer to the [Volcano Global v0.3.0 Release Notes](https://github.com/volcano-sh/volcano-global/releases/tag/v0.3.0).

Sincerely thanks to community developers: @JesseStutler, @fx147, @Monokaix, @zhoujinyu, @anryko, @tanberBro

## Volcano Dashboard v0.2.0

Volcano Dashboard v0.2.0 brings significant enhancements to resource management capabilities, making it easier to manage Volcano resources through a web interface.

**Key Enhancements**:

* **PodGroup Dashboard Support**: View all PodGroups across namespaces, search and filter by name, namespace, and status, inspect detailed YAML configuration with syntax highlighting
* **Job Create and Delete Operations**: Create new Volcano Jobs and delete existing ones directly from the dashboard interface
* **Queue Management Enhancements**: Delete and update Queue configurations (resource quotas, weights, etc.), edit Queue YAML directly in the dashboard
* **Security Hardening**: SELinux options configured, Seccomp profile set to RuntimeDefault, containers run as non-root user, privilege escalation disabled

For detailed information, please refer to the [Volcano Dashboard v0.2.0 Release Notes](https://github.com/volcano-sh/dashboard/releases/tag/v0.2.0).

Sincerely thanks to community developers: @vzhou-p, @Shrutim1505, @JesseStutler, @karanBRAVO, @Sayan4444, @jayesh9747, @Alivestars24, @kuldeep, @Monokaix

## Scheduler Stability and Performance

**Reclaim Refactoring and Enhancements**

The Reclaim mechanism has been significantly improved through a comprehensive refactor of the Reclaim Action and critical logic fixes in the Capacity Plugin. These changes collectively enhance the accuracy, stability, and performance of resource reclamation in multi-tenant clusters.

Key improvements:
- **Reclaim Action Refactoring**: The reclaim workflow has been restructured to improve code readability, maintainability, and test coverage.
- **Enhanced Capacity Plugin Logic**: Fixed `reclaimableFn` and `preemptiveFn` to correctly handle scalar resources and prevent incorrect preemption decisions.
- **Improved Stability**: Addressed edge cases in resource calculation to prevent scheduling loops and incorrect evictions.

Related PRs: https://github.com/volcano-sh/volcano/pull/4794, https://github.com/volcano-sh/volcano/pull/4659, https://github.com/volcano-sh/volcano/pull/4919

Sincerely thanks to community developers: @guoqinwill, @hajnalmt

## Kubernetes 1.34 Support

Volcano stays current with Kubernetes releases. Version 1.14 supports the latest Kubernetes v1.34 and ensures functionality and reliability through comprehensive unit and end-to-end (E2E) tests.

Related PR: https://github.com/volcano-sh/volcano/pull/4704

Sincerely thanks to community developers: @suyiiyii, @tunedev

## **Conclusion: Volcano v1.14.0 — A Unified Scheduling Platform for the AI Era**

Volcano v1.14.0 marks a significant evolution in cloud-native batch computing. With the introduction of the multi-scheduler architecture and Agent Scheduler, Volcano now serves as a unified scheduling platform capable of handling both batch AI training and latency-sensitive AI Agent workloads. The enhanced network topology awareness, generic OS colocation support, and Ascend vNPU integration further solidify Volcano's position as the go-to solution for AI infrastructure.

Meanwhile, Volcano Global v0.3.0 expands multi-cluster capabilities with HyperJob for large-scale distributed training and data-aware scheduling. Volcano Dashboard v0.2.0 significantly improves the user experience with comprehensive resource management features.

**Experience Volcano v1.14.0 now and embrace the unified scheduling platform for the AI era!**

**v1.14.0 release:** https://github.com/volcano-sh/volcano/releases/tag/v1.14.0

**Volcano Global v0.3.0 release:** https://github.com/volcano-sh/volcano-global/releases/tag/v0.3.0

**Volcano Dashboard v0.2.0 release:** https://github.com/volcano-sh/dashboard/releases/tag/v0.2.0

## **Acknowledgments**

Volcano v1.14.0 ecosystem release (including Volcano Global v0.3.0 and Dashboard v0.2.0) includes contributions from 55 community members. Sincerely thanks to all contributors:

| | | |
| --- | --- | --- |
| @3sunny | @3th4novo | @acsoto |
| @Alivestars24 | @Aman-Cool | @anryko |
| @archlitchi | @dafu-wu | @DSFans2014 |
| @FAUST-BENCHOU | @fengruotj | @Freshwlnd |
| @fx147 | @goyalpalak18 | @guoqinwill |
| @Haibara-Ai97 | @hajnalmt | @halcyon-r |
| @handan-yxh | @JackyTYang | @jayesh9747 |
| @JesseStutler | @jiahuat | @karanBRAVO |
| @kingeasternsun | @kiritoxkiriko | @kube-gopher |
| @kuldeep | @LiZhenCheng9527 | @medyagh |
| @MondayCha | @Monokaix | @mvinchoo |
| @neeraj542 | @nitindhiman314e | @ouyangshengjia |
| @PersistentJZH | @qi-min | @rhh777 |
| @ruanwenjun | @RushabhMehta2005 | @sailorvii |
| @Sayan4444 | @Shrutim1505 | @ssfffss |
| @suyiiyii | @tanberBro | @Tau721 |
| @vzhou-p | @wangyang0616 | @weapons97 |
| @Wonki4 | @zhaoqi612 | @zhengchenyu |
| @zhoujinyu | @zjj2wry | |
