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

package gang

import (
	"github.com/stretchr/testify/assert"
	v1 "k8s.io/api/core/v1"
	"k8s.io/client-go/tools/record"
	"testing"
	"volcano.sh/apis/pkg/apis/scheduling"
	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/util"

	"volcano.sh/volcano/pkg/scheduler/api"
)

func TestShouldSkipUnschedulableForReleasing(t *testing.T) {
	newTask := func(uid string, status api.TaskStatus, nodeName string) *api.TaskInfo {
		return &api.TaskInfo{
			UID: api.TaskID(uid),
			TransactionContext: api.TransactionContext{
				Status:   status,
				NodeName: nodeName,
			},
			Resreq: api.EmptyResource(),
		}
	}

	tests := []struct {
		name     string
		min      int32
		tasks    []*api.TaskInfo
		expected bool
	}{
		{
			name: "partial termination",
			min:  2,
			tasks: []*api.TaskInfo{
				newTask("running", api.Running, "node-1"),
				newTask("releasing", api.Releasing, "node-2"),
			},
			expected: true,
		},
		{
			name: "pending replacement still needs condition",
			min:  2,
			tasks: []*api.TaskInfo{
				newTask("running", api.Running, "node-1"),
				newTask("releasing", api.Releasing, "node-2"),
				newTask("replacement", api.Pending, ""),
			},
		},
		{
			name: "pipelined replacement still needs condition",
			min:  2,
			tasks: []*api.TaskInfo{
				newTask("running", api.Running, "node-1"),
				newTask("releasing", api.Releasing, "node-2"),
				newTask("replacement", api.Pipelined, "node-3"),
			},
		},
		{
			name: "never scheduled releasing task is not counted",
			min:  1,
			tasks: []*api.TaskInfo{
				newTask("releasing", api.Releasing, ""),
			},
		},
		{
			name: "scheduled tasks below minAvailable",
			min:  3,
			tasks: []*api.TaskInfo{
				newTask("running", api.Running, "node-1"),
				newTask("releasing", api.Releasing, "node-2"),
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			job := api.NewJobInfo("job-1", tc.tasks...)
			job.MinAvailable = tc.min
			if got := shouldSkipUnschedulableForReleasing(job); got != tc.expected {
				t.Fatalf("shouldSkipUnschedulableForReleasing() = %v, want %v", got, tc.expected)
			}
		})
	}
}

func TestGroupExplanationFollowsReadiness(t *testing.T) {
	task := api.NewTaskInfo(util.BuildPod("ns", "p", "", v1.PodPending, api.BuildResourceList("1", "1Mi"), "job", nil, nil))
	sc := cache.NewCustomMockSchedulerCache("volcano", nil, nil, &util.FakeStatusUpdater{}, nil, record.NewFakeRecorder(10))
	defer cache.ShutdownMockSchedulerCache(sc)
	sc.AddQueueV1beta1(util.BuildQueue("q", 1, nil))
	sc.AddPodGroupV1beta1(util.BuildPodGroup("job", "ns", "q", 1, nil, schedulingv1beta1.PodGroupInqueue))
	sc.AddPod(task.Pod)
	ssn := framework.OpenSession(sc, nil, nil)
	defer framework.CloseSession(ssn)
	job := ssn.Jobs[task.Job]
	task = job.Tasks[task.UID]
	job.GroupDiagnostic = &api.GroupSchedulingDiagnostic{}
	plugin := New(nil)
	for _, tc := range []struct {
		name   string
		status api.TaskStatus
		active scheduling.PodGroupConditionType
	}{
		{"failed", api.Pending, scheduling.PodGroupUnschedulableType},
		{"binding", api.Binding, scheduling.PodGroupScheduled},
		{"failed again", api.Pending, scheduling.PodGroupUnschedulableType},
	} {
		t.Run(tc.name, func(t *testing.T) {
			job.UpdateTaskStatus(task, tc.status)
			plugin.OnSessionClose(ssn)
			for _, condition := range job.PodGroup.Status.Conditions {
				if condition.Type == tc.active {
					assert.Equal(t, v1.ConditionTrue, condition.Status)
					assert.NotEmpty(t, condition.Message)
				} else {
					assert.Equal(t, v1.ConditionFalse, condition.Status)
					assert.Empty(t, condition.Message)
				}
			}
		})
	}
}
