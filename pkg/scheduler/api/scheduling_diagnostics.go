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
	"cmp"
	"errors"
	"fmt"
	"maps"
	"slices"
	"sort"
	"strings"

	v1 "k8s.io/api/core/v1"
	"volcano.sh/apis/pkg/apis/scheduling"
)

// PendingTaskDiagnosticKind distinguishes an individual rejection from gang waiting.
type PendingTaskDiagnosticKind uint8

const (
	PendingTaskFailure PendingTaskDiagnosticKind = iota + 1
	PendingGangWaiting
)

// PendingTaskDiagnostic retains a final Pending result until session-close publication.
type PendingTaskDiagnostic struct {
	Kind    PendingTaskDiagnosticKind
	Reason  string
	Failure error
}

// BlockerScope identifies whether a check rejected a member or an entire domain.
type BlockerScope string

const (
	MemberScope    BlockerScope = "Member"
	HyperNodeScope BlockerScope = "HyperNode"
)

// SchedulingBlocker is the stable identity of a member or domain rejection.
type SchedulingBlocker struct {
	Scope         BlockerScope
	Reason        string
	ResourceName  v1.ResourceName
	TaskID        TaskID
	HyperNodeName string
	// PlacementDomain is the enclosing constraint from an established placement.
	PlacementDomain string
}

// GroupSchedulingDiagnostic holds a completed Job attempt. An empty result clears blockers.
type GroupSchedulingDiagnostic struct {
	Blockers []SchedulingBlocker
}

// GroupReadyMessage is shared by the ready PodGroup condition and Event.
const GroupReadyMessage = "PodGroup satisfies its gang requirements."

// RecordPendingTaskFailure retains a result independently of the working fit errors.
func (ji *JobInfo) RecordPendingTaskFailure(id TaskID, reason string, failure error) {
	if failure == nil {
		return
	}
	if fit, ok := failure.(*FitErrors); ok {
		failure = fit.Clone()
	} else {
		failure = errors.New(failure.Error())
	}
	ji.SetPendingTaskDiagnostic(id, PendingTaskDiagnostic{Kind: PendingTaskFailure, Reason: reason, Failure: failure})
}

// SetPendingTaskDiagnostic allocates session-local storage on the first result.
func (ji *JobInfo) SetPendingTaskDiagnostic(id TaskID, diagnostic PendingTaskDiagnostic) {
	if ji.PendingTaskDiagnostics == nil {
		ji.PendingTaskDiagnostics = make(map[TaskID]PendingTaskDiagnostic)
	}
	ji.PendingTaskDiagnostics[id] = diagnostic
}

// TaskSchedulingCondition selects the final explanation, after actions have finished.
// An absent Pending result leaves the condition observed through the informer intact.
func (ji *JobInfo) TaskSchedulingCondition(task *TaskInfo) *v1.PodCondition {
	if task.SchGated {
		return nil
	}
	condition := &v1.PodCondition{Type: v1.PodScheduled, Status: v1.ConditionFalse, Reason: PodReasonUnschedulable}
	if diagnostic, found := ji.PendingTaskDiagnostics[task.UID]; found && diagnostic.Reason == PodReasonSchedulerError && diagnostic.Failure != nil && (task.Status == Pending || task.Status == Allocated) {
		condition.Reason, condition.Message = diagnostic.Reason, diagnostic.Failure.Error()
		return condition
	}
	switch task.Status {
	case Pipelined:
		condition.Message = "Waiting for resources to be released for this Pod."
	case Allocated:
		condition.Reason = PodReasonSchedulable
		condition.Message = fmt.Sprintf("Waiting for PodGroup %s/%s to satisfy gang requirements.", ji.Namespace, ji.Name)
	case Pending:
		diagnostic, found := ji.PendingTaskDiagnostics[task.UID]
		if !found {
			return nil
		}
		switch diagnostic.Kind {
		case PendingTaskFailure:
			if diagnostic.Failure == nil {
				return nil
			}
			condition.Reason, condition.Message = diagnostic.Reason, taskFailureMessage(diagnostic.Failure)
		case PendingGangWaiting:
			condition.Message = fmt.Sprintf("Waiting for PodGroup %s/%s to satisfy gang requirements.", ji.Namespace, ji.Name)
		default:
			return nil
		}
	default:
		return nil
	}
	return condition
}

// GroupSchedulingMessage formats only a completed group result. A skipped attempt
// preserves the previously published unschedulable explanation.
func (ji *JobInfo) GroupSchedulingMessage() string {
	if ji.GroupDiagnostic == nil && ji.PodGroup != nil {
		for i := len(ji.PodGroup.Status.Conditions) - 1; i >= 0; i-- {
			c := ji.PodGroup.Status.Conditions[i]
			if c.Type == scheduling.PodGroupUnschedulableType && c.Status == v1.ConditionTrue && c.Message != "" {
				return c.Message
			}
		}
	}
	const prefix = "Gang requirements are not satisfied."
	if ji.GroupDiagnostic == nil || len(ji.GroupDiagnostic.Blockers) == 0 {
		return prefix
	}
	// A trial supplies context for the logs. Only an established placement
	// shared by all checks for this cause can identify a domain in the message.
	type cause struct {
		scope       BlockerScope
		pod, reason string
		resource    v1.ResourceName
	}
	type location struct {
		searched bool
		fixed    string
	}
	causes := make(map[cause]location)
	for _, blocker := range ji.GroupDiagnostic.Blockers {
		key := cause{scope: blocker.Scope, reason: blocker.Reason, resource: blocker.ResourceName}
		if blocker.Scope == MemberScope {
			task := ji.Tasks[blocker.TaskID]
			if task == nil {
				continue
			}
			key.pod = task.Namespace + "/" + task.Name
		}
		loc, exists := causes[key]
		if !exists {
			loc.fixed = blocker.PlacementDomain
		} else if loc.fixed != blocker.PlacementDomain {
			loc.fixed = ""
		}
		loc.searched = loc.searched || blocker.HyperNodeName != ""
		causes[key] = loc
	}
	ordered := slices.SortedFunc(maps.Keys(causes), func(a, b cause) int {
		return cmp.Or(cmp.Compare(a.scope, b.scope), cmp.Compare(a.pod, b.pod),
			cmp.Compare(a.reason, b.reason), cmp.Compare(a.resource, b.resource))
	})
	messages := []string{prefix}
	for _, key := range ordered {
		resource := string(key.resource)
		if resource == "" {
			resource = "resource"
		}
		var message string
		if key.scope == HyperNodeScope {
			message = "HyperNode placement requirements are not satisfied"
			if key.reason == "InsufficientResources" {
				message = "Insufficient HyperNode " + resource + " capacity"
			}
		} else {
			subject := "Pod " + key.pod
			switch key.reason {
			case "InsufficientResources":
				message = subject + " has insufficient " + resource + " capacity"
			case "NodeAffinity":
				message = subject + " has no node satisfying node affinity"
			case "TaintToleration":
				message = subject + " has no node with tolerated taints"
			case "PodAffinity", "InterPodAffinity":
				message = subject + " has no node satisfying Pod affinity constraints"
			case "PlacementRejected":
				message = subject + " does not satisfy placement requirements"
			default:
				message = subject + " does not satisfy scheduling predicates"
			}
		}
		loc := causes[key]
		if loc.fixed != "" {
			message += " within HyperNode " + loc.fixed
		} else if key.scope == MemberScope && loc.searched {
			message += " within the checked HyperNodes"
		}
		messages = append(messages, message+".")
	}
	return strings.Join(messages, " ")
}

// taskFailureMessage explains why no node fits the Pod. Node totals, per-reason
// counts and candidate names stay in the logs, so another node that fails for
// the same reason leaves the Pod condition unchanged.
func taskFailureMessage(failure error) string {
	fit, ok := failure.(*FitErrors)
	if !ok {
		return failure.Error()
	}
	var constraints []string
	for category := range fit.failureCategories() {
		switch category.Reason {
		case "InsufficientResources":
			if category.ResourceName == "" {
				constraints = append(constraints, "resource requests")
			} else {
				constraints = append(constraints, string(category.ResourceName)+" request")
			}
		case "NodeAffinity":
			constraints = append(constraints, "node affinity")
		case "TaintToleration":
			constraints = append(constraints, "taint tolerations")
		case "PodAffinity", "InterPodAffinity":
			constraints = append(constraints, "Pod affinity constraints")
		default:
			constraints = append(constraints, "scheduling predicates")
		}
	}
	sort.Strings(constraints)
	last := len(constraints) - 1
	list := constraints[last]
	if last > 0 {
		list = strings.Join(constraints[:last], ", ") + " and " + list
	}
	return "No eligible node satisfies this Pod's " + list + "."
}

// Clone snapshots mutable node errors before another candidate reuses them.
func (f *FitErrors) Clone() *FitErrors {
	if f == nil {
		return nil
	}
	result := NewFitErrors()
	result.err, result.hyperNode = f.err, f.hyperNode
	for name, node := range f.nodes {
		copyNode := *node
		copyNode.Status = make(StatusSets, len(node.Status))
		for i, status := range node.Status {
			if status == nil {
				continue
			}
			copyStatus := *status
			copyStatus.InsufficientResources = append([]string(nil), status.InsufficientResources...)
			copyNode.Status[i] = &copyStatus
		}
		result.nodes[name] = &copyNode
	}
	return result
}

// Merge combines retained node failures without carrying a candidate-specific prefix.
func (f *FitErrors) Merge(other *FitErrors) {
	if other == nil {
		return
	}
	snapshot := other.Clone()
	for name, node := range snapshot.nodes {
		f.nodes[name] = node
	}
	if len(f.nodes) == 0 && f.err == "" {
		f.err = other.err
	}
	f.hyperNode = ""
}

// CoversNodes verifies that every node in the permitted scope was checked.
func (f *FitErrors) CoversNodes(nodes []*NodeInfo) bool {
	if f == nil || len(nodes) == 0 {
		return false
	}
	for _, node := range nodes {
		if _, ok := f.nodes[node.Name]; !ok {
			return false
		}
	}
	return true
}

// failureCategories classifies node rejections by predicate identity and
// resource dimension, never by trial node name.
func (f *FitErrors) failureCategories() map[SchedulingBlocker]struct{} {
	keys := make(map[SchedulingBlocker]struct{})
	if f != nil {
		for _, node := range f.nodes {
			for _, status := range node.Status {
				if status == nil {
					continue
				}
				key := SchedulingBlocker{Scope: MemberScope, Reason: "PredicateRejected"}
				switch status.Plugin {
				case "predicates-resource-fit", "NodeResourcesFit":
					key.Reason = "InsufficientResources"
				case "NodeAffinity", "TaintToleration", "InterPodAffinity":
					key.Reason = status.Plugin
				}
				if len(status.InsufficientResources) > 0 {
					key.Reason = "InsufficientResources"
					for _, resource := range status.InsufficientResources {
						key.ResourceName = v1.ResourceName(resource)
						keys[key] = struct{}{}
					}
				} else {
					keys[key] = struct{}{}
				}
			}
		}
	}
	if len(keys) == 0 {
		keys[SchedulingBlocker{Scope: MemberScope, Reason: "PredicateRejected"}] = struct{}{}
	}
	return keys
}

// SchedulingBlockers uses predicate identities and resource dimensions, never trial node names.
func (f *FitErrors) SchedulingBlockers(id TaskID, domain string) []SchedulingBlocker {
	categories := f.failureCategories()
	result := make([]SchedulingBlocker, 0, len(categories))
	for key := range categories {
		key.TaskID, key.HyperNodeName = id, domain
		result = append(result, key)
	}
	return result
}

// RecordGangWaiting replaces failures for members whose placements were tried
// successfully but are discarded by the outer gang decision.
func (ji *JobInfo) RecordGangWaiting(tasks []*TaskInfo) {
	for _, task := range tasks {
		if !task.SchGated {
			ji.SetPendingTaskDiagnostic(task.UID, PendingTaskDiagnostic{Kind: PendingGangWaiting})
		}
	}
}
