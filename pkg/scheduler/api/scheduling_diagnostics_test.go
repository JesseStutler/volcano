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

package api

import (
	"errors"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// nodeStatuses builds the fit errors of a task from the status that rejected it on each node.
func nodeStatuses(statuses map[string]*Status) *FitErrors {
	fitErrors := NewFitErrors()
	for node, status := range statuses {
		fitErrors.SetNodeError(node, &FitError{Status: StatusSets{status}})
	}
	return fitErrors
}

func TestTaskSchedulingCondition(t *testing.T) {
	const (
		gangWaiting     = "Waiting for PodGroup ns/job to satisfy gang requirements."
		resourceWaiting = "Waiting for resources to be released for this Pod."
		affinityFailure = "No eligible node satisfies this Pod's node affinity."
	)
	affinity := &Status{Plugin: BlockerNodeAffinity, Reason: nodeAffinity}
	cpu := &Status{Plugin: "predicates-resource-fit", Reason: "Insufficient cpu", InsufficientResources: []string{"cpu"}}
	volume := &Status{Plugin: "VolumeBinding", Reason: "node(s) had volume node affinity conflict"}
	unscheduled := func(reason, message string) *v1.PodCondition {
		return &v1.PodCondition{Type: v1.PodScheduled, Status: v1.ConditionFalse, Reason: reason, Message: message}
	}

	tests := []struct {
		name       string
		status     TaskStatus
		gated      bool
		diagnostic *PendingTaskDiagnostic
		// want is nil when the condition observed through the informer is kept.
		want *v1.PodCondition
	}{
		{
			name:   "pending member without a record",
			status: Pending,
		},
		{
			name:       "member waiting for the gang",
			status:     Pending,
			diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting},
			want:       unscheduled(PodReasonUnschedulable, gangWaiting),
		},
		{
			name:   "own fit error names its category",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable,
				Failure: nodeStatuses(map[string]*Status{"n1": affinity}),
			},
			want: unscheduled(PodReasonUnschedulable, affinityFailure),
		},
		{
			name:   "more nodes with the same failure keep the message",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable,
				Failure: nodeStatuses(map[string]*Status{"n1": affinity, "n2": affinity, "n3": affinity}),
			},
			want: unscheduled(PodReasonUnschedulable, affinityFailure),
		},
		{
			name:   "failure categories are sorted",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable,
				Failure: nodeStatuses(map[string]*Status{"n1": affinity, "n2": cpu}),
			},
			want: unscheduled(PodReasonUnschedulable, "No eligible node satisfies this Pod's cpu request and node affinity."),
		},
		{
			name:   "unclassified predicate",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable,
				Failure: nodeStatuses(map[string]*Status{"n1": volume}),
			},
			want: unscheduled(PodReasonUnschedulable, "No eligible node satisfies this Pod's scheduling predicates."),
		},
		{
			name:   "explicit failure keeps its text",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable,
				Failure: errors.New("Queue q has insufficient resources for this Pod."),
			},
			want: unscheduled(PodReasonUnschedulable, "Queue q has insufficient resources for this Pod."),
		},
		{
			name:   "scheduler error on a pending member",
			status: Pending,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonSchedulerError, Failure: errors.New("binding failed"),
			},
			want: unscheduled(PodReasonSchedulerError, "binding failed"),
		},
		{
			name:   "scheduler error on an allocated member",
			status: Allocated,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonSchedulerError, Failure: errors.New("binding failed"),
			},
			want: unscheduled(PodReasonSchedulerError, "binding failed"),
		},
		{
			name:   "retained allocation waits for the gang",
			status: Allocated,
			want:   unscheduled(PodReasonSchedulable, gangWaiting),
		},
		{
			name:   "retained pipeline supersedes an earlier failure",
			status: Pipelined,
			diagnostic: &PendingTaskDiagnostic{
				Kind: PendingTaskFailure, Reason: PodReasonUnschedulable, Failure: errors.New("old failure"),
			},
			want: unscheduled(PodReasonUnschedulable, resourceWaiting),
		},
		{
			name:       "member handed to binding",
			status:     Binding,
			diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting},
		},
		{
			name:       "scheduling-gated member",
			status:     Pending,
			gated:      true,
			diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			task := NewTaskInfo(&v1.Pod{ObjectMeta: metav1.ObjectMeta{UID: "a", Name: "a", Namespace: "ns"}})
			task.Status, task.SchGated = tt.status, tt.gated
			// A rolled-back trial placement must not reach the condition.
			task.LastTransaction = &TransactionContext{NodeName: "trial-node", Status: Allocated}
			job := NewJobInfo("ns/job", task)
			job.Namespace, job.Name = "ns", "job"
			if tt.diagnostic != nil {
				job.SetPendingTaskDiagnostic(task.UID, *tt.diagnostic)
			}

			assert.Equal(t, tt.want, job.TaskSchedulingCondition(task))
		})
	}
}

// Tasks of one role share the working fit errors, and a later candidate
// overwrites them. A recorded failure must keep what it was recorded with.
func TestRecordPendingTaskFailure(t *testing.T) {
	working := nodeStatuses(map[string]*Status{
		"n1": {Plugin: BlockerNodeAffinity, Reason: nodeAffinity},
	})
	job := NewJobInfo("ns/job")
	job.RecordPendingTaskFailure("a", PodReasonUnschedulable, working)
	job.RecordPendingTaskFailure("b", PodReasonUnschedulable, working)

	insufficientCPU := &Status{Plugin: "predicates-resource-fit", Reason: "Insufficient cpu", InsufficientResources: []string{"cpu"}}
	working.SetNodeError("n1", &FitError{Status: StatusSets{insufficientCPU}})
	working.SetNodeError("n2", &FitError{Status: StatusSets{insufficientCPU}})

	for _, id := range []TaskID{"a", "b"} {
		recorded, found := job.PendingTaskDiagnostics[id]
		require.True(t, found)
		assert.Equal(t, PendingTaskFailure, recorded.Kind)
		assert.Equal(t, PodReasonUnschedulable, recorded.Reason)
		assert.Equal(t, "0/1 nodes are unavailable: 1 node(s) didn't match Pod's node affinity/selector.", recorded.Failure.Error())
	}
}

// Diagnostics belong to one session. The snapshot of the next session starts without them.
func TestJobInfoCloneResetsDiagnostics(t *testing.T) {
	job := NewJobInfo("ns/job")
	job.SetPendingTaskDiagnostic("a", PendingTaskDiagnostic{Kind: PendingGangWaiting})
	job.GroupDiagnostic = &GroupSchedulingDiagnostic{
		Blockers: []SchedulingBlocker{{Scope: MemberScope, Reason: BlockerNodeAffinity, TaskID: "a"}},
	}

	next := job.Clone()

	assert.Nil(t, next.PendingTaskDiagnostics)
	assert.Nil(t, next.GroupDiagnostic)
}

func TestGroupSchedulingMessage(t *testing.T) {
	const (
		gpu = v1.ResourceName("nvidia.com/gpu")
		// searchedRacks exceeds any realistic message budget if the racks were listed.
		searchedRacks = 100

		searchedMessage    = "Gang requirements are not satisfied. Insufficient HyperNode nvidia.com/gpu capacity. Pod ns/a has no node satisfying node affinity within the checked HyperNodes."
		establishedMessage = "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity within HyperNode zone."
	)
	task := NewTaskInfo(&v1.Pod{ObjectMeta: metav1.ObjectMeta{UID: "a", Name: "a", Namespace: "ns"}})
	// affinity is the member blocker found in hyperNode, inside the established placement if any.
	affinity := func(hyperNode, placement string) SchedulingBlocker {
		return SchedulingBlocker{Scope: MemberScope, Reason: BlockerNodeAffinity, TaskID: task.UID, HyperNodeName: hyperNode, PlacementDomain: placement}
	}
	capacity := func(hyperNode string) SchedulingBlocker {
		return SchedulingBlocker{Scope: HyperNodeScope, Reason: BlockerInsufficientResources, ResourceName: gpu, HyperNodeName: hyperNode}
	}
	manyRacks := []SchedulingBlocker{capacity("rack-0")}
	for i := 1; i <= searchedRacks; i++ {
		manyRacks = append(manyRacks, affinity(fmt.Sprintf("rack-%d", i), ""))
	}

	tests := []struct {
		name     string
		blockers []SchedulingBlocker
		want     string
	}{
		{
			name: "no blocker recorded",
			want: "Gang requirements are not satisfied.",
		},
		{
			name:     "member failure without HyperNodes",
			blockers: []SchedulingBlocker{affinity("", "")},
			want:     "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity.",
		},
		{
			name:     "candidate HyperNodes are not listed",
			blockers: []SchedulingBlocker{affinity("h1", ""), affinity("h2", ""), capacity("h0")},
			want:     searchedMessage,
		},
		{
			name:     "another failed HyperNode and a different order keep the message",
			blockers: []SchedulingBlocker{capacity("h3"), affinity("h2", ""), capacity("h0"), affinity("h4", ""), affinity("h1", "")},
			want:     searchedMessage,
		},
		{
			name:     "many candidate HyperNodes with the same blockers",
			blockers: manyRacks,
			want:     searchedMessage,
		},
		{
			name:     "established placement names the enclosing HyperNode",
			blockers: []SchedulingBlocker{affinity("rack-a", "zone"), affinity("rack-b", "zone")},
			want:     establishedMessage,
		},
		{
			name:     "a check outside the established placement names no HyperNode",
			blockers: []SchedulingBlocker{affinity("rack-a", "zone"), affinity("other", "")},
			want:     "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity within the checked HyperNodes.",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			job := NewJobInfo("ns/job", task)
			job.GroupDiagnostic = &GroupSchedulingDiagnostic{Blockers: tt.blockers}

			assert.Equal(t, tt.want, job.GroupSchedulingMessage())
		})
	}
}
