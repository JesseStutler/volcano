#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"

echo "[1/4] Stop/delete descheduler demo objects"
kubectl_cmd -n "${VOLCANO_NS}" delete job volcano-descheduler-finops-demo --ignore-not-found=true
kubectl_cmd -n "${VOLCANO_NS}" delete cm volcano-descheduler-finops-demo --ignore-not-found=true
kubectl_cmd -n "${VOLCANO_NS}" delete sa volcano-descheduler-finops-demo --ignore-not-found=true
kubectl_cmd delete clusterrole volcano-descheduler-finops-demo --ignore-not-found=true
kubectl_cmd delete clusterrolebinding volcano-descheduler-finops-demo --ignore-not-found=true

echo "[2/4] Delete demo namespace"
kubectl_cmd delete ns "${DEMO_NS}" --ignore-not-found=true

echo "[3/4] Uncordon nodes"
kubectl_cmd uncordon "${NODE_A}" || true
kubectl_cmd uncordon "${NODE_B}" || true
kubectl_cmd uncordon "${NODE_C}" || true

if [[ -f "${SCRIPT_DIR}/volcano-scheduler.conf.backup" ]]; then
  echo "[4/4] Restore Volcano scheduler ConfigMap from backup"
  kubectl_cmd -n "${VOLCANO_NS}" create cm "${VOLCANO_SCHEDULER_CM}" \
    --from-file=volcano-scheduler.conf="${SCRIPT_DIR}/volcano-scheduler.conf.backup" \
    --dry-run=client -o yaml | kubectl_cmd apply -f -
  kubectl_cmd -n "${VOLCANO_NS}" rollout restart deploy "${VOLCANO_SCHEDULER_DEPLOY}"
  kubectl_cmd -n "${VOLCANO_NS}" rollout status deploy "${VOLCANO_SCHEDULER_DEPLOY}" --timeout=120s
else
  echo "[4/4] No scheduler backup found; skip scheduler restore"
fi
