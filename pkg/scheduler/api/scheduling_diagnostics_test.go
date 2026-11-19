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
	affinity := func(domain string) SchedulingBlocker {
		return SchedulingBlocker{Scope: MemberScope, Reason: "NodeAffinity", TaskID: task.UID, HyperNodeName: domain}
	}
	capacity := func(domain string) SchedulingBlocker {
		return SchedulingBlocker{Scope: HyperNodeScope, Reason: "InsufficientResources", ResourceName: "nvidia.com/gpu", HyperNodeName: domain}
	}
	fixed := affinity("rack-a")
	fixed.PlacementDomain = "zone"
	sibling := affinity("rack-b")
	sibling.PlacementDomain = "zone"
	many := []SchedulingBlocker{capacity("rack-0")}
	for i := 0; i < 100; i++ {
		many = append(many, affinity(fmt.Sprintf("rack-%d", i)))
	}
	const searched = "Gang requirements are not satisfied. Insufficient HyperNode nvidia.com/gpu capacity. Pod ns/a has no node satisfying node affinity within the checked HyperNodes."
	for _, tc := range []struct {
		name     string
		blockers []SchedulingBlocker
		want     string
	}{
		{
			name:     "member failure without HyperNodes",
			blockers: []SchedulingBlocker{affinity("")},
			want:     "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity.",
		},
		{
			name:     "candidate HyperNodes are not listed",
			blockers: []SchedulingBlocker{affinity("h1"), affinity("h2"), capacity("h0")},
			want:     searched,
		},
		{
			name:     "another failed HyperNode and a different order keep the message",
			blockers: []SchedulingBlocker{capacity("h3"), affinity("h2"), capacity("h0"), affinity("h4"), affinity("h1")},
			want:     searched,
		},
		{
			name:     "many candidate domains with the same blockers",
			blockers: many,
			want:     searched,
		},
		{
			name:     "established placement identifies the enclosing constraint",
			blockers: []SchedulingBlocker{fixed, sibling},
			want:     "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity within HyperNode zone.",
		},
		{
			name:     "a check outside the fixed placement has a single combined explanation",
			blockers: []SchedulingBlocker{fixed, affinity("other")},
			want:     "Gang requirements are not satisfied. Pod ns/a has no node satisfying node affinity within the checked HyperNodes.",
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			job.GroupDiagnostic = &GroupSchedulingDiagnostic{Blockers: tc.blockers}
			assert.Equal(t, tc.want, job.GroupSchedulingMessage())
		})
	}
}

func TestTaskFailureMessage(t *testing.T) {
	affinity := &Status{Plugin: "NodeAffinity", Reason: "node(s) didn't match Pod's node affinity/selector"}
	cpu := &Status{Plugin: "resourcefit", Reason: "Insufficient cpu", InsufficientResources: []string{"cpu"}}
	fitErrors := func(nodes map[string]*Status) *FitErrors {
		fit := NewFitErrors()
		for name, status := range nodes {
			fit.SetNodeError(name, &FitError{Status: StatusSets{status}})
		}
		return fit
	}
	for _, tc := range []struct {
		name    string
		failure error
		want    string
	}{
		{
			name:    "one category",
			failure: fitErrors(map[string]*Status{"n1": affinity}),
			want:    "No eligible node satisfies this Pod's node affinity.",
		},
		{
			name:    "another node with the same failure keeps the message",
			failure: fitErrors(map[string]*Status{"n1": affinity, "n2": affinity, "n3": affinity}),
			want:    "No eligible node satisfies this Pod's node affinity.",
		},
		{
			name:    "categories are sorted",
			failure: fitErrors(map[string]*Status{"n1": affinity, "n2": cpu}),
			want:    "No eligible node satisfies this Pod's cpu request and node affinity.",
		},
		{
			name:    "unclassified predicate",
			failure: fitErrors(map[string]*Status{"n1": {Plugin: "VolumeBinding", Reason: "node(s) had volume node affinity conflict"}}),
			want:    "No eligible node satisfies this Pod's scheduling predicates.",
		},
		{
			name:    "explicit error keeps its text",
			failure: errors.New("Queue q has insufficient resources for this Pod."),
			want:    "Queue q has insufficient resources for this Pod.",
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			assert.Equal(t, tc.want, taskFailureMessage(tc.failure))
		})
	}
}
