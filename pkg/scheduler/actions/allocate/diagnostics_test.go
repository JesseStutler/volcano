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
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/utils/ptr"
	"sync/atomic"
	"testing"
	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/conf"
	"volcano.sh/volcano/pkg/scheduler/framework"
	networktopologyaware "volcano.sh/volcano/pkg/scheduler/plugins/network-topology-aware"
	"volcano.sh/volcano/pkg/scheduler/util"
)

func TestAllocatePublishesSelectedDiagnostics(t *testing.T) {
	for _, tc := range []struct {
		name                                    string
		secondFits, screenFirst, partialSuccess bool
	}{
		{name: "failed candidate followed by successful candidate", secondFits: true},
		{name: "affinity fails across both permitted domains"},
		{name: "capacity screen plus scoped affinity failure", screenFirst: true},
		{name: "ready group with a failed member", partialSuccess: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
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
			pg := util.BuildPodGroupWithNetWorkTopologies("peer", "ns", "", "q", 3, nil, schedulingv1beta1.PodGroupInqueue, "hard", 1)
			if tc.partialSuccess {
				pg.Spec.MinMember = 1
			}
			if tc.screenFirst {
				resources := api.BuildResourceList("3", "3Mi")
				pg.Spec.MinResources = &resources
				require.NoError(t, sc.AddOrUpdateNode(util.BuildNode("node-0", api.BuildResourceList("1", "4Gi", api.ScalarResource{Name: "pods", Value: "2000"}), nil)))
			}
			sc.AddPodGroupV1beta1(pg)
			framework.RegisterPluginBuilder(networktopologyaware.PluginName, networktopologyaware.New)
			registerDryRunTestPlugins()
			tiers[0].Plugins = append(tiers[0].Plugins,
				conf.PluginOption{Name: networktopologyaware.PluginName, EnabledHyperNodeGradient: ptr.To(true), EnabledHyperNodeOrder: ptr.To(true)},
				conf.PluginOption{Name: dryRunTestPlugin, EnabledPredicate: ptr.To(true), EnabledTaskOrder: ptr.To(true)})
			ssn := framework.OpenSession(sc, tiers, nil)
			defer framework.CloseSession(ssn)
			ssn.AddTaskOrderFn(dryRunTestPlugin, func(l, r interface{}) int {
				a, b := l.(*api.TaskInfo).Name, r.(*api.TaskInfo).Name
				if a < b {
					return -1
				}
				if a > b {
					return 1
				}
				return 0
			})
			ssn.AddPredicateFn(dryRunTestPlugin, func(task *api.TaskInfo, node *api.NodeInfo) error {
				failingMember := "task-1"
				if tc.partialSuccess {
					failingMember = "task-0"
				}
				if task.Name == failingMember && (node.Name == "node-0" || !tc.secondFits) {
					return api.NewFitErrWithStatus(task, node, &api.Status{Code: api.UnschedulableAndUnresolvable, Plugin: "NodeAffinity", Reason: "node affinity does not match"})
				}
				return nil
			})
			New().Execute(ssn)
			job := ssn.Jobs["ns/peer"]
			require.NotNil(t, job.GroupDiagnostic)
			if tc.partialSuccess {
				assert.Len(t, job.TaskStatusIndex[api.Binding], 2)
				assert.Len(t, job.PendingTaskDiagnostics, 1)
				assert.Equal(t, api.PendingTaskFailure, job.PendingTaskDiagnostics["ns-task-0"].Kind)
				assert.Empty(t, job.GroupDiagnostic.Blockers)
				return
			}
			if tc.secondFits {
				assert.Len(t, job.TaskStatusIndex[api.Binding], 3)
				assert.Empty(t, job.PendingTaskDiagnostics)
				assert.Empty(t, job.GroupDiagnostic.Blockers)
				return
			}
			assert.Len(t, job.TaskStatusIndex[api.Pending], 3)
			assert.Equal(t, api.PendingGangWaiting, job.PendingTaskDiagnostics["ns-task-0"].Kind)
			assert.Equal(t, api.PendingGangWaiting, job.PendingTaskDiagnostics["ns-task-2"].Kind)
			if tc.screenFirst {
				assert.Equal(t, api.PendingGangWaiting, job.PendingTaskDiagnostics["ns-task-1"].Kind)
				assert.Contains(t, job.GroupSchedulingMessage(), "HyperNode h1 has insufficient cpu capacity")
			} else {
				assert.Equal(t, api.PendingTaskFailure, job.PendingTaskDiagnostics["ns-task-1"].Kind)
				assert.Contains(t, job.TaskSchedulingCondition(job.Tasks["ns-task-1"]).Message, "0/2 nodes")
			}
			assert.Contains(t, job.GroupSchedulingMessage(), "Pod ns/task-1 has no node satisfying node affinity")
			assert.NotContains(t, job.TaskSchedulingCondition(job.Tasks["ns-task-0"]).Message, "node-")
		})
	}
}
