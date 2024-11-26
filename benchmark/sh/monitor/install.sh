#!/bin/bash
# Copyright 2024 The Volcano Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack --set alertmanager.enabled=false \
 --set prometheus.prometheusSpec.resources.limits.cpu="500m" \
 --set prometheus-node-exporter.tolerations="" \
 prometheus-community/kube-prometheus-stack -n monitoring --create-namespace