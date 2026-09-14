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

package framework

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/unschedulable"
)

func newRejectionTestSession(enabled bool) *Session {
	ssn := &Session{unschedulableJobCacheEnabled: enabled}
	if enabled {
		ssn.jobRejections = make(map[api.JobID]map[rejectionKey]*rejectionAggregate)
	}
	return ssn
}

func TestAddRejectionDeduplicatesTasks(t *testing.T) {
	ssn := newRejectionTestSession(true)

	ssn.AddRejection("job", "plugin-a", unschedulable.RejectionPredicate, "task-a", "task-a")
	ssn.AddRejection("job", "plugin-a", unschedulable.RejectionPredicate, "task-b", "task-a")
	ssn.AddRejection("job", "plugin-a", unschedulable.RejectionAllocatable, "task-a")
	ssn.AddRejection("job", "plugin-b", unschedulable.RejectionPredicate, "task-a")

	assert.ElementsMatch(t, []unschedulable.Rejection{
		{Plugin: "plugin-a", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-a", "task-b"}},
		{Plugin: "plugin-a", Source: unschedulable.RejectionAllocatable, Tasks: []api.TaskID{"task-a"}},
		{Plugin: "plugin-b", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-a"}},
	}, ssn.rejectionsForJob("job"))
}

func TestAddRejectionEnqueueLeavesNilTasksWhenUnspecified(t *testing.T) {
	ssn := newRejectionTestSession(true)

	ssn.AddRejection("job", "plugin", unschedulable.RejectionEnqueue)

	got := ssn.rejectionsForJob("job")
	if assert.Len(t, got, 1) {
		assert.Nil(t, got[0].Tasks)
	}
}

func TestAddRejectionWithKeys(t *testing.T) {
	ssn := newRejectionTestSession(true)
	ssn.AddRejectionWithKeys("job", "plugin", unschedulable.RejectionPredicate,
		[]unschedulable.HintKey{"node-a/cpu", "node-a/cpu"}, "task-a")
	ssn.AddRejectionWithKeys("job", "plugin", unschedulable.RejectionPredicate,
		[]unschedulable.HintKey{"node-b/memory"}, "task-b")

	got := ssn.rejectionsForJob("job")
	if assert.Len(t, got, 1) {
		assert.ElementsMatch(t, []api.TaskID{"task-a", "task-b"}, got[0].Tasks)
		assert.ElementsMatch(t, []unschedulable.HintKey{"node-a/cpu", "node-b/memory"}, got[0].HintKeys)
	}
}

func TestAddRejectionWithKeysFallsBackOnNilKeys(t *testing.T) {
	ssn := newRejectionTestSession(true)
	ssn.AddRejectionWithKeys("job", "plugin", unschedulable.RejectionPredicate,
		[]unschedulable.HintKey{"node-a/cpu"}, "task-a")
	ssn.AddRejectionWithKeys("job", "plugin", unschedulable.RejectionPredicate, nil, "task-b")

	got := ssn.rejectionsForJob("job")
	if assert.Len(t, got, 1) {
		assert.ElementsMatch(t, []api.TaskID{"task-a", "task-b"}, got[0].Tasks)
		assert.Nil(t, got[0].HintKeys)
	}
}

func TestAddRejectionWithKeysOverLimitFallsBack(t *testing.T) {
	ssn := newRejectionTestSession(true)
	keys := make([]unschedulable.HintKey, 0, unschedulable.MaxHintKeysPerPluginEvent+1)
	for i := range unschedulable.MaxHintKeysPerPluginEvent + 1 {
		keys = append(keys, unschedulable.HintKey(fmt.Sprintf("node-%03d/cpu", i)))
	}

	for i, key := range keys {
		ssn.AddRejectionWithKeys("job", "plugin", unschedulable.RejectionPredicate, []unschedulable.HintKey{key}, api.TaskID(fmt.Sprintf("task-%03d", i)))
	}

	got := ssn.rejectionsForJob("job")
	if assert.Len(t, got, 1) {
		assert.Len(t, got[0].Tasks, len(keys))
		assert.Nil(t, got[0].HintKeys)
	}
}

func TestCollectJobRejections(t *testing.T) {
	tests := []struct {
		name             string
		cacheEnabled     bool
		before           []unschedulable.Rejection
		during           []unschedulable.Rejection
		wantCollected    []unschedulable.Rejection
		wantRemaining    []unschedulable.Rejection
		wantCallbackRuns bool
	}{
		{
			name:             "collects rejections recorded by the callback",
			cacheEnabled:     true,
			wantCallbackRuns: true,
			during: []unschedulable.Rejection{
				{Plugin: "trial", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-b"}},
			},
			wantCollected: []unschedulable.Rejection{
				{Plugin: "trial", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-b"}},
			},
		},
		{
			name:             "keeps existing rejections outside the callback",
			cacheEnabled:     true,
			wantCallbackRuns: true,
			before: []unschedulable.Rejection{
				{Plugin: "existing", Source: unschedulable.RejectionAllocatable, Tasks: []api.TaskID{"task-a"}},
			},
			during: []unschedulable.Rejection{
				{Plugin: "trial", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-b"}},
			},
			wantCollected: []unschedulable.Rejection{
				{Plugin: "trial", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-b"}},
			},
			wantRemaining: []unschedulable.Rejection{
				{Plugin: "existing", Source: unschedulable.RejectionAllocatable, Tasks: []api.TaskID{"task-a"}},
			},
		},
		{
			name:             "runs callback without collecting when cache is disabled",
			wantCallbackRuns: true,
			during: []unschedulable.Rejection{
				{Plugin: "trial", Source: unschedulable.RejectionPredicate, Tasks: []api.TaskID{"task-b"}},
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			ssn := newRejectionTestSession(test.cacheEnabled)
			for _, rejection := range test.before {
				ssn.AddRejectionWithKeys("job", rejection.Plugin, rejection.Source, rejection.HintKeys, rejection.Tasks...)
			}

			callbackRuns := false
			collected := ssn.CollectJobRejections("job", func() {
				callbackRuns = true
				for _, rejection := range test.during {
					ssn.AddRejectionWithKeys("job", rejection.Plugin, rejection.Source, rejection.HintKeys, rejection.Tasks...)
				}
			})

			assert.Equal(t, test.wantCallbackRuns, callbackRuns)
			assert.Equal(t, test.wantCollected, collected)
			assert.Equal(t, test.wantRemaining, ssn.rejectionsForJob("job"))
		})
	}
}
