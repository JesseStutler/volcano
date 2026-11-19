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
	v1 "k8s.io/api/core/v1"
	"k8s.io/klog/v2"
	"volcano.sh/apis/pkg/apis/scheduling"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/util"
)

// candidateDiagnostics travels with a candidate's statement and worksheet.
// It is retained before rollback clears the statement operations.
type candidateDiagnostics struct {
	taskFailures          map[api.TaskID]api.PendingTaskDiagnostic
	trialPlacementTaskIDs []api.TaskID
	gangSkippedTaskIDs    []api.TaskID
	blockers              map[api.SchedulingBlocker]struct{}
	// Scopes share the session node slices. Each member is checked against its own permitted domains.
	scopes map[api.TaskID]map[string][]*api.NodeInfo
	err    error
}

func newCandidateDiagnostics() *candidateDiagnostics {
	return &candidateDiagnostics{
		scopes:       make(map[api.TaskID]map[string][]*api.NodeInfo),
		taskFailures: make(map[api.TaskID]api.PendingTaskDiagnostic),
		blockers:     make(map[api.SchedulingBlocker]struct{}),
	}
}

func (d *candidateDiagnostics) recordFailure(task *api.TaskInfo, fit *api.FitErrors, domain string) {
	if fit == nil {
		return
	}
	klog.V(4).InfoS("Task has no feasible node in candidate", "task", klog.KRef(task.Namespace, task.Name), "hyperNode", domain, "fitErrors", fit)
	d.taskFailures[task.UID] = api.PendingTaskDiagnostic{Kind: api.PendingTaskFailure, Reason: api.PodReasonUnschedulable, Failure: fit.Clone()}
	if domain == framework.ClusterTopHyperNode {
		domain = ""
	}
	for _, blocker := range fit.SchedulingBlockers(task.UID, domain) {
		d.blockers[blocker] = struct{}{}
	}
}

func (d *candidateDiagnostics) merge(other *candidateDiagnostics) {
	if other == nil {
		return
	}
	for id, scopes := range other.scopes {
		if d.scopes[id] == nil {
			d.scopes[id] = make(map[string][]*api.NodeInfo)
		}
		for name, nodes := range scopes {
			d.scopes[id][name] = nodes
		}
	}
	d.trialPlacementTaskIDs = append(d.trialPlacementTaskIDs, other.trialPlacementTaskIDs...)
	d.gangSkippedTaskIDs = append(d.gangSkippedTaskIDs, other.gangSkippedTaskIDs...)
	for id, failure := range other.taskFailures {
		if old, ok := d.taskFailures[id]; ok {
			if oldFit, ok := old.Failure.(*api.FitErrors); ok {
				if newFit, ok := failure.Failure.(*api.FitErrors); ok {
					oldFit.Merge(newFit)
					d.taskFailures[id] = old
					continue
				}
			}
		}
		if fit, ok := failure.Failure.(*api.FitErrors); ok {
			failure.Failure = fit.Clone()
		}
		d.taskFailures[id] = failure
	}
	for blocker := range other.blockers {
		d.blockers[blocker] = struct{}{}
	}
	if other.err != nil {
		d.err = other.err
	}
}

func (d *candidateDiagnostics) recordStatement(stmt *framework.Statement) {
	if stmt == nil {
		return
	}
	for _, task := range stmt.PlacementTasks() {
		d.trialPlacementTaskIDs = append(d.trialPlacementTaskIDs, task.UID)
	}
}

// apply runs after the outer Job decision. A failed trial alone cannot establish
// an individual failure on nodes that were never checked for that Pod.
func (d *candidateDiagnostics) apply(ssn *framework.Session, job *api.JobInfo) {
	if d == nil {
		return
	}
	placed := make(map[api.TaskID]bool)
	affected := make(map[api.TaskID]struct{})
	for _, id := range d.trialPlacementTaskIDs {
		placed[id] = true
		affected[id] = struct{}{}
	}
	for _, id := range d.gangSkippedTaskIDs {
		affected[id] = struct{}{}
	}
	for id := range d.taskFailures {
		affected[id] = struct{}{}
	}
	if len(affected) == 0 && len(d.blockers) == 0 && d.err == nil {
		return
	}
	for id := range affected {
		task := job.Tasks[id]
		if task == nil || task.SchGated {
			continue
		}
		if failure, found := d.taskFailures[id]; found && failure.Reason == api.PodReasonSchedulerError && (task.Status == api.Pending || task.Status == api.Allocated) {
			job.SetPendingTaskDiagnostic(id, failure)
			continue
		}
		if task.Status != api.Pending {
			delete(job.PendingTaskDiagnostics, id)
			continue
		}
		// Commit/dispatch failures belong to the failing member, even if its trial fit.
		if prior, ok := job.PendingTaskDiagnostics[id]; ok && prior.Reason == api.PodReasonSchedulerError && placed[id] {
			continue
		}
		failure, failed := d.taskFailures[id]
		if _, isFit := failure.Failure.(*api.FitErrors); failed && !isFit {
			job.SetPendingTaskDiagnostic(id, failure)
			continue
		}
		if fit, ok := failure.Failure.(*api.FitErrors); failed && ok && !placed[id] && d.coversTask(id, fit) {
			job.SetPendingTaskDiagnostic(id, failure)
		} else if d.err == nil {
			job.SetPendingTaskDiagnostic(id, api.PendingTaskDiagnostic{Kind: api.PendingGangWaiting})
		}
	}
	if d.err != nil {
		return
	}
	job.GroupDiagnostic = &api.GroupSchedulingDiagnostic{}
	if !ssn.JobReady(job) && !ssn.JobPipelined(job) {
		for blocker := range d.blockers {
			// The PodGroup message leaves candidate HyperNode names out. Keep them here.
			klog.V(4).InfoS("Group scheduling blocker", "job", klog.KRef(job.Namespace, job.Name), "scope", blocker.Scope,
				"reason", blocker.Reason, "resource", blocker.ResourceName, "task", blocker.TaskID, "hyperNode", blocker.HyperNodeName)
			job.GroupDiagnostic.Blockers = append(job.GroupDiagnostic.Blockers, blocker)
		}
	}
}

func (d *candidateDiagnostics) screening(ssn *framework.Session, stats *api.HyperNodeGradientStats, resources *api.HyperNodeMinResourceFilterStats, minimum *api.Resource, queues ...*util.PriorityQueue) {
	if stats != nil {
		for name := range stats.ExcludedByReason {
			if name == framework.ClusterTopHyperNode {
				continue
			}
			for _, queue := range queues {
				d.includeScope(queue, name, ssn.RealNodesList[name])
			}
			d.blockers[api.SchedulingBlocker{Scope: api.HyperNodeScope, Reason: "PlacementRejected", HyperNodeName: name}] = struct{}{}
		}
	}
	if resources == nil || minimum == nil {
		return
	}
	for name := range resources.ExcludedByReason {
		for _, queue := range queues {
			d.includeScope(queue, name, ssn.RealNodesList[name])
		}
		available := api.EmptyResource()
		for _, node := range ssn.RealNodesList[name] {
			available.Add(node.FutureIdle())
		}
		_, dimensions := minimum.LessEqualWithResourcesName(available, api.Zero)
		if len(dimensions) == 0 {
			d.blockers[api.SchedulingBlocker{Scope: api.HyperNodeScope, Reason: "InsufficientResources", HyperNodeName: name}] = struct{}{}
		}
		for _, dimension := range dimensions {
			d.blockers[api.SchedulingBlocker{Scope: api.HyperNodeScope, Reason: "InsufficientResources", ResourceName: v1.ResourceName(dimension), HyperNodeName: name}] = struct{}{}
		}
	}
}

func (d *candidateDiagnostics) recordSkipped(job *api.JobInfo, tasks *util.PriorityQueue) {
	remaining := tasks.Clone()
	for !remaining.Empty() {
		task := remaining.Pop().(*api.TaskInfo)
		if !task.SchGated && !job.Skip.SkipTask(task.UID) {
			d.gangSkippedTaskIDs = append(d.gangSkippedTaskIDs, task.UID)
		}
	}
}

// includeScope also covers domains rejected before an individual Pod was checked.
// This prevents a failure in one domain from becoming a Pod-wide fit failure.
func (d *candidateDiagnostics) includeScope(tasks *util.PriorityQueue, domain string, nodes []*api.NodeInfo) {
	remaining := tasks.Clone()
	for !remaining.Empty() {
		task := remaining.Pop().(*api.TaskInfo)
		if task.SchGated {
			continue
		}
		if d.scopes[task.UID] == nil {
			d.scopes[task.UID] = make(map[string][]*api.NodeInfo)
		}
		d.scopes[task.UID][domain] = nodes
	}
}

func (d *candidateDiagnostics) coversTask(id api.TaskID, fit *api.FitErrors) bool {
	if len(d.scopes[id]) == 0 {
		return false
	}
	for _, nodes := range d.scopes[id] {
		if !fit.CoversNodes(nodes) {
			return false
		}
	}
	return true
}

// recordError retains an operational failure for members whose usable placements
// could not be selected or restored. It does not establish new group blockers.
func (d *candidateDiagnostics) recordError(err error) {
	d.err = err
	for _, id := range d.trialPlacementTaskIDs {
		d.taskFailures[id] = api.PendingTaskDiagnostic{Kind: api.PendingTaskFailure, Reason: api.PodReasonSchedulerError, Failure: err}
	}
}

func establishedDomain(ssn *framework.Session, placement string, topology *scheduling.NetworkTopologySpec) string {
	if placement == "" || topology == nil || topology.Mode != scheduling.HardNetworkTopologyMode || topology.HighestTierAllowed == nil {
		return ""
	}
	name, err := ssn.HyperNodes.HighestAllowedHyperNode(*topology.HighestTierAllowed, placement)
	if err != nil || name == framework.ClusterTopHyperNode {
		return ""
	}
	return name
}

// Ancestors are ordered finest first, so overlapping Job and SubJob
// constraints report the narrower established scope.
func (d *candidateDiagnostics) markEstablishedDomain(ssn *framework.Session, jobDomain, subJobDomain string) {
	if d == nil || (jobDomain == "" && subJobDomain == "") {
		return
	}
	for blocker := range d.blockers {
		if blocker.PlacementDomain != "" {
			continue
		}
		for _, name := range ssn.HyperNodeIndex().Ancestors(blocker.HyperNodeName) {
			if name == jobDomain || name == subJobDomain {
				delete(d.blockers, blocker)
				blocker.PlacementDomain = name
				d.blockers[blocker] = struct{}{}
				break
			}
		}
	}
}
