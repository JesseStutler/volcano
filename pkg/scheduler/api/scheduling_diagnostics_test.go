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
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"testing"
)

func TestTaskSchedulingCondition(t *testing.T) {
	for _, tc := range []struct {
		name                    string
		status                  TaskStatus
		diagnostic              *PendingTaskDiagnostic
		gated                   bool
		wantReason, wantMessage string
	}{
		{name: "skipped pending preserves status", status: Pending},
		{name: "rollback", status: Pending, diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting}, wantReason: PodReasonUnschedulable, wantMessage: "Waiting for PodGroup ns/job to satisfy gang requirements."},
		{name: "individual error", status: Pending, diagnostic: &PendingTaskDiagnostic{Kind: PendingTaskFailure, Reason: PodReasonUnschedulable, Failure: errors.New("affinity failed")}, wantReason: PodReasonUnschedulable, wantMessage: "affinity failed"},
		{name: "scheduler error", status: Pending, diagnostic: &PendingTaskDiagnostic{Kind: PendingTaskFailure, Reason: PodReasonSchedulerError, Failure: errors.New("binding failed")}, wantReason: PodReasonSchedulerError, wantMessage: "binding failed"},
		{name: "pipeline supersedes failure", status: Pipelined, diagnostic: &PendingTaskDiagnostic{Kind: PendingTaskFailure, Reason: PodReasonUnschedulable, Failure: errors.New("old failure")}, wantReason: PodReasonUnschedulable, wantMessage: "Waiting for resources to be released for this Pod."},
		{name: "binding", status: Binding, diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting}},
		{name: "gated", status: Pending, gated: true, diagnostic: &PendingTaskDiagnostic{Kind: PendingGangWaiting}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			task := NewTaskInfo(&v1.Pod{ObjectMeta: metav1.ObjectMeta{UID: "a", Name: "a", Namespace: "ns"}})
			task.Status, task.SchGated = tc.status, tc.gated
			job := NewJobInfo("ns/job", task)
			job.Namespace, job.Name = "ns", "job"
			if tc.diagnostic != nil {
				job.SetPendingTaskDiagnostic(task.UID, *tc.diagnostic)
			}
			for _, node := range []string{"node-1", "node-2"} {
				task.LastTransaction = &TransactionContext{NodeName: node, Status: Allocated}
				condition := job.TaskSchedulingCondition(task)
				if tc.wantReason == "" {
					assert.Nil(t, condition)
					continue
				}
				require.NotNil(t, condition)
				assert.Equal(t, tc.wantReason, condition.Reason)
				assert.Equal(t, tc.wantMessage, condition.Message)
				assert.Equal(t, v1.ConditionFalse, condition.Status)
			}
		})
	}
}

func TestDiagnosticSnapshot(t *testing.T) {
	job := NewJobInfo("ns/job")
	source := NewFitErrors()
	source.SetNodeError("n1", &FitError{Status: StatusSets{&Status{Plugin: "NodeAffinity", Reason: "original", InsufficientResources: []string{"cpu"}}}})
	job.RecordPendingTaskFailure("a", PodReasonUnschedulable, source)
	snapshot := job.PendingTaskDiagnostics["a"].Failure.(*FitErrors)
	expected := snapshot.Error()
	source.nodes["n1"].Status[0].Reason = "changed"
	source.nodes["n1"].Status[0].InsufficientResources[0] = "memory"
	assert.Equal(t, expected, snapshot.Error())
	assert.Equal(t, []string{"cpu"}, snapshot.nodes["n1"].Status[0].InsufficientResources)
	assert.Empty(t, snapshot.err, "formatting must not mutate a shared snapshot")
	job.GroupDiagnostic = &GroupSchedulingDiagnostic{Blockers: []SchedulingBlocker{{Scope: MemberScope, Reason: "NodeAffinity", TaskID: "a"}}}
	next := job.Clone()
	assert.Nil(t, next.PendingTaskDiagnostics)
	assert.Nil(t, next.GroupDiagnostic)
}

func TestGroupSchedulingMessage(t *testing.T) {
	task := NewTaskInfo(&v1.Pod{ObjectMeta: metav1.ObjectMeta{UID: "a", Name: "a", Namespace: "ns"}})
	job := NewJobInfo("ns/job", task)
	a := SchedulingBlocker{Scope: MemberScope, Reason: "NodeAffinity", TaskID: task.UID, HyperNodeName: "h1"}
	b := a
	b.HyperNodeName = "h2"
	capacity := SchedulingBlocker{Scope: HyperNodeScope, Reason: "InsufficientResources", ResourceName: "nvidia.com/gpu", HyperNodeName: "h0"}
	for _, blockers := range [][]SchedulingBlocker{{a, b, capacity}, {capacity, b, a, a}} {
		job.GroupDiagnostic = &GroupSchedulingDiagnostic{Blockers: blockers}
		assert.Equal(t, "Gang requirements are not satisfied. HyperNode h0 has insufficient nvidia.com/gpu capacity. Pod ns/a has no node satisfying node affinity within HyperNodes h1, h2.", job.GroupSchedulingMessage())
	}
}
