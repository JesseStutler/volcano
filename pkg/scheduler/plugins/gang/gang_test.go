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
	"testing"

	v1 "k8s.io/api/core/v1"
	"k8s.io/client-go/tools/record"

	"volcano.sh/apis/pkg/apis/scheduling"
	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/util"
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

// A PodGroup keeps one active explanation. A ready group reports Scheduled, an
// unready group reports Unschedulable, and the other condition is retired.
func TestOnSessionClose(t *testing.T) {
	const (
		unsatisfied     = "Gang requirements are not satisfied."
		affinityBlocker = "Gang requirements are not satisfied. Pod ns/p has no node satisfying node affinity."
	)
	published := func(conditionType schedulingv1beta1.PodGroupConditionType, message string) []schedulingv1beta1.PodGroupCondition {
		return []schedulingv1beta1.PodGroupCondition{{Type: conditionType, Status: v1.ConditionTrue, Message: message}}
	}

	tests := []struct {
		name string
		// conditions are the PodGroup conditions published by an earlier session.
		conditions []schedulingv1beta1.PodGroupCondition
		// memberStatus is the status of the only member when the session closes.
		memberStatus api.TaskStatus
		wantActive   scheduling.PodGroupConditionType
		wantMessage  string
	}{
		{
			name:         "unready group is reported for the first time",
			memberStatus: api.Pending,
			wantActive:   scheduling.PodGroupUnschedulableType,
			wantMessage:  unsatisfied,
		},
		{
			name:         "unready group without a new result keeps its explanation",
			conditions:   published(schedulingv1beta1.PodGroupUnschedulableType, affinityBlocker),
			memberStatus: api.Pending,
			wantActive:   scheduling.PodGroupUnschedulableType,
			wantMessage:  affinityBlocker,
		},
		{
			name:         "ready group retires the unschedulable explanation",
			conditions:   published(schedulingv1beta1.PodGroupUnschedulableType, affinityBlocker),
			memberStatus: api.Binding,
			wantActive:   scheduling.PodGroupScheduled,
			wantMessage:  api.GroupReadyMessage,
		},
		{
			name:         "unready group retires the ready explanation",
			conditions:   published(schedulingv1beta1.PodGroupScheduled, api.GroupReadyMessage),
			memberStatus: api.Pending,
			wantActive:   scheduling.PodGroupUnschedulableType,
			wantMessage:  unsatisfied,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			podGroup := util.BuildPodGroup("job", "ns", "q", 1, nil, schedulingv1beta1.PodGroupInqueue)
			podGroup.Status.Conditions = tc.conditions
			pod := util.BuildPod("ns", "p", "", v1.PodPending, api.BuildResourceList("1", "1Mi"), "job", nil, nil)
			sc := cache.NewCustomMockSchedulerCache("volcano", nil, nil, &util.FakeStatusUpdater{}, nil, record.NewFakeRecorder(10))
			defer cache.ShutdownMockSchedulerCache(sc)
			sc.AddQueueV1beta1(util.BuildQueue("q", 1, nil))
			sc.AddPodGroupV1beta1(podGroup)
			sc.AddPod(pod)
			ssn := framework.OpenSession(sc, nil, nil)
			defer framework.CloseSession(ssn)
			member := api.NewTaskInfo(pod)
			job := ssn.Jobs[member.Job]
			job.UpdateTaskStatus(job.Tasks[member.UID], tc.memberStatus)

			New(nil).OnSessionClose(ssn)

			active := false
			for _, condition := range job.PodGroup.Status.Conditions {
				if condition.Type != tc.wantActive {
					if condition.Status != v1.ConditionFalse || condition.Message != "" {
						t.Errorf("condition %s = (%s, %q), want it retired", condition.Type, condition.Status, condition.Message)
					}
					continue
				}
				active = true
				if condition.Status != v1.ConditionTrue || condition.Message != tc.wantMessage {
					t.Errorf("condition %s = (%s, %q), want (%s, %q)", condition.Type, condition.Status, condition.Message, v1.ConditionTrue, tc.wantMessage)
				}
			}
			if !active {
				t.Errorf("condition %s was not published", tc.wantActive)
			}
		})
	}
}
