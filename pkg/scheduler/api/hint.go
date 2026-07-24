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

package api

import (
	"context"

	"k8s.io/klog/v2"
	fwk "k8s.io/kube-scheduler/framework"
)

// Volcano-specific event resources that are not part of the kube-scheduler
// framework resource set.
const (
	PodGroupEvent  fwk.EventResource = "PodGroup"
	QueueEvent     fwk.EventResource = "Queue"
	HyperNodeEvent fwk.EventResource = "HyperNode"
	NumaInfoEvent  fwk.EventResource = "NumaInfo"
)

// ClusterEvent identifies one category of cluster change a plugin subscribes to.
// Resource is the object type whose change may affect scheduling and ActionType
// names the kind of change.
type ClusterEvent struct {
	Resource   fwk.EventResource
	ActionType fwk.ActionType
}

// HintResult is the decision a JobHintFn returns for one Job on one event.
type HintResult int

const (
	// HintSkip means the event cannot unblock this Job; keep it cached.
	HintSkip HintResult = iota
	// HintWakeup means the event may unblock this Job; drop the record.
	HintWakeup
)

// JobHintFn is invoked when a subscribed cluster event fires for a Job that the
// plugin previously rejected. It reports whether this event may make the Job
// schedulable.
//
//	logger    logger scoped to this hint invocation.
//	job       the cached Job under evaluation.
//	rejection the plugin's own rejection from the previous session; for predicate
//	          sources it also carries the task IDs that failed.
//	oldObj    object state before the change; nil on Add events.
//	newObj    object state after the change; nil on Delete events.
//
// A non-nil error is treated as HintWakeup by the caller.
type JobHintFn func(
	logger klog.Logger,
	job *JobInfo,
	rejection Rejection,
	oldObj, newObj any,
) (HintResult, error)

// ClusterEventWithHint pairs one cluster event a plugin cares about with the
// callback used to check whether that event may help a specific Job. A nil HintFn
// means every occurrence of Event wakes Jobs blocked by this plugin.
type ClusterEventWithHint struct {
	Event  ClusterEvent
	HintFn JobHintFn
}

// HintProvider lets a plugin declare the events that can change its previous
// unschedulable decisions.
type HintProvider interface {
	// EventsToRegister returns every (event, hint) pair this plugin subscribes to.
	EventsToRegister(ctx context.Context) ([]ClusterEventWithHint, error)
}

// RejectionSource names the extension point that emitted a rejection.
type RejectionSource string

const (
	// RejectionPredicate comes from PredicateFn / PrePredicateFn, including
	// allocate's inline node-fit check (attributed to predicates/noderesources).
	RejectionPredicate RejectionSource = "predicate"
	// RejectionAllocatable comes from the Allocatable extension point.
	RejectionAllocatable RejectionSource = "allocatable"
	// RejectionEnqueue comes from the JobEnqueueable extension point.
	RejectionEnqueue RejectionSource = "enqueue"
)

// Rejection describes one plugin decision that made a Job unschedulable in a session.
type Rejection struct {
	// Plugin is the registered HintProvider name, e.g. "predicates/nodeaffinity".
	Plugin string
	// Source is the extension point that emitted the rejection.
	Source RejectionSource
	// Tasks holds the failed task IDs; nil only for RejectionEnqueue, which is
	// a whole-PodGroup decision.
	Tasks []TaskID
}

// SkipDecision names the work an action should skip for a pending Job this
// session, derived from the cached rejections and the Job's gang topology.
type SkipDecision struct {
	// Enqueue skips enqueue's JobEnqueueable re-check for this Job.
	Enqueue bool

	// Allocate skips the allocate and backfill actions entirely for this Job.
	Allocate bool

	// Tasks lists task IDs that allocate and backfill should treat as
	// unschedulable this session. Consulted only when Allocate is false.
	Tasks map[TaskID]struct{}
}

// SkipTask reports whether the given task should be treated as unschedulable this
// session because of cached per-task rejections.
func (d SkipDecision) SkipTask(taskID TaskID) bool {
	if d.Allocate {
		return true
	}
	_, ok := d.Tasks[taskID]
	return ok
}

// ComputeSkip turns the cached rejections into a SkipDecision for the Job. The
// RejectionEnqueue source sets Enqueue; per-task sources set Allocate when the
// Job can no longer reach its gang criterion, otherwise they list the tasks to
// skip.
func ComputeSkip(job *JobInfo, rejections []Rejection) SkipDecision {
	var d SkipDecision
	tasks := map[TaskID]struct{}{}
	for _, r := range rejections {
		if r.Source == RejectionEnqueue {
			d.Enqueue = true
			continue
		}
		for _, t := range r.Tasks {
			tasks[t] = struct{}{}
		}
	}
	if len(tasks) == 0 {
		return d
	}
	if !canReach(job, tasks) {
		d.Allocate = true
		return d
	}
	d.Tasks = tasks
	return d
}

// canReach reports whether job can still reach its gang criteria after excluding
// the skipped tasks. It checks the job-level MinAvailable, the per-role
// TaskMinAvailable (when enforced), and the per-subgroup MinSubJobs for
// network-topology jobs.
func canReach(job *JobInfo, skipped map[TaskID]struct{}) bool {
	total := int32(0)
	perRole := map[string]int32{}
	for status, tasks := range job.TaskStatusIndex {
		if !viableStatus(status) {
			continue
		}
		for _, t := range tasks {
			if status == Pending {
				if _, s := skipped[t.UID]; s {
					continue
				}
			}
			total++
			perRole[t.TaskRole]++
		}
	}

	// Job-level gang minMember.
	if total < job.MinAvailable {
		return false
	}

	// Per-role minAvailable, gated the same way as CheckTaskValid.
	if job.MinAvailable >= job.TaskMinAvailableTotal {
		for role, min := range job.TaskMinAvailable {
			if min == 0 {
				continue
			}
			if perRole[role] < min {
				return false
			}
		}
	}

	// Per-subgroup minSubGroups for network-topology jobs.
	if len(job.MinSubJobs) > 0 {
		viableSub := map[SubJobGID]int32{}
		for _, sj := range job.SubJobs {
			cnt := int32(0)
			for status, tasks := range sj.TaskStatusIndex {
				if !viableStatus(status) {
					continue
				}
				for _, t := range tasks {
					if status == Pending {
						if _, s := skipped[t.UID]; s {
							continue
						}
					}
					cnt++
				}
			}
			if cnt >= sj.MinAvailable {
				viableSub[sj.GID]++
			}
		}
		for gid, min := range job.MinSubJobs {
			if viableSub[gid] < min {
				return false
			}
		}
	}

	return true
}

// viableStatus reports whether a task in the given status could still contribute
// to gang readiness: it is either already occupying resources or pending.
func viableStatus(status TaskStatus) bool {
	return AllocatedStatus(status) || status == Succeeded || status == Pipelined || status == Pending
}
