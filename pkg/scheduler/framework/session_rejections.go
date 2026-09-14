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
	"sort"

	"k8s.io/apimachinery/pkg/util/sets"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/unschedulable"
)

// rejectionKey identifies a rejection by the plugin and extension point that
// produced it, so repeated rejections for the same key merge their tasks.
type rejectionKey struct {
	plugin string
	source unschedulable.RejectionSource
}

// rejectionAggregate contains the tasks and hint keys recorded for one rejection key.
type rejectionAggregate struct {
	tasks    sets.Set[api.TaskID]
	hintKeys sets.Set[unschedulable.HintKey] // nil means coarse fallback
}

// AddRejection records, for the current session, that plugin made job
// unschedulable through the given source, optionally naming the failed tasks.
// Rejections are drained into the unschedulable-job cache at CloseSession.
func (ssn *Session) AddRejection(jobID api.JobID, plugin string, source unschedulable.RejectionSource, tasks ...api.TaskID) {
	ssn.AddRejectionWithKeys(jobID, plugin, source, nil, tasks...)
}

// AddRejectionWithKeys records, for the current session, that plugin made
// job unschedulable through the given source, optionally naming the failed
// tasks and the hint keys that were available for that rejection.
func (ssn *Session) AddRejectionWithKeys(jobID api.JobID, plugin string, source unschedulable.RejectionSource, hintKeys []unschedulable.HintKey, tasks ...api.TaskID) {
	if !ssn.unschedulableJobCacheEnabled {
		return
	}
	if ssn.jobRejections == nil {
		ssn.jobRejections = make(map[api.JobID]map[rejectionKey]*rejectionAggregate)
	}
	rejectionsByKey := ssn.jobRejections[jobID]
	if rejectionsByKey == nil {
		rejectionsByKey = make(map[rejectionKey]*rejectionAggregate)
		ssn.jobRejections[jobID] = rejectionsByKey
	}
	key := rejectionKey{plugin: plugin, source: source}
	aggregate, ok := rejectionsByKey[key]
	if !ok {
		aggregate = &rejectionAggregate{tasks: sets.New[api.TaskID]()}
		rejectionsByKey[key] = aggregate
	}
	aggregate.tasks.Insert(tasks...)

	if !ok {
		if len(hintKeys) == 0 {
			return
		}
		aggregate.hintKeys = sets.New[unschedulable.HintKey](hintKeys...)
		if aggregate.hintKeys.Len() > unschedulable.MaxHintKeysPerPluginEvent {
			aggregate.hintKeys = nil
		}
		return
	}

	if aggregate.hintKeys == nil || len(hintKeys) == 0 {
		aggregate.hintKeys = nil
		return
	}
	aggregate.hintKeys.Insert(hintKeys...)
	if aggregate.hintKeys.Len() > unschedulable.MaxHintKeysPerPluginEvent {
		aggregate.hintKeys = nil
	}
}

// rejectionsForJob returns the rejections accumulated for job this session.
func (ssn *Session) rejectionsForJob(jobID api.JobID) []unschedulable.Rejection {
	rejectionsByKey := ssn.jobRejections[jobID]
	if len(rejectionsByKey) == 0 {
		return nil
	}
	rejections := make([]unschedulable.Rejection, 0, len(rejectionsByKey))
	for key, aggregate := range rejectionsByKey {
		var taskIDs []api.TaskID
		if aggregate.tasks.Len() > 0 {
			taskIDs = sets.List(aggregate.tasks)
			sort.Slice(taskIDs, func(i, j int) bool { return taskIDs[i] < taskIDs[j] })
		}
		var hintKeys []unschedulable.HintKey
		if aggregate.hintKeys != nil {
			hintKeys = sets.List(aggregate.hintKeys)
			sort.Slice(hintKeys, func(i, j int) bool { return hintKeys[i] < hintKeys[j] })
		}
		rejections = append(rejections, unschedulable.Rejection{
			Plugin:   key.plugin,
			Source:   key.source,
			Tasks:    taskIDs,
			HintKeys: hintKeys,
		})
	}
	sort.Slice(rejections, func(i, j int) bool {
		if rejections[i].Plugin != rejections[j].Plugin {
			return rejections[i].Plugin < rejections[j].Plugin
		}
		return rejections[i].Source < rejections[j].Source
	})
	return rejections
}

// CollectJobRejections runs evaluate with an isolated rejection aggregate for
// jobID and returns only the rejections recorded during that evaluation.
// Rejections recorded before the call remain in the Session aggregate.
func (ssn *Session) CollectJobRejections(jobID api.JobID, evaluate func()) []unschedulable.Rejection {
	if !ssn.unschedulableJobCacheEnabled {
		evaluate()
		return nil
	}

	retainedRejections := ssn.jobRejections[jobID]
	// Detach existing rejections so AddRejection creates an isolated aggregate
	// for this evaluation.
	delete(ssn.jobRejections, jobID)

	evaluate()
	collectedRejections := ssn.rejectionsForJob(jobID)

	// Remove the evaluation's aggregate before restoring the retained one.
	delete(ssn.jobRejections, jobID)
	if retainedRejections != nil {
		ssn.jobRejections[jobID] = retainedRejections
	}
	return collectedRejections
}
