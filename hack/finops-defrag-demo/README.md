# FinOps 资源碎片整理 Demo：Descheduler + Volcano Binpack

本文用于录制一个完整 Demo：集群运行一段时间后，低负载训练任务散落在多个节点上，形成资源碎片；通过 descheduler 的高利用率整理策略驱逐低利用率节点上的 Pod，再由 Volcano binpack 重新调度，把工作负载压实到目标节点，实现资源整合。

## 演示目标

初始状态：

- A/B 节点上各有一些低负载训练 Pod，资源请求较低。
- C 节点上已有一部分训练负载，资源利用率高于整理阈值。
- Volcano scheduler 已启用 binpack。
- 每个节点都可能存在系统组件、监控组件或其他基础负载，因此判断是否低利用率时以现场实际 requests 为准。

触发整理：

- descheduler 使用 `HighNodeUtilization` 策略识别低利用率节点。
- descheduler 驱逐 A/B 上可迁移的低负载 Pod。
- Deployment 重新拉起 Pod。
- 新 Pod 使用 `schedulerName: volcano`，由 Volcano binpack 调度到 C。

最终状态：

- A/B 节点上 demo 业务 Pod 被清空或显著减少。
- C 节点承载 anchor 负载和迁移后的低负载 Pod。
- 体现 FinOps 场景下的节点压实和碎片整理效果。

## 演示口径

可以这样描述初始状态：

> 这里模拟训练任务运行一段时间后的状态。训练任务结束、缩容或局部空闲后，部分 Pod 仍散落在多个节点上，每个节点都占一点资源，导致后续大规格任务无法连续获得资源，也不利于节点缩容。调度器已经开启 binpack，但 binpack 只影响新 Pod 的放置，不能主动移动已经运行的 Pod。因此需要 descheduler 先触发安全驱逐，再由 Volcano binpack 对重建 Pod 进行资源整合。

## 文件说明

```text
hack/finops-defrag-demo/
  env.sh                         # 参数入口：context、节点名、镜像、阈值
  01-prepare-initial-state.sh    # 构造初始碎片状态
  02-run-descheduler.sh          # 触发一次 descheduler 整理
  03-verify.sh                   # 验证 Pod 迁移和节点资源分布
  04-cleanup.sh                  # 清理 demo 资源，必要时恢复 scheduler 配置
```

## 执行前准备

1. 确认 kubectl 已连接到目标集群。

```bash
kubectl config current-context
kubectl get nodes -o wide
```

2. 选择三个 worker 节点，分别作为 A/B/C。

建议选择规格一致或接近的节点。C 节点用于资源整合目标节点，A/B 节点模拟碎片节点。节点上可以有基础负载，不要求像本地测试集群一样干净。

3. 记录节点当前 requests。

```bash
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

重点看 `Allocated resources` 中 CPU/Memory Requests 的百分比。后续阈值配置要结合这些实际值：

- A/B：总 requests 需要低于 descheduler threshold，才能作为驱逐源。
- C：总 requests 需要高于 descheduler threshold，才能表现为资源整合目标。

4. 确认 Volcano scheduler 已安装，并且普通 Pod 可使用：

```yaml
spec:
  schedulerName: volcano
```

5. 确认 Volcano scheduler 配置中启用了 `binpack`。

常见配置类似：

```yaml
actions: "enqueue, allocate, backfill"
tiers:
- plugins:
  - name: priority
  - name: gang
    enablePreemptable: false
  - name: conformance
- plugins:
  - name: overcommit
  - name: drf
    enablePreemptable: false
  - name: predicates
  - name: proportion
  - name: nodeorder
  - name: binpack
```

如果录制时需要更稳定地看到所有 Pod 被压到 C，可以临时增强 binpack 权重：

```yaml
- name: binpack
  arguments:
    binpack.weight: 50
    binpack.cpu: 10
    binpack.memory: 10
```

脚本里通过 `PATCH_VOLCANO_BINPACK=true` 控制是否临时修改。共享环境谨慎使用，录制结束后执行清理脚本恢复。

6. 确认镜像可拉取。

默认镜像：

```text
registry.k8s.io/pause:3.10
docker.io/volcanosh/vc-descheduler:latest
```

如果目标环境不能访问这些镜像，需要提前同步到可访问的镜像仓库，然后在 `env.sh` 或执行前 export：

```bash
export PAUSE_IMAGE=<your-registry>/pause:3.10
export DESCHEDULER_IMAGE=<your-registry>/vc-descheduler:latest
```

## 参数配置

进入目录：

```bash
cd hack/finops-defrag-demo
```

修改或 export 参数：

```bash
export KUBE_CONTEXT=<your-context>   # 为空时使用当前 kubectl context
export NODE_A=<worker-a-name>
export NODE_B=<worker-b-name>
export NODE_C=<worker-c-name>

export PAUSE_IMAGE=<your-registry>/pause:3.10
export DESCHEDULER_IMAGE=<your-registry>/vc-descheduler:latest
```

如果需要临时增强 binpack：

```bash
export PATCH_VOLCANO_BINPACK=true
```

默认资源请求：

```bash
export ANCHOR_CPU=4
export ANCHOR_MEMORY=8Gi
export LOW_CPU=500m
export LOW_MEMORY=512Mi
export THRESHOLD_CPU=20
export THRESHOLD_MEMORY=20
```

含义：

- anchor Pod 固定在 C，用于让 C 高于阈值。
- low Pod 是待整理的低负载业务 Pod。
- A/B 上 demo Pod 加上节点已有基础负载后，仍应低于阈值。
- C 上 anchor 加上节点已有基础负载后，应高于阈值。

如果节点已有基础负载较高，需要先按现场实际值调整：

- 如果 A/B 已经高于 `20%`，可以提高 `THRESHOLD_CPU`/`THRESHOLD_MEMORY`，但要确保 C 仍高于阈值。
- 如果 C 没有高于阈值，可以增加 `ANCHOR_CPU`/`ANCHOR_MEMORY`。
- 如果节点规格较小，可以降低 anchor requests。例如 8C 节点可先尝试 `ANCHOR_CPU=2`。

## 执行流程

### 1. 构造初始碎片状态

```bash
bash 01-prepare-initial-state.sh
```

脚本做的事情：

- 给 A/B/C 打 demo 标签。
- 可选：增强 Volcano binpack 配置并重启 scheduler。
- 创建 `finops-demo` 命名空间。
- 将 anchor workload 固定到 C。
- 通过临时 cordon 控制 `low-a` 落到 A，`low-b` 落到 B。
- 最后恢复 A/B 可调度，C 保持 cordon，等待下一步触发整理。

录制点：

```bash
kubectl get pods -n finops-demo -o wide
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

预期：

- `anchor-c` 在 C。
- `low-a` 在 A。
- `low-b` 在 B。
- A/B 是低负载碎片节点。
- C 已有较高 requests。

### 2. 触发 descheduler 整理

```bash
bash 02-run-descheduler.sh
```

脚本做的事情：

- uncordon C，让迁移后的 Pod 可以落到 C。
- 创建一个 descheduler Job。
- descheduler 使用 `HighNodeUtilization` 策略。
- 策略通过 labelSelector 只处理 demo Pod，避免影响系统 Pod 或其他业务。
- 抓取 descheduler 日志到：

```text
hack/finops-defrag-demo/run-logs/descheduler.log
```

descheduler 核心配置：

```yaml
apiVersion: "descheduler/v1alpha2"
kind: "DeschedulerPolicy"
maxNoOfPodsToEvictPerNode: 10
maxNoOfPodsToEvictTotal: 10
profiles:
- name: default
  pluginConfig:
  - name: DefaultEvictor
    args:
      nodeFit: true
      labelSelector:
        matchLabels:
          app.kubernetes.io/part-of: finops-defrag-demo
      priorityThreshold:
        value: 10000
  - name: HighNodeUtilization
    args:
      thresholds:
        cpu: 20
        memory: 20
      evictableNamespaces:
        exclude:
        - kube-system
        - volcano-system
  plugins:
    balance:
      enabled:
      - HighNodeUtilization
```

说明：

- 有些环境或平台封装里会把同类策略显示为 `HighUtilization`。核心语义保持一致：从低利用率节点驱逐 Pod，让重建 Pod 走 binpack/MostAllocated。
- 如果集群已经有内置 descheduler，不一定要创建脚本里的 Job；可以直接把同等策略配置进去，然后手动触发或等待周期触发。

### 3. 验证结果

```bash
bash 03-verify.sh
```

重点看三类证据。

第一，Pod 最终落点：

```bash
kubectl get pods -n finops-demo -o wide
```

预期：

```text
anchor-c   -> NODE_C
low-a-*    -> NODE_C
low-b-*    -> NODE_C
```

第二，descheduler 事件：

```bash
kubectl get events -n finops-demo --sort-by=.lastTimestamp | grep HighNodeUtilization
```

预期能看到类似：

```text
pod evicted from <NODE_A> node by sigs.k8s.io/descheduler
pod evicted from <NODE_B> node by sigs.k8s.io/descheduler
```

第三，节点 requests 分布：

```bash
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

预期：

- A/B 的 `finops-demo` Pod 清空或显著减少。
- C 上有 `anchor-c` 和迁移后的 `low-a/low-b` Pod。
- C 的 CPU/Memory requests 明显高于 A/B。

### 4. 清理

录制完成后可以清理：

```bash
bash 04-cleanup.sh
```

脚本会删除：

- `finops-demo` 命名空间。
- demo descheduler Job/ConfigMap/RBAC。
- 如果之前 `PATCH_VOLCANO_BINPACK=true`，会尝试用备份恢复 Volcano scheduler ConfigMap 并重启 scheduler。

## 录制建议

建议按下面顺序录：

1. 展示集群节点。

```bash
kubectl get nodes -o wide
```

2. 展示 Volcano scheduler 配置中有 `binpack`。

```bash
kubectl -n volcano-system get cm volcano-scheduler-configmap -o yaml
```

3. 展示初始负载基线。

```bash
kubectl describe nodes ${NODE_A} ${NODE_B} ${NODE_C}
```

口径：

> 节点上会存在系统组件和基础负载，因此我们先看实际 requests，再选择阈值和 anchor 负载，保证 A/B 是低利用率碎片节点，C 是资源整合目标节点。

4. 执行初始状态脚本。

```bash
bash 01-prepare-initial-state.sh
```

5. 展示初始碎片。

```bash
kubectl get pods -n finops-demo -o wide
kubectl describe nodes ${NODE_A} ${NODE_B} ${NODE_C}
```

口径：

> 可以看到训练任务运行后，低负载 Pod 分散在 A/B，C 上已有一部分负载。此时如果只靠 scheduler，已经运行的 Pod 不会被主动移动。

6. 执行 descheduler。

```bash
bash 02-run-descheduler.sh
```

7. 展示 descheduler 日志。

```bash
grep -E "Node is underutilized|Node is overutilized|Evicted pod|Number of evicted pods" run-logs/descheduler.log
```

8. 展示最终结果。

```bash
bash 03-verify.sh
```

口径：

> descheduler 负责发现低利用率节点并驱逐可迁移 Pod；Volcano binpack 负责把重建 Pod 尽量放到已有较高利用率的 C 节点。两者组合后，A/B 的碎片被释放，负载被压实到 C。

## 常见问题

### Pod 没有被驱逐

检查：

- Pod 是否带有 `app.kubernetes.io/part-of=finops-defrag-demo` 标签。
- Pod 是否有 PDB 阻止驱逐。
- Pod 是否是 DaemonSet/static/mirror pod，这类通常不可驱逐。
- A/B 是否真的低于 `THRESHOLD_CPU` 和 `THRESHOLD_MEMORY`。
- descheduler 日志中是否有 `No removable pods` 或 `pod labels do not match`。

### Pod 被驱逐但没有落到 C

检查：

- C 是否已 uncordon。
- C 是否满足 Pod 的 nodeSelector/affinity/taint toleration。
- Pod 是否设置了 `schedulerName: volcano`。
- Volcano scheduler 是否启用了 `binpack`。
- 如果结果不稳定，录制环境可临时设置 `PATCH_VOLCANO_BINPACK=true`。

### 节点上已有基础负载，阈值怎么调

以 `kubectl describe node` 看到的 requests 百分比为准：

- A/B 作为驱逐源，需要低于 thresholds。
- C 作为整合目标，需要高于 thresholds。
- 如果 A/B 基础负载已经接近阈值，不要只调大 low Pod 数量，否则会让 A/B 不再低利用率。优先提高 threshold，同时提高 C 的 anchor requests，让 C 仍高于 threshold。

## 保守性说明

这个 Demo 使用 Deployment 和 pause 容器模拟训练任务尾部碎片。真实训练任务录制时建议选择可重启、可驱逐、无本地状态依赖的 Pod，避免用有状态任务或关键服务做演示对象。
