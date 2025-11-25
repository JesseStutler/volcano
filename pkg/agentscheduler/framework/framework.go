/*
Copyright 2018 The Kubernetes Authors.
Copyright 2018-2023 The Volcano Authors.

Modifications made by Volcano authors:
- Enhanced session initialization with configuration support

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package framework

import (
	"k8s.io/klog/v2"
	k8scache "k8s.io/kubernetes/pkg/scheduler/backend/cache"
	"k8s.io/kubernetes/pkg/scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/conf"
	k8sutil "volcano.sh/volcano/pkg/scheduler/plugins/util/k8s"
)

// Framework manages the scheduler plugins and their execution points.
type Framework struct {
	*k8sutil.Framework // Embedding Framework to implement framework.Handle interface

	plugins map[string]Plugin
	Tiers   []conf.Tier

	// Function registries
	PredicateFns      map[string]api.PredicateFn
	PrePredicateFns   map[string]api.PrePredicateFn
	NodeOrderFns      map[string]api.NodeOrderFn
	BatchNodeOrderFns map[string]api.BatchNodeOrderFn
	NodeMapFns        map[string]api.NodeMapFn
	NodeReduceFns     map[string]api.NodeReduceFn

	Cache cache.Cache // TODO: need to replace to agent scheduler's own cache
}

var _ framework.Handle = &Framework{}

// NewFramework initializes the framework with the given plugins.
func NewFramework(tiers []conf.Tier, cache cache.Cache) *Framework {
	utilFwk := k8sutil.NewFramework(
		nil, // fast path scheduler needs to use snapshot shared lister instead
		k8sutil.WithSnapshotSharedLister(k8scache.NewEmptySnapshot()), // TODO: may need to use to volcano scheduler's own snapshot?
		k8sutil.WithSharedDRAManager(cache.SharedDRAManager()),
		k8sutil.WithClientSet(cache.Client()),
		k8sutil.WithInformerFactory(cache.SharedInformerFactory()),
	)

	fwk := &Framework{
		plugins:           make(map[string]Plugin),
		Tiers:             tiers,
		PredicateFns:      make(map[string]api.PredicateFn),
		PrePredicateFns:   make(map[string]api.PrePredicateFn),
		NodeOrderFns:      make(map[string]api.NodeOrderFn),
		BatchNodeOrderFns: make(map[string]api.BatchNodeOrderFn),
		NodeMapFns:        make(map[string]api.NodeMapFn),
		NodeReduceFns:     make(map[string]api.NodeReduceFn),

		Cache: cache,

		Framework: utilFwk,
	}

	for _, tier := range tiers {
		for _, pluginConf := range tier.Plugins {
			if pb, found := GetPluginBuilder(pluginConf.Name); !found {
				klog.Errorf("Failed to get plugin %s.", pluginConf.Name)
			} else {
				plugin := pb(pluginConf.Arguments)
				fwk.plugins[plugin.Name()] = plugin
				plugin.OnSchedulingStart(fwk)
			}
		}
	}

	return fwk
}
