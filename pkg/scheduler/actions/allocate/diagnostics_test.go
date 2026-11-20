/*
Copyright 2026 The Volcano Authors.

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

package allocate

import (
	"strings"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/utils/ptr"

	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/conf"
	"volcano.sh/volcano/pkg/scheduler/framework"
	networktopologyaware "volcano.sh/volcano/pkg/scheduler/plugins/network-topology-aware"
	"volcano.sh/volcano/pkg/scheduler/util"
)

// Allocate writes the records of the Job's final decision to JobInfo. The topology
// has two HyperNodes with one node each: h1 holds node-0 and h2 holds node-1.
func TestAllocateDiagnostics(t *testing.T) {
	const (
		waiting = api.PendingGangWaiting
		failed  = api.PendingTaskFailure
	)
	// affinity is the blocker of task-1 failing node affinity in hyperNode.
	affinity := func(hyperNode, placement string) api.SchedulingBlocker {
		return api.SchedulingBlocker{
			Scope: api.MemberScope, Reason: api.BlockerNodeAffinity, TaskID: "ns-task-1",
			HyperNodeName: hyperNode, PlacementDomain: placement,
		}
	}

	tests := []struct {
		name string
		// minMember is the gang minimum. The Pending members are task-0, task-1 and task-2.
		minMember int32
		// rejectedTask fails node affinity on the rejectedOn nodes.
		rejectedTask string
		rejectedOn   sets.Set[string]
		// minResources is the minimum that a HyperNode must hold for the PodGroup.
		minResources v1.ResourceList
		// smallNode has a single CPU, which leaves its HyperNode below minResources.
		smallNode string
		// runningOn hosts a fourth, running member. It establishes the Job's placement.
		runningOn string

		wantBinding  int
		wantPending  map[api.TaskID]api.PendingTaskDiagnosticKind
		wantBlockers []api.SchedulingBlocker
	}{
		{
			name:         "failed candidate followed by a selected candidate",
			minMember:    3,
			rejectedTask: "task-1",
			rejectedOn:   sets.New("node-0"),
			wantBinding:  3,
			wantPending:  map[api.TaskID]api.PendingTaskDiagnosticKind{},
		},
		{
			name:         "member fails in every permitted HyperNode",
			minMember:    3,
			rejectedTask: "task-1",
			rejectedOn:   sets.New("node-0", "node-1"),
			wantPending: map[api.TaskID]api.PendingTaskDiagnosticKind{
				"ns-task-0": waiting, "ns-task-1": failed, "ns-task-2": waiting,
			},
			wantBlockers: []api.SchedulingBlocker{affinity("h1", ""), affinity("h2", "")},
		},
		{
			name:         "established placement restricts the search",
			minMember:    4,
			rejectedTask: "task-1",
			rejectedOn:   sets.New("node-0", "node-1"),
			runningOn:    "node-0",
			wantPending: map[api.TaskID]api.PendingTaskDiagnosticKind{
				"ns-task-0": waiting, "ns-task-1": failed, "ns-task-2": waiting,
			},
			wantBlockers: []api.SchedulingBlocker{affinity("h1", "h1")},
		},
		{
			name:         "HyperNode below the minimum resources is not searched",
			minMember:    3,
			rejectedTask: "task-1",
			rejectedOn:   sets.New("node-0", "node-1"),
			minResources: api.BuildResourceList("3", "3Mi"),
			smallNode:    "node-0",
			wantPending: map[api.TaskID]api.PendingTaskDiagnosticKind{
				"ns-task-0": waiting, "ns-task-1": waiting, "ns-task-2": waiting,
			},
			wantBlockers: []api.SchedulingBlocker{
				{Scope: api.HyperNodeScope, Reason: api.BlockerInsufficientResources, ResourceName: v1.ResourceCPU, HyperNodeName: "h1"},
				affinity("h2", ""),
			},
		},
		{
			name:         "ready group with a failed member",
			minMember:    1,
			rejectedTask: "task-0",
			rejectedOn:   sets.New("node-0", "node-1"),
			wantBinding:  2,
			wantPending:  map[api.TaskID]api.PendingTaskDiagnosticKind{"ns-task-0": failed},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sc, tiers := newPlacementAllocationCache(t, 2, 3)
			t.Cleanup(func() { cache.ShutdownMockSchedulerCache(sc) })
			ready := &atomic.Bool{}
			ready.Store(true)
			sc.HyperNodesInfo = api.NewHyperNodesInfoWithCache(api.HyperNodeInfoMap{
				"h1": newPlacementTestHyperNode("h1", 1, ""),
				"h2": newPlacementTestHyperNode("h2", 1, ""),
			}, map[int]sets.Set[string]{1: sets.New("h1", "h2")}, map[string]sets.Set[string]{
				"h1": sets.New("node-0"), "h2": sets.New("node-1"),
			}, ready)
			pg := util.BuildPodGroupWithNetWorkTopologies("peer", "ns", "", "q", tt.minMember, nil, schedulingv1beta1.PodGroupInqueue, "hard", 1)
			if tt.minResources != nil {
				pg.Spec.MinResources = &tt.minResources
			}
			sc.AddPodGroupV1beta1(pg)
			if tt.smallNode != "" {
				require.NoError(t, sc.AddOrUpdateNode(util.BuildNode(tt.smallNode, api.BuildResourceList("1", "4Gi", api.ScalarResource{Name: "pods", Value: "2000"}), nil)))
			}
			if tt.runningOn != "" {
				sc.AddPod(util.BuildPod("ns", "task-running", tt.runningOn, v1.PodRunning, api.BuildResourceList("1", "1Mi"), "peer", nil, nil))
			}
			framework.RegisterPluginBuilder(networktopologyaware.PluginName, networktopologyaware.New)
			registerDryRunTestPlugins()
			tiers[0].Plugins = append(tiers[0].Plugins,
				conf.PluginOption{Name: networktopologyaware.PluginName, EnabledHyperNodeGradient: ptr.To(true), EnabledHyperNodeOrder: ptr.To(true)},
				conf.PluginOption{Name: dryRunTestPlugin, EnabledPredicate: ptr.To(true), EnabledTaskOrder: ptr.To(true)})
			ssn := framework.OpenSession(sc, tiers, nil)
			defer framework.CloseSession(ssn)
			// Order the members by name so that task-0 is always tried first.
			ssn.AddTaskOrderFn(dryRunTestPlugin, func(l, r interface{}) int {
				return strings.Compare(l.(*api.TaskInfo).Name, r.(*api.TaskInfo).Name)
			})
			ssn.AddPredicateFn(dryRunTestPlugin, func(task *api.TaskInfo, node *api.NodeInfo) error {
				if task.Name == tt.rejectedTask && tt.rejectedOn.Has(node.Name) {
					return api.NewFitErrWithStatus(task, node, &api.Status{Code: api.UnschedulableAndUnresolvable, Plugin: api.BlockerNodeAffinity, Reason: "node affinity does not match"})
				}
				return nil
			})

			New().Execute(ssn)

			job := ssn.Jobs["ns/peer"]
			assert.Len(t, job.TaskStatusIndex[api.Binding], tt.wantBinding)
			pending := make(map[api.TaskID]api.PendingTaskDiagnosticKind)
			for id, diagnostic := range job.PendingTaskDiagnostics {
				pending[id] = diagnostic.Kind
			}
			assert.Equal(t, tt.wantPending, pending)
			require.NotNil(t, job.GroupDiagnostic)
			assert.ElementsMatch(t, tt.wantBlockers, job.GroupDiagnostic.Blockers)
		})
	}
}
