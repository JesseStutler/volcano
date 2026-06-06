# 资源碎片整理演示

这个文档记录一套手工可执行的演示流程：先构造“训练任务运行一段时间后 Pod 分散在多个节点”的状态，再通过 descheduler 触发驱逐，由 Volcano binpack 负责重调度，把负载压到一个目标节点上。

文档里的 YAML 可以直接用 `kubectl apply`，也可以按字段在控制台里手工创建。不同环境的 descheduler 配置入口可能不一样，核心参数保持一致即可。

## 场景说明

初始状态：

- 选 3 个 worker 节点，记为 A、B、C。
- A/B 上放低负载 Pod，模拟碎片。
- C 上放一个 anchor Pod，模拟已有训练负载。
- Volcano scheduler 已开启 binpack。
- 节点上可能还有系统组件、监控组件或其他基础负载，阈值要按现场 requests 调整。

整理过程：

- descheduler 使用高利用率整理策略，从低利用率节点驱逐可迁移 Pod。
- Deployment 自动重建 Pod。
- 重建 Pod 使用 `schedulerName: volcano`。
- Volcano binpack 将新 Pod 尽量调度到已有较高利用率的 C。

最后希望看到：

- A/B 上 demo Pod 清空或明显减少。
- C 上有 anchor Pod 和迁移后的低负载 Pod。

可以这样讲初始状态：

> 这里模拟训练任务运行一段时间之后的碎片状态。任务结束、缩容或局部空闲后，一些 Pod 还散在多个节点上，每个节点都占一点资源。scheduler 的 binpack 只影响新 Pod 的放置，不会主动移动已经运行的 Pod，所以需要 descheduler 先触发驱逐，再交给 Volcano binpack 重新压实。

## 变量

下面的名字按现场替换：

```text
NODE_A=<worker-a>
NODE_B=<worker-b>
NODE_C=<worker-c>
DEMO_NS=finops-demo
PAUSE_IMAGE=<reachable-registry>/pause:3.10
DESCHEDULER_IMAGE=<reachable-registry>/vc-descheduler:<tag>
```

镜像不一定能直接从外网拉取。提前确认目标集群能访问 `PAUSE_IMAGE` 和 `DESCHEDULER_IMAGE`。如果平台已经内置 descheduler，就不需要部署文档里的 descheduler Job，只需要按同等策略配置即可。

建议先看节点当前 requests：

```bash
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

关注 `Allocated resources`：

- A/B 总 requests 要低于 descheduler 阈值，才能作为驱逐源。
- C 总 requests 要高于阈值，才能作为压实目标。
- 如果 A/B 基础负载已经高于 20%，就把阈值调高，同时增加 C 的 anchor requests，让 C 仍高于阈值。

示例参数按 16C/32Gi 节点写：

```text
anchor: cpu=4, memory=8Gi
low pod: cpu=500m, memory=512Mi
threshold: cpu=20, memory=20
```

如果节点是 8C，可以先把 anchor 调成 `cpu=2`。如果现场基础负载较高，以实际 requests 为准。

## 1. 检查 Volcano binpack

确认 Volcano scheduler 配置中有 `binpack`：

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

如果现场效果不稳定，录制时可以临时把 binpack 权重调高。改完需要重启 scheduler 组件。

```yaml
- name: binpack
  arguments:
    binpack.weight: 50
    binpack.cpu: 10
    binpack.memory: 10
```

这一步只为提高演示确定性。录完之后恢复原配置。

## 2. 给节点打标签

给三个节点标记角色。控制台里手工加 label 也可以。

```bash
kubectl label node <NODE_A> finops-demo/enabled=true finops-demo/role=A --overwrite
kubectl label node <NODE_B> finops-demo/enabled=true finops-demo/role=B --overwrite
kubectl label node <NODE_C> finops-demo/enabled=true finops-demo/role=C --overwrite
```

确认：

```bash
kubectl get nodes -L finops-demo/role,finops-demo/enabled
```

## 3. 构造初始状态

为了录制稳定，可以手工控制初始落点：

1. C 上创建 anchor。
2. A 上创建 `low-a` 两个副本。
3. B 上创建 `low-b` 两个副本。

如果可以用命令操作，最简单的做法是临时 cordon 节点来控制落点：

```bash
# anchor 放 C。C 即使 cordon，也通过 toleration 允许 anchor 落上去。
kubectl cordon <NODE_C>

# low-a 放 A：只保留 A 可调度。
kubectl uncordon <NODE_A>
kubectl cordon <NODE_B>
kubectl cordon <NODE_C>

# low-b 放 B：只保留 B 可调度。
kubectl cordon <NODE_A>
kubectl uncordon <NODE_B>
kubectl cordon <NODE_C>
```

如果只能在控制台操作，也可以直接在 workload 里设置 `nodeSelector` 或节点亲和性，把 `low-a` 固定到 A、`low-b` 固定到 B。触发整理前需要把固定到 A/B 的强约束撤掉，否则重建 Pod 不能迁到 C。下面的示例使用 demo 节点范围亲和性，不固定 A/B；初始落点靠临时 cordon 控制。

创建命名空间：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finops-demo
```

anchor workload：

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
      tolerations:
      - key: node.kubernetes.io/unschedulable
        operator: Exists
        effect: NoSchedule
      containers:
      - name: pause
        image: <PAUSE_IMAGE>
        resources:
          requests:
            cpu: "4"
            memory: 8Gi
```

low-a workload：

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

low-b workload 只需要把名字和 label 从 `low-a` 改成 `low-b`：

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

初始状态验证：

```bash
kubectl get pods -n finops-demo -o wide
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

录制时要看到：

- `anchor-c` 在 C。
- `low-a` 在 A。
- `low-b` 在 B。
- A/B 在阈值以下，C 在阈值以上。

## 4. 触发整理

触发前先让 C 可调度：

```bash
kubectl uncordon <NODE_C>
```

如果平台自带 descheduler，就在对应配置入口里设置同等策略。下面是等价的 policy 参考：

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

有的平台把同类能力叫 `HighUtilization`。不用纠结名字，关键是：

- 驱逐源：低于阈值的节点。
- 驱逐对象：只选 demo label 或 demo namespace 下的 Pod。
- 驱逐检查：开启 node fit，避免驱逐后无处可去。
- 重建调度：Pod 要使用 `schedulerName: volcano`。
- 调度策略：Volcano 开启 binpack。

如果没有内置 descheduler，可以临时创建一个 Job。注意替换镜像地址。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: volcano-descheduler-finops-demo
  namespace: volcano-system
data:
  policy.yaml: |
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
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: volcano-descheduler-finops-demo
  namespace: volcano-system
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: volcano-descheduler-finops-demo
rules:
- apiGroups: ["events.k8s.io"]
  resources: ["events"]
  verbs: ["create", "update"]
- apiGroups: [""]
  resources: ["nodes", "namespaces", "pods"]
  verbs: ["get", "watch", "list"]
- apiGroups: [""]
  resources: ["pods/eviction"]
  verbs: ["create"]
- apiGroups: ["policy"]
  resources: ["poddisruptionbudgets"]
  verbs: ["get", "watch", "list"]
- apiGroups: ["scheduling.k8s.io"]
  resources: ["priorityclasses"]
  verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: volcano-descheduler-finops-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: volcano-descheduler-finops-demo
subjects:
- kind: ServiceAccount
  name: volcano-descheduler-finops-demo
  namespace: volcano-system
---
apiVersion: batch/v1
kind: Job
metadata:
  name: volcano-descheduler-finops-demo
  namespace: volcano-system
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      serviceAccountName: volcano-descheduler-finops-demo
      containers:
      - name: descheduler
        image: <DESCHEDULER_IMAGE>
        imagePullPolicy: IfNotPresent
        command:
        - /vc-descheduler
        - --policy-config-file=/policy-dir/policy.yaml
        - --descheduling-interval=60s
        - --leader-elect=false
        - --v=4
        volumeMounts:
        - mountPath: /policy-dir
          name: policy-volume
      volumes:
      - name: policy-volume
        configMap:
          name: volcano-descheduler-finops-demo
```

Job 跑出第一轮 eviction 后可以删掉，避免持续反复驱逐：

```bash
kubectl -n volcano-system logs job/volcano-descheduler-finops-demo
kubectl -n volcano-system delete job volcano-descheduler-finops-demo
```

## 5. 验证

Pod 落点：

```bash
kubectl get pods -n finops-demo -o wide
```

期望：

```text
anchor-c   -> NODE_C
low-a-*    -> NODE_C
low-b-*    -> NODE_C
```

事件：

```bash
kubectl get events -n finops-demo --sort-by=.lastTimestamp | grep -E "HighNodeUtilization|HighUtilization|Successfully assigned"
```

能看到两类信息：

- descheduler 从 A/B 驱逐 Pod。
- Volcano 后续把新 Pod 调度到 C。

节点 requests：

```bash
kubectl describe nodes <NODE_A> <NODE_B> <NODE_C>
```

期望：

- A/B 上没有 `finops-demo` 的低负载 Pod，或者数量明显减少。
- C 上有 anchor 和迁移后的 low Pod。
- C 的 requests 明显高于 A/B。

descheduler 日志里比较有用的关键字：

```bash
Node is underutilized
Node is overutilized
Evicted pod
Number of evicted pods
```

## 录制顺序

1. 展示节点列表。
2. 展示 Volcano scheduler 配置里有 `binpack`。
3. 展示三个节点的 requests 基线。
4. 创建初始 workload，展示 A/B/C 落点。
5. 触发 descheduler。
6. 展示 eviction 事件或日志。
7. 展示最终 Pod 全部或大部分被压到 C。
8. 展示 A/B requests 降低、C requests 升高。

讲解不要太复杂，围绕三句话：

- 这是训练任务运行后的碎片状态。
- descheduler 负责把低利用率节点上的可迁移 Pod 驱逐出来。
- Volcano binpack 负责把重建 Pod 放到更适合压实的节点。

## 常见问题

### Pod 没有被驱逐

检查：

- Pod 是否带有 `app.kubernetes.io/part-of=finops-defrag-demo`。
- Pod 是否被 PDB 保护。
- Pod 是否来自 DaemonSet、static pod 或 mirror pod。
- A/B 的实际 requests 是否低于 thresholds。
- descheduler 日志是否出现 `pod labels do not match` 或 `No removable pods`。

### Pod 被驱逐后没有去 C

检查：

- C 是否已 uncordon。
- C 是否满足 Pod 的 nodeSelector、affinity 和 taint toleration。
- Pod 是否是 `schedulerName: volcano`。
- Volcano scheduler 是否启用 binpack。
- 如果现场调度结果受其他插件影响，可以临时提高 binpack 权重。

### 节点基础负载影响阈值

不要照搬固定阈值。先看节点 requests：

- A/B 要低于 threshold。
- C 要高于 threshold。
- 如果 A/B 基础负载偏高，提高 threshold，同时提高 C 的 anchor requests。
- 如果 C 基础负载已经够高，可以降低 anchor requests，避免过度占资源。

## 清理

录制结束后清理 demo workload：

```bash
kubectl delete ns finops-demo
kubectl uncordon <NODE_A>
kubectl uncordon <NODE_B>
kubectl uncordon <NODE_C>
```

如果临时创建过 descheduler Job/RBAC：

```bash
kubectl -n volcano-system delete job volcano-descheduler-finops-demo --ignore-not-found
kubectl -n volcano-system delete cm volcano-descheduler-finops-demo --ignore-not-found
kubectl -n volcano-system delete sa volcano-descheduler-finops-demo --ignore-not-found
kubectl delete clusterrole volcano-descheduler-finops-demo --ignore-not-found
kubectl delete clusterrolebinding volcano-descheduler-finops-demo --ignore-not-found
```

如果临时改过 Volcano scheduler binpack 权重，恢复原配置并重启 scheduler。

