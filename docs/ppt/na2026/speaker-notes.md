# Speaker notes

Short English prompts for the current 26-slide presentation.

## 01. Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents

Today we will look at how Volcano supports different AI workloads on shared Kubernetes clusters. We will move from scheduling paths to group placement, then show how ecosystem integrations and benchmarks bring these ideas into practice.

## 02. Speakers

Briefly introduce yourselves and your work in cloud native infrastructure. Connect that experience to the challenges of scheduling training, inference, and emerging agent workloads.

## 03. Unified scheduling

Different workloads have different scheduling needs. Start with how Volcano coordinates those needs across a shared cluster.

## 04. Different Workloads, Shared Infrastructure

Training and inference both need complete groups and good network locality. Training groups follow parallelism patterns such as TP and PP, while inference groups follow roles and replicas. Agent workloads add bursts and startup latency concerns. A runtime controller can reuse warm capacity, then request more Pods through a fast scheduling path when the pool needs to grow.

## 05. Unified Scheduling Framework

Different workloads can use different scheduling paths, while sharing the same cluster. The Sharding Controller uses node metrics and scheduling strategies to adjust the node pools. NodeShard carries the desired allocation, and the schedulers coordinate changes with the nodes already in use. This gives each path room to adapt as workload demands change.

## 06. Dynamic Node Sharding

The controller combines node state with a sharding strategy to calculate the desired allocation. For example, it can filter nodes by CPU allocation, prefer nodes labeled for warmup, and cap how many nodes a scheduler receives. CPU allocation here comes from Pod resource requests, rather than measured CPU usage.

In the YAML, nodesDesired is the target set and nodesInUse is the current set. Their difference identifies nodes to add or release. The scheduler coordinates these changes as candidate pools evolve.

## 07. Multi-level gang & network topology

Having available nodes is only part of the problem. We also need to keep workload groups complete and place them within suitable network domains.

## 08. Training and Inference Groups

A training job can contain several pipeline stages, with tensor-parallel ranks inside each stage. A serving instance can contain Prefill and Decode roles, each with its own replicas. These structures create requirements at more than one level. We need to admit the overall workload while preserving complete compute groups inside it.

## 09. Multi-Level Gang Scheduling

PodGroup expresses admission requirements for the whole job or serving group. SubGroup preserves smaller units, such as a TP group or a role replica. One policy can use replica labels to identify multiple SubGroups. The network hierarchy below provides the domains where those complete groups can be placed.

## 10. HyperNode: Network Topology

HyperNode turns the physical network hierarchy into scheduling domains. A parent HyperNode groups other HyperNodes, while a leaf HyperNode groups Kubernetes nodes. Named tiers such as spine and leaf let workloads express locality requirements. This gives the scheduler a common view of the network at several levels.

## 11. Place Groups at Different Topology Levels

This is one placement example, not a fixed layout for Prefill and Decode. The PodGroup uses the core tier, while its SubGroups request different topology domains. Each level can have its own network topology constraints.

For example, one SubGroup may need tight communication within a leaf, while another can span a spine. The actual choices depend on communication patterns and cluster topology. The role names do not dictate where they must run.

## 12. Gang-Aware Preemption

Each training gang needs both of its Pods and stays inside one HyperNode. Taking one Pod from each of A, B, C and D interrupts four training jobs and can lose work since their last checkpoint.

Within HyperNode West, consider victim gangs in priority order. A and B together release four slots. Simulate the complete incoming gang, including its topology constraints. Commit only a feasible plan. A failed trial causes no eviction.

These training jobs have no surplus Pods, so this example uses whole-gang victims. C, D and the jobs in HyperNode East keep running.

## 13. PodGroup Anti-Affinity

Each serving instance remains a complete PodGroup within its chosen domain. PodGroup anti-affinity places matching instances in separate supernodes, reducing their exposure to the same domain failure. The scheduler provides placement separation. Application health checks and routing still handle service recovery.

## 14. SubGroup Affinity and Anti-Affinity

The next step is to express relationships between SubGroups inside one PodGroup. Prefill and Decode groups may benefit from staying in the same supernode, while Decode replicas should use separate leaf domains. These affinity and anti-affinity rules are planned work. They would combine communication locality with replica isolation.

## 15. Ecosystem

Workload controllers know the roles, replicas, and minimum group sizes. The next examples show how they pass that structure to Volcano.

## 16. Kthena: Group and Role Topology

Kthena lets users describe scheduling intent in ModelServing. The groupPolicy applies to the whole ServingGroup, while rolePolicy applies to its role replicas. Here, the whole group stays within a spine domain and each role replica stays within a leaf. The next slide shows how these settings become Volcano PodGroup fields.

## 17. Kthena: Role Replica Mapping

Start with the three count rules below the YAML. Blue marks the minimum number of groups, green marks Pods per group, and purple marks the total. For Kthena, minRoleReplicas sets minSubGroups. workerReplicas excludes the Entry Pod, so add one Entry to each worker count. Here, one Prefill group and three Decode groups each need two Pods, giving eight.

There are two role policies but four SubGroups. The example sets desired replicas equal to these gang minimums. Role identity labels distinguish the three Decode replicas. The groupPolicy and rolePolicy from the previous slide also carry into the generated PodGroup. The excerpts here focus on counts, while the companion YAML retains selectors and topology fields.

## 18. KubeRay: Multi-Host Replica Mapping

The Head is a separate one-Pod SubGroup. It is not included in workerGroupSpecs. With autoscaling enabled, minReplicas gives the worker SubGroup count, while numOfHosts gives Pods per worker SubGroup. The total is one Head plus two times two worker Pods. The right diagram shows three SubGroups: one for the head and one for each worker replica. That gives five minimum Pods.

The replica label keeps each pair of hosts together. Replica grouping must be enabled. The YAML now includes both the head and worker policies. The companion example includes the replica-name selector. Worker-group topology support is still in progress.

## 19. Grove: PodGang Mapping

Each named Grove group becomes one SubGroup. Here, minReplicas sets Pods per SubGroup, not the number of SubGroups. Prefill needs two Pods and Decode needs four. The same names and counts appear inside the Volcano PodGroup. Each group creates one SubGroup policy, giving two SubGroups and six minimum Pods.

The backend uses grove.io/podclique labels to select group members. The companion YAML includes those selectors. This mapping preserves gang structure, but this backend does not yet support topologyConstraint.

## 20. Ecosystem Roadmap

RBG integration is in progress at both the PodGroup and SubGroup levels. HyperNode tree query support is another part of that work, giving the controller access to the topology hierarchy.

For Kubeflow, the planned work extends group structure and topology support. For LWS, it includes coordination across roles and multiple groups. These are ongoing and planned integrations, not a claim that every capability is already available.

## 21. Benchmark framework & progress

More workload shapes and placement rules also mean more behavior to validate. We need repeatable tests that help us compare schedulers and understand where each approach works well.

## 22. Scheduling Benchmark Framework

The framework generates workloads and records what happens through the API and scheduler. Audit events and Prometheus provide measurements for reports, including scheduling latency and binding throughput. Tests can use Kind with KWOK or an existing cluster. These measurements describe scheduling behavior, while GPU execution performance needs separate testing.

## 23. Cross-Scheduler Benchmarks

This page shows how we plan to compare schedulers. Keep the workload definition, arrivals, and resource requests fixed. Run one scheduler at a time, reset cluster state, and replay the same inputs for the next scheduler. Repeat runs and retain versions, configuration, and measurements.

Check that compared schedulers support equivalent scheduling semantics, especially for gangs and topology. This is an experiment design, not a performance result. The next slide covers which workload and topology scenarios to test.

## 24. Workload and Topology Test Matrix

The test matrix should cover several kinds of pressure. Bursts test tail latency and backlog recovery, while larger gangs expose resource fragmentation. Topology cases check whether complete groups land in valid domains. The goal is to find the scenarios each scheduler handles well and understand the tradeoffs.

## 25. v1.17 Roadmap

These are roadmap directions selected for this talk, not an official priority ranking. Resource defragmentation would relocate workloads at PodGroup granularity to consolidate GPU capacity. HyperNode work includes a kube-scheduler extender and SubGroup affinity and anti-affinity.

Accelerator work covers generic xPU topology, DRA binpack, and ResourceClaim preemption and reclaim. DRA-backed extended resources let workloads keep familiar resource requests; continue validating that integration rather than presenting the upstream feature as new. DRANET adds network-device allocation and GPU/NIC locality. Ecosystem work extends group and topology support in Kubeflow, KubeRay, and LWS. The roadmap also tracks gang preemption and reclaim, tenant queue fairness, and performance improvements backed by benchmarks.

## 26. Volcano Users

These logos represent Volcano users and platforms that use or provide Volcano. Their usage and integration models differ. Thank them for their feedback and contributions, and invite the audience to share workload examples or integration needs.

The QR codes open the Volcano website, GitHub repository, and the Volcano channel in CNCF Slack. Slack requires workspace access. Open the floor for questions.
