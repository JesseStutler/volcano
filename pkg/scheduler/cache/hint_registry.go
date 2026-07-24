/*
Copyright 2025 The Volcano Authors.

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

package cache

import (
	"context"
	"sync"

	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/klog/v2"
	fwk "k8s.io/kube-scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
)

// HintRegistry stores the HintProviders declared by plugins, keyed by plugin
// name, so the UnschedulableJobCache can look up a plugin's events at Record time.
type HintRegistry struct {
	mu             sync.RWMutex
	eventsByPlugin map[string][]api.ClusterEventWithHint
}

// NewHintRegistry creates an empty HintRegistry.
func NewHintRegistry() *HintRegistry {
	return &HintRegistry{
		eventsByPlugin: make(map[string][]api.ClusterEventWithHint),
	}
}

// Register calls p.EventsToRegister once, then stores the returned slice under
// name, overwriting any previous entry for the same plugin. name must match
// Rejection.Plugin.
func (r *HintRegistry) Register(name string, p api.HintProvider) {
	if r == nil || p == nil {
		return
	}
	events, err := p.EventsToRegister(context.TODO())
	if err != nil {
		klog.Errorf("Failed to register hints for plugin %s: %v", name, err)
		return
	}
	if len(events) == 0 {
		return
	}

	r.mu.Lock()
	defer r.mu.Unlock()
	r.eventsByPlugin[name] = events
	klog.V(5).Infof("Registered %d hint event(s) for plugin %s", len(events), name)
}

// eventsForPlugin returns a snapshot of the events registered for the given
// plugin, or nil when the plugin has no HintProvider.
func (r *HintRegistry) eventsForPlugin(name string) []api.ClusterEventWithHint {
	r.mu.RLock()
	defer r.mu.RUnlock()
	events, ok := r.eventsByPlugin[name]
	if !ok {
		return nil
	}
	out := make([]api.ClusterEventWithHint, len(events))
	copy(out, events)
	return out
}

// hasPlugin reports whether the plugin declared any hints.
func (r *HintRegistry) hasPlugin(name string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	_, ok := r.eventsByPlugin[name]
	return ok
}

// subscribedResources returns the union of all event resources declared across
// every registered plugin.
func (r *HintRegistry) subscribedResources() sets.Set[fwk.EventResource] {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := sets.New[fwk.EventResource]()
	for _, events := range r.eventsByPlugin {
		for _, e := range events {
			out.Insert(e.Event.Resource)
		}
	}
	return out
}
