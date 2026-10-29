# Volcano KubeCon NA 2026：演讲草稿

**Volcano for the Agentic AI Era: Unified Scheduling Across Training, Inference, and Agents**

2026-10-29 更新。标题与摘要保持不变，正文 25 分钟，问答 5 分钟。对应 [PPT 草稿](Volcano_KubeCon_NA_2026_draft.pptx)。

## 四部分主线

1. **统一调度**：复用双路径与 NodeShard 材料，讲不同调度路径如何协调使用集群。
2. **多级 Gang 与网络拓扑**：从 PodGroup / SubGroup 的完整副本，讲到组内放置和组间分离。
3. **Ecosystem**：哪些社区已经采用、采用到什么程度，哪些集成还在扩展。
4. **Benchmark 框架与进展**：怎么测、已有基础、正在验证的结果，以及还需要继续做的测试。

连接这四部分的逻辑是：框架协调资源，工作负载表达需求，生态控制器传递这些需求，benchmark 验证调度表现。后续方向放在各部分结尾，不再单列一章 roadmap。

两个转场：

> 有了可用节点，还不等于工作负载能够运行。接下来要解决完整副本和拓扑放置。

> 接入的 workload 和 controller 越多，就越需要可重复的测试，弄清规模、延迟和调度开销如何变化。

## 逐页安排

| 页 | 内容 | 时间 | 素材 |
|---|---|---:|---|
| **第一章** | **统一调度** | **6:00** | |
| 1 | 原标题与讲者，交代四部分内容 | 0:30 | 封面 |
| 2 | Different Workloads, Shared Infrastructure：Agent 应用、推理与训练的基础设施需求 | 1:00 | 生命周期图精简 |
| 3 | A Coordinated Scheduling Framework：双路径，简述 worker / Binder | 1:30 | China 7–8 / EU 9 |
| 4 | NodeShard: Coordinating Node Access：节点候选范围如何协调 | 2:00 | China 9 / EU 10–11 |
| 5 | Available Nodes Are Only the Beginning：从资源范围转到工作负载需求 | 1:00 | 转场图 |
| **第二章** | **Multi-Level Gang + Network Topology** | **8:30** | |
| 6 | PodGroup / SubGroup：用 Kthena P/D 案例解释完整副本 | 2:30 | China 14、22 |
| 7 | HyperNode：拓扑域、层级与约束 | 2:00 | China 16 |
| 8 | Multi-Level Placement：实例位于较大域，副本位于较小域 | 2:00 | China 17 |
| 9 | PodGroup Anti-Affinity：组内聚拢、实例间分离；顺带讲 required / preferred | 2:00 | China 15，更新状态 |
| **第三章** | **Ecosystem** | **4:30** | |
| 10 | 能力表：Kthena、KubeRay、Grove 已有接入与推进中的部分 | 2:00 | 新增能力表 |
| 11 | KubeRay：两个完整的双 Pod 副本，不等于任意四个 Pods | 1:00 | 具体案例 |
| 12 | 扩展方向：standalone HyperNode 已交付；Kubeflow / LWS 深化；SubGroup 关系提案 | 1:30 | 合并原 roadmap 页 |
| **第四章** | **Benchmark Framework & Progress** | **6:00** | |
| 13 | 框架：环境 → workload profiles → audit / metrics → reports | 1:30 | 仓库 benchmark/ |
| 14 | 进展：已有场景与指标采集；仍在推进的测试和优化验证 | 1:30 | 已有能力 / 测试中两栏 |
| 15 | 一项代表性结果：配置、观察、结论边界与下一步复测 | 1:30 | 待选结果，当前留占位 |
| 16 | 回顾四部分，邀请贡献 workload profile、测试反馈和生态集成 | 1:30 | 收尾 |
| 17 | Q&A | 5:00 | |

## Benchmark 这一章怎么讲

仓库已有 Kind/KWOK 与已有集群入口、Gang / Pod 场景、拓扑配置、audit-exporter、Prometheus/Grafana 和报告收集。这些是框架进展，可以先讲清楚，不必等到所有性能测试完成。

结果页只选一个有上下文的例子：一条曲线、一项优化前后对比，或一个 profiling 发现。注明版本、环境、规模、指标口径和重复次数；尚未稳定的结果标为 **Under validation**。具体展示哪项结果仍待选定，草稿不填猜测数字。

KWOK 结果用于说明调度行为与开销，不证明真实 GPU 通信或模型吞吐。benchmark 也不必承担“证明双路径一定更快”的任务；可以坦诚讲已经测到了什么、接下来还在验证什么。

## 制作与准备

深蓝为正式内容，浅蓝为可编辑图示草稿，浅黄为中文制作备注；Proposed 表示未来能力，Under validation 表示结果还在核实。当前使用工作版式，来源与讲解边界放在讲者备注。

先把前三章的旧图与新增生态状态整理好，同时选定 benchmark 的代表性案例。只沿用正在推进的测试，不为凑一页结果另起大规模实验。最后留两次计时排练，核对版本和 PR 状态。

生态状态沿用 2026-10-28 的核查，演讲前再确认。详细来源见[研究记录](Volcano_KubeCon_NA_2026_group_topology_outline.zh-CN.md)；benchmark 依据见[框架文档](https://github.com/volcano-sh/volcano/blob/a3d50b503/benchmark/README.md)与[指标收集脚本](https://github.com/volcano-sh/volcano/blob/a3d50b503/benchmark/scripts/collect-report.sh)。
