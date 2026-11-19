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
	"fmt"

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

// recordFailure keeps the fit errors of a member that found no node in this
// candidate, and the group blockers they stand for.
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

// recordQueueRejection explains a member that its queue cannot admit.
func (d *candidateDiagnostics) recordQueueRejection(task *api.TaskInfo, queue *api.QueueInfo) {
	d.taskFailures[task.UID] = api.PendingTaskDiagnostic{
		Kind: api.PendingTaskFailure, Reason: api.PodReasonUnschedulable,
		Failure: fmt.Errorf("Queue %s has insufficient resources for this Pod.", queue.Name),
	}
}

// recordTaskError keeps an operational failure with the member that hit it.
func (d *candidateDiagnostics) recordTaskError(id api.TaskID, err error) {
	d.taskFailures[id] = api.PendingTaskDiagnostic{Kind: api.PendingTaskFailure, Reason: api.PodReasonSchedulerError, Failure: err}
}

// abort stops the candidate on an operational failure of one member. Such a
// failure establishes no group blocker.
func (d *candidateDiagnostics) abort(id api.TaskID, err error) {
	d.recordTaskError(id, err)
	d.err = err
}

// recordTrialPlacement remembers a member placed by this candidate. Its ID
// must survive the rollback that clears the statement.
func (d *candidateDiagnostics) recordTrialPlacement(id api.TaskID) {
	d.trialPlacementTaskIDs = append(d.trialPlacementTaskIDs, id)
}

// recordStatement remembers every member placed by a restored statement.
func (d *candidateDiagnostics) recordStatement(stmt *framework.Statement) {
	if stmt == nil {
		return
	}
	for _, task := range stmt.PlacementTasks() {
		d.recordTrialPlacement(task.UID)
	}
}

// recordHyperNodeBlocker notes that a HyperNode was rejected as a whole.
func (d *candidateDiagnostics) recordHyperNodeBlocker(reason string, resource v1.ResourceName, hyperNode string) {
	d.blockers[api.SchedulingBlocker{Scope: api.HyperNodeScope, Reason: reason, ResourceName: resource, HyperNodeName: hyperNode}] = struct{}{}
}

// merge adds the results of another candidate, or of a SubJob within this one.
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
		d.mergeTaskFailure(id, failure)
	}
	for blocker := range other.blockers {
		d.blockers[blocker] = struct{}{}
	}
	if other.err != nil {
		d.err = other.err
	}
}

// mergeTaskFailure combines the fit errors found for one member in different
// candidates. Any other failure replaces the earlier one.
func (d *candidateDiagnostics) mergeTaskFailure(id api.TaskID, failure api.PendingTaskDiagnostic) {
	fit, isFit := failure.Failure.(*api.FitErrors)
	if !isFit {
		d.taskFailures[id] = failure
		return
	}
	if existing, ok := d.taskFailures[id].Failure.(*api.FitErrors); ok {
		existing.Merge(fit)
		return
	}
	failure.Failure = fit.Clone()
	d.taskFailures[id] = failure
}

// failSelection ends a search whose usable candidates could not be selected or restored.
func (d *candidateDiagnostics) failSelection(candidates map[string]*candidateDiagnostics, err error) *candidateDiagnostics {
	for _, candidate := range candidates {
		d.merge(candidate)
	}
	d.recordError(err)
	return d
}

// apply runs after the outer Job decision. A failed trial alone cannot establish
// an individual failure on nodes that were never checked for that Pod.
func (d *candidateDiagnostics) apply(ssn *framework.Session, job *api.JobInfo) {
	if d == nil {
		return
	}
	affected := d.affectedTasks()
	if len(affected) == 0 && len(d.blockers) == 0 && d.err == nil {
		return
	}
	for id, placed := range affected {
		d.applyTask(job, id, placed)
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

// affectedTasks lists the members this result can explain, and whether the
// candidate placed each of them.
func (d *candidateDiagnostics) affectedTasks() map[api.TaskID]bool {
	affected := make(map[api.TaskID]bool)
	for _, id := range d.gangSkippedTaskIDs {
		affected[id] = false
	}
	for id := range d.taskFailures {
		affected[id] = false
	}
	for _, id := range d.trialPlacementTaskIDs {
		affected[id] = true
	}
	return affected
}

// applyTask writes the Pending record of one member.
func (d *candidateDiagnostics) applyTask(job *api.JobInfo, id api.TaskID, placed bool) {
	task := job.Tasks[id]
	if task == nil || task.SchGated {
		return
	}
	failure, failed := d.taskFailures[id]
	if failed && failure.Reason == api.PodReasonSchedulerError && (task.Status == api.Pending || task.Status == api.Allocated) {
		job.SetPendingTaskDiagnostic(id, failure)
		return
	}
	if task.Status != api.Pending {
		delete(job.PendingTaskDiagnostics, id)
		return
	}
	// Commit/dispatch failures belong to the failing member, even if its trial fit.
	if prior, ok := job.PendingTaskDiagnostics[id]; ok && prior.Reason == api.PodReasonSchedulerError && placed {
		return
	}
	fit, isFit := failure.Failure.(*api.FitErrors)
	switch {
	case failed && !isFit:
		job.SetPendingTaskDiagnostic(id, failure)
	case failed && !placed && d.coversTask(id, fit):
		job.SetPendingTaskDiagnostic(id, failure)
	case d.err == nil:
		job.SetPendingTaskDiagnostic(id, api.PendingTaskDiagnostic{Kind: api.PendingGangWaiting})
	}
}

// recordExcludedHyperNodes records the candidate HyperNodes that were excluded
// before any member was checked: those the gradient plugins rejected and those
// whose resources cannot hold the minimum request.
func (d *candidateDiagnostics) recordExcludedHyperNodes(ssn *framework.Session, stats *api.HyperNodeGradientStats, resources *api.HyperNodeMinResourceFilterStats, minimum *api.Resource, queues ...*util.PriorityQueue) {
	if stats != nil {
		for name := range stats.ExcludedByReason {
			if name == framework.ClusterTopHyperNode {
				continue
			}
			for _, queue := range queues {
				d.includeScope(queue, name, ssn.RealNodesList[name])
			}
			d.recordHyperNodeBlocker(api.BlockerPlacementRejected, "", name)
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
			d.recordHyperNodeBlocker(api.BlockerInsufficientResources, "", name)
		}
		for _, dimension := range dimensions {
			d.recordHyperNodeBlocker(api.BlockerInsufficientResources, v1.ResourceName(dimension), name)
		}
	}
}

// recordSkipped remembers the members left unexamined when gang failure stops the task loop.
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

// coversTask reports whether the fit errors cover every node the member may use.
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
		d.recordTaskError(id, err)
	}
}

// establishedDomain returns the HyperNode that an existing placement restricts
// further scheduling to. Only a hard topology constraint restricts it.
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

// markEstablishedDomain tags the blockers found inside an established placement.
// Ancestors are ordered finest first, so overlapping Job and SubJob
// constraints report the narrower established scope.
func (d *candidateDiagnostics) markEstablishedDomain(ssn *framework.Session, jobDomain, subJobDomain string) {
	if d == nil || (jobDomain == "" && subJobDomain == "") {
		return
	}
	marked := make(map[api.SchedulingBlocker]struct{}, len(d.blockers))
	for blocker := range d.blockers {
		if blocker.PlacementDomain == "" {
			for _, name := range ssn.HyperNodeIndex().Ancestors(blocker.HyperNodeName) {
				if name == jobDomain || name == subJobDomain {
					blocker.PlacementDomain = name
					break
				}
			}
		}
		marked[blocker] = struct{}{}
	}
	d.blockers = marked
}

// roleFitErrors gathers the fit errors already found for the task's role in
// its SubJob. A task skipped by the predicate cache shares them.
func roleFitErrors(job *api.JobInfo, subJob *api.SubJobInfo, task *api.TaskInfo) *api.FitErrors {
	fitErrors := api.NewFitErrors()
	for id, previous := range job.NodesFitErrors {
		member := job.Tasks[id]
		if member != nil && member.TaskRole == task.TaskRole && previous != nil && job.TaskToSubJob[id] == subJob.UID {
			fitErrors.Merge(previous)
		}
	}
	return fitErrors
}
