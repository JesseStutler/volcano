#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"

echo "== Pods =="
kubectl_cmd -n "${DEMO_NS}" get pods -o wide

echo
echo "== Recent descheduler events =="
kubectl_cmd -n "${DEMO_NS}" get events --sort-by=.lastTimestamp | grep -E "HighNodeUtilization|Successfully assigned|Created pod|Killing" || true

echo
echo "== Node request summary =="
kubectl_cmd describe nodes "${NODE_A}" "${NODE_B}" "${NODE_C}" | sed -n '/^Name:/,/^Events:/p'

echo
echo "== Expected result =="
echo "A(${NODE_A}) and B(${NODE_B}) should have no finops-demo low-* pods."
echo "C(${NODE_C}) should have anchor-c plus all low-a/low-b pods."

