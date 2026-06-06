#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"
LOG_DIR="${SCRIPT_DIR}/run-logs"
mkdir -p "${LOG_DIR}"

echo "[1/4] Uncordon C so evicted pods can be packed there"
kubectl_cmd uncordon "${NODE_C}" || true

echo "[2/4] Create one-shot descheduler job"
kubectl_cmd -n "${VOLCANO_NS}" delete job volcano-descheduler-finops-demo --ignore-not-found=true
cat <<EOF | kubectl_cmd apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: volcano-descheduler-finops-demo
  namespace: ${VOLCANO_NS}
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
            cpu: ${THRESHOLD_CPU}
            memory: ${THRESHOLD_MEMORY}
          evictableNamespaces:
            exclude:
            - kube-system
            - ${VOLCANO_NS}
      plugins:
        balance:
          enabled:
          - HighNodeUtilization
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: volcano-descheduler-finops-demo
  namespace: ${VOLCANO_NS}
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
  namespace: ${VOLCANO_NS}
---
apiVersion: batch/v1
kind: Job
metadata:
  name: volcano-descheduler-finops-demo
  namespace: ${VOLCANO_NS}
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/part-of: finops-defrag-demo
        app.kubernetes.io/name: volcano-descheduler-finops-demo
    spec:
      restartPolicy: Never
      serviceAccountName: volcano-descheduler-finops-demo
      containers:
      - name: descheduler
        image: ${DESCHEDULER_IMAGE}
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
EOF

echo "[3/4] Wait for first descheduler scan"
kubectl_cmd -n "${VOLCANO_NS}" wait --for=condition=Ready pod -l job-name=volcano-descheduler-finops-demo --timeout=120s
sleep "${DESCHEDULER_WAIT_SECONDS}"

echo "[4/4] Capture logs and stop descheduler"
kubectl_cmd -n "${VOLCANO_NS}" logs job/volcano-descheduler-finops-demo | tee "${LOG_DIR}/descheduler.log"
kubectl_cmd -n "${VOLCANO_NS}" delete job volcano-descheduler-finops-demo --ignore-not-found=true

echo
echo "After descheduling:"
kubectl_cmd -n "${DEMO_NS}" get pods -o wide

