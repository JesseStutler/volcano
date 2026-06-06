#!/usr/bin/env bash
set -euo pipefail

# Copy this file or export these variables before running the demo scripts.

# Leave empty to use the current kubectl context.
: "${KUBE_CONTEXT:=}"

: "${DEMO_NS:=finops-demo}"
: "${VOLCANO_NS:=volcano-system}"
: "${VOLCANO_SCHEDULER_DEPLOY:=volcano-scheduler}"
: "${VOLCANO_SCHEDULER_CM:=volcano-scheduler-configmap}"

# Pick three worker nodes for the demo.
: "${NODE_A:=volcano-worker}"
: "${NODE_B:=volcano-worker2}"
: "${NODE_C:=volcano-worker3}"

# Images. In restricted environments, mirror these images to an accessible registry.
: "${PAUSE_IMAGE:=registry.k8s.io/pause:3.10}"
: "${DESCHEDULER_IMAGE:=docker.io/volcanosh/vc-descheduler:latest}"

# Demo requests. Keep C above the descheduler threshold, and A/B below it.
: "${ANCHOR_CPU:=4}"
: "${ANCHOR_MEMORY:=8Gi}"
: "${LOW_CPU:=500m}"
: "${LOW_MEMORY:=512Mi}"

# Descheduler threshold for HighNodeUtilization. Nodes below both values are candidates.
: "${THRESHOLD_CPU:=20}"
: "${THRESHOLD_MEMORY:=20}"

# Optional: temporarily make Volcano binpack scoring stronger for a deterministic recording.
# If the target cluster already has binpack/most-allocated behavior configured, keep this false.
: "${PATCH_VOLCANO_BINPACK:=false}"
: "${BINPACK_WEIGHT:=50}"
: "${BINPACK_CPU:=10}"
: "${BINPACK_MEMORY:=10}"

# How long to leave the descheduler running after the first scan starts.
: "${DESCHEDULER_WAIT_SECONDS:=12}"

kubectl_cmd() {
  if [[ -n "${KUBE_CONTEXT}" ]]; then
    kubectl --context "${KUBE_CONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}
