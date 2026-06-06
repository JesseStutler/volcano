# 资源碎片整理演示方案

## 目的

演示一个训练任务运行一段时间后的资源碎片整理场景：

- 集群本身开启 Volcano binpack，正常情况下新任务会倾向于往已有负载的节点上放。
- 训练任务运行和结束一段时间后，A、B 节点上仍散落一些低负载 Pod，形成碎片。
- C 节点上已有一部分训练负载，适合作为收拢目标。
- 通过 descheduler 驱逐 A、B 上的低负载 Pod。
- Pod 重建后交给 Volcano scheduler。
- Volcano binpack 将这些 Pod 尽量重新调度到 C，让 A、B 空出来。

核心展示点：

- descheduler 负责“把可迁移 Pod 释放出来”。
- Volcano binpack 负责“把重建 Pod 尽量收拢到目标节点”。
- 整理后 A、B 的业务 Pod 减少，C 的资源利用率升高。

## 角色定义

选择 3 个 worker 节点：

```text
NODE_A=<worker-a>
NODE_B=<worker-b>
NODE_C=<worker-c>
DEMO_NS=finops-demo
```

节点含义：

- `NODE_A`：碎片节点 A。
- `NODE_B`：碎片节点 B。
- `NODE_C`：负载收拢目标节点。

建议先看三个节点当前 requests：

```bash
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

阈值设置原则：

- A/B 总 requests 低于 descheduler 阈值。
- C 总 requests 高于 descheduler 阈值。
- 如果节点上已有基础负载，按现场 requests 调整 anchor Pod 的 requests 或 descheduler 阈值。

## 1. Volcano 配置

确认 scheduler 配置中启用 `binpack`：

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

如果演示时调度结果不够稳定，可以临时提高 binpack 权重：

```yaml
- name: binpack
  arguments:
    binpack.weight: 50
    binpack.cpu: 10
    binpack.memory: 10
```

改完 scheduler 配置后，重启 scheduler 组件。演示结束后恢复原配置。

## 2. 节点标签

给三个节点打标签，用于 workload 选择演示节点：

```bash
kubectl label node <NODE_A> finops-demo/enabled=true finops-demo/role=A --overwrite
kubectl label node <NODE_B> finops-demo/enabled=true finops-demo/role=B --overwrite
kubectl label node <NODE_C> finops-demo/enabled=true finops-demo/role=C --overwrite
```

确认：

```bash
kubectl get nodes -L finops-demo/role,finops-demo/enabled
```

## 3. 初始场景设置

初始状态要构造成：

```text
NODE_A: low-a x 2
NODE_B: low-b x 2
NODE_C: anchor-c x 1
```

说明：

- `anchor-c` 模拟 C 上已有训练负载。
- `low-a`、`low-b` 模拟散落在 A/B 上的低负载训练 Pod。
- 所有 demo Pod 都设置 `schedulerName: volcano`。
- `low-a`、`low-b` 从一开始就只限制在 A/B/C 这三个 demo 节点内，不固定到 A 或 B。
- 这里不是要证明初始调度一定会这么放，而是构造一个训练任务运行后常见的碎片状态，方便后面展示整理效果。

建议初始场景准备阶段先不要触发 descheduler。可以让 descheduler 组件存在，但策略先不启用，或者先不要创建本次 demo 的策略。等初始状态录完，再启用/触发 descheduler。

初始落点用“临时禁止/恢复节点调度”来控制：

1. 先让 C 可调度，创建 `anchor-c`，让它落到 C。
2. 禁止 B/C 调度，只保留 A 可调度，创建 `low-a`。
3. 禁止 A/C 调度，只保留 B 可调度，创建 `low-b`。
4. 初始状态录完后，恢复 A/B/C 可调度。

如果通过页面操作，就在节点页面临时将对应节点设置为不可调度；如果用命令，可以用 `cordon/uncordon`。

命令方式参考：

```bash
# 创建 anchor 前：确保 C 可调度
kubectl uncordon <NODE_C>

# 创建 low-a 前：只保留 A 可调度
kubectl uncordon <NODE_A>
kubectl cordon <NODE_B>
kubectl cordon <NODE_C>

# 创建 low-b 前：只保留 B 可调度
kubectl cordon <NODE_A>
kubectl uncordon <NODE_B>
kubectl cordon <NODE_C>

# 初始状态录完后：恢复 A/B/C 可调度，再触发 descheduler
kubectl uncordon <NODE_A>
kubectl uncordon <NODE_B>
kubectl uncordon <NODE_C>
```

### 3.1 创建命名空间

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finops-demo
```

### 3.2 创建 C 上的 anchor 负载

根据节点规格调整 requests。16C/32Gi 节点可先用 `4 CPU / 8Gi`。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anchor-c
  namespace: finops-demo
  labels:
    app.kubernetes.io/part-of: finops-defrag-demo
    app.kubernetes.io/name: anchor-c
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: anchor-c
  template:
    metadata:
      labels:
        app.kubernetes.io/part-of: finops-defrag-demo
        app.kubernetes.io/name: anchor-c
    spec:
      schedulerName: volcano
      nodeSelector:
        finops-demo/role: C
      containers:
      - name: pause
        image: <PAUSE_IMAGE>
        resources:
          requests:
            cpu: "4"
            memory: 8Gi
```

### 3.3 创建 A/B 上的低负载 Pod

每个 Pod 设置 `500m CPU / 512Mi`，按需要调整。

`low-a`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: low-a
  namespace: finops-demo
  labels:
    app.kubernetes.io/part-of: finops-defrag-demo
    app.kubernetes.io/name: low-a
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: low-a
  template:
    metadata:
      labels:
        app.kubernetes.io/part-of: finops-defrag-demo
        app.kubernetes.io/name: low-a
    spec:
      schedulerName: volcano
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: finops-demo/enabled
                operator: In
                values: ["true"]
      containers:
      - name: pause
        image: <PAUSE_IMAGE>
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

`low-b`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: low-b
  namespace: finops-demo
  labels:
    app.kubernetes.io/part-of: finops-defrag-demo
    app.kubernetes.io/name: low-b
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: low-b
  template:
    metadata:
      labels:
        app.kubernetes.io/part-of: finops-defrag-demo
        app.kubernetes.io/name: low-b
    spec:
      schedulerName: volcano
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: finops-demo/enabled
                operator: In
                values: ["true"]
      containers:
      - name: pause
        image: <PAUSE_IMAGE>
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
```

录制初始状态：

```bash
kubectl get pods -n finops-demo -o wide
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

需要看到：

```text
low-a   在 NODE_A
low-b   在 NODE_B
anchor  在 NODE_C
```

## 4. 整理前检查

触发 descheduler 前确认三件事：

- A/B/C 都已经恢复可调度。
- `low-a`、`low-b` 没有固定到 A/B，只限制在 A/B/C 这三个 demo 节点内。
- Volcano binpack 一直保持开启，不需要等到整理时才开启。

descheduler 在这一步之后再启用或手动触发。

## 5. Descheduler 配置

使用高利用率整理策略。不同平台入口可能不同，关键配置保持一致。前端能直接配置的话，优先用前端配置；下面的 YAML 只是字段参考。

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

配置含义：

- `thresholds.cpu/memory`: 低于该阈值的节点作为整理来源。
- `labelSelector`: 只驱逐本次 demo 的 Pod。
- `nodeFit: true`: 确保 Pod 驱逐后仍有节点可放。
- `maxNoOfPodsToEvict*`: 控制本次最多驱逐数量。

如果平台里策略名显示为 `HighUtilization`，按平台字段配置即可，语义保持一致。

## 6. 触发整理

初始状态录完、A/B/C 都恢复可调度后，再启用或手动触发 descheduler。

如果是周期性 descheduler，建议只打开本次 demo 策略，确认第一轮 eviction 完成后关闭策略，避免后面反复驱逐影响画面。

如果是临时 Job 方式，第一轮 eviction 完成后就删除 Job。

观察：

```bash
kubectl get pods -n finops-demo -o wide
kubectl get events -n finops-demo --sort-by=.lastTimestamp
```

日志关键字：

```text
Node is underutilized
Node is overutilized
Evicted pod
Number of evicted pods
```

## 7. 结果验证

期望整理后：

```text
NODE_A: 无 low-a / low-b，或数量明显减少
NODE_B: 无 low-a / low-b，或数量明显减少
NODE_C: anchor-c + low-a + low-b
```

验证命令：

```bash
kubectl get pods -n finops-demo -o wide
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

对比口径：

| 阶段 | A | B | C |
| --- | --- | --- | --- |
| 整理前 | low-a | low-b | anchor-c |
| 整理后 | 空或减少 | 空或减少 | anchor-c + low-a + low-b |

## 8. 录制顺序

1. 展示 Volcano scheduler 已启用 binpack。
2. 展示 A/B/C 三个节点当前 requests。
3. 创建初始 workload，展示 Pod 分散在 A/B/C。
4. 说明这是模拟训练任务运行后留下的碎片状态。
5. 恢复 A/B/C 可调度，确认 `low-a`、`low-b` 可以被重新调度到 C。
6. 展示并启用 descheduler 策略。
7. 展示 eviction 事件。
8. 展示最终 Pod 被压到 C。
9. 展示 A/B requests 下降、C requests 上升。

## 9. 清理

```bash
kubectl delete ns finops-demo
kubectl uncordon <NODE_A>
kubectl uncordon <NODE_B>
kubectl uncordon <NODE_C>
```

如果临时创建过 descheduler Job/RBAC，也一起删除。

如果临时改过 Volcano scheduler 配置，恢复原配置并重启 scheduler。
