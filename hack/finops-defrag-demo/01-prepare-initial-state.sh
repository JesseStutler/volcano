#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"

echo "[1/7] Label demo nodes"
kubectl_cmd label node "${NODE_A}" finops-demo/enabled=true finops-demo/role=A --overwrite
kubectl_cmd label node "${NODE_B}" finops-demo/enabled=true finops-demo/role=B --overwrite
kubectl_cmd label node "${NODE_C}" finops-demo/enabled=true finops-demo/role=C --overwrite

if [[ "${PATCH_VOLCANO_BINPACK}" == "true" ]]; then
  echo "[2/7] Patch Volcano scheduler config to strengthen binpack scoring"
  kubectl_cmd -n "${VOLCANO_NS}" get cm "${VOLCANO_SCHEDULER_CM}" \
    -o go-template='{{ index .data "volcano-scheduler.conf" }}' \
    > "${SCRIPT_DIR}/volcano-scheduler.conf.backup"
  cat <<EOF | kubectl_cmd apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${VOLCANO_SCHEDULER_CM}
  namespace: ${VOLCANO_NS}
data:
  volcano-scheduler.conf: |
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
        arguments:
          binpack.weight: ${BINPACK_WEIGHT}
          binpack.cpu: ${BINPACK_CPU}
          binpack.memory: ${BINPACK_MEMORY}
EOF
  kubectl_cmd -n "${VOLCANO_NS}" rollout restart deploy "${VOLCANO_SCHEDULER_DEPLOY}"
  kubectl_cmd -n "${VOLCANO_NS}" rollout status deploy "${VOLCANO_SCHEDULER_DEPLOY}" --timeout=120s
else
  echo "[2/7] Skip Volcano scheduler patch; assuming binpack is already enabled"
fi

echo "[3/7] Recreate demo namespace"
kubectl_cmd delete ns "${DEMO_NS}" --ignore-not-found=true
while kubectl_cmd get ns "${DEMO_NS}" >/dev/null 2>&1; do
  sleep 1
done
kubectl_cmd create ns "${DEMO_NS}"

echo "[4/7] Place anchor workload on C while C is cordoned"
kubectl_cmd cordon "${NODE_C}"
kubectl_cmd uncordon "${NODE_A}" || true
kubectl_cmd uncordon "${NODE_B}" || true
cat <<EOF | kubectl_cmd apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anchor-c
  namespace: ${DEMO_NS}
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
        image: ${PAUSE_IMAGE}
        resources:
          requests:
            cpu: "${ANCHOR_CPU}"
            memory: ${ANCHOR_MEMORY}
EOF
kubectl_cmd -n "${DEMO_NS}" rollout status deploy/anchor-c --timeout=120s

echo "[5/7] Place low-a on A"
kubectl_cmd uncordon "${NODE_A}" || true
kubectl_cmd cordon "${NODE_B}"
kubectl_cmd cordon "${NODE_C}"
cat <<EOF | kubectl_cmd apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: low-a
  namespace: ${DEMO_NS}
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
        image: ${PAUSE_IMAGE}
        resources:
          requests:
            cpu: "${LOW_CPU}"
            memory: ${LOW_MEMORY}
EOF
kubectl_cmd -n "${DEMO_NS}" rollout status deploy/low-a --timeout=120s

echo "[6/7] Place low-b on B"
kubectl_cmd cordon "${NODE_A}"
kubectl_cmd uncordon "${NODE_B}" || true
kubectl_cmd cordon "${NODE_C}"
cat <<EOF | kubectl_cmd apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: low-b
  namespace: ${DEMO_NS}
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
        image: ${PAUSE_IMAGE}
        resources:
          requests:
            cpu: "${LOW_CPU}"
            memory: ${LOW_MEMORY}
EOF
kubectl_cmd -n "${DEMO_NS}" rollout status deploy/low-b --timeout=120s

echo "[7/7] Restore A/B schedulable. Keep C cordoned until descheduler step."
kubectl_cmd uncordon "${NODE_A}" || true
kubectl_cmd uncordon "${NODE_B}" || true
kubectl_cmd cordon "${NODE_C}"

echo
echo "Initial state:"
kubectl_cmd -n "${DEMO_NS}" get pods -o wide
echo
echo "Node request summary:"
kubectl_cmd describe nodes "${NODE_A}" "${NODE_B}" "${NODE_C}" | sed -n '/^Name:/,/^Events:/p'
