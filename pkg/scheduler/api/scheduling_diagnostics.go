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
			condition.Reason, condition.Message = diagnostic.Reason, diagnostic.Failure.Error()
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
	// Group domain names only for the same member, cause and resource dimension.
	groups := make(map[SchedulingBlocker]map[string]struct{})
	for _, blocker := range ji.GroupDiagnostic.Blockers {
		domain := blocker.HyperNodeName
		blocker.HyperNodeName = ""
		if groups[blocker] == nil {
			groups[blocker] = make(map[string]struct{})
		}
		groups[blocker][domain] = struct{}{}
	}
	messages := make([]string, 0, len(groups))
	for blocker, domains := range groups {
		names := make([]string, 0, len(domains))
		for name := range domains {
			if name != "" {
				names = append(names, name)
			}
		}
		sort.Strings(names)
		domain := ""
		if len(names) == 1 {
			domain = "HyperNode " + names[0]
		} else if len(names) > 1 {
			domain = "HyperNodes " + strings.Join(names, ", ")
		}
		subject := domain
		if blocker.Scope == MemberScope {
			task := ji.Tasks[blocker.TaskID]
			if task == nil {
				continue
			}
			subject = "Pod " + task.Namespace + "/" + task.Name
		}
		if subject == "" {
			subject = "The placement"
		}
		var explanation string
		switch blocker.Reason {
		case "InsufficientResources":
			resource := string(blocker.ResourceName)
			if resource == "" {
				resource = "resource"
			}
			explanation = "has insufficient " + resource + " capacity"
		case "NodeAffinity":
			explanation = "has no node satisfying node affinity"
		case "TaintToleration":
			explanation = "has no node with tolerated taints"
		case "PodAffinity", "InterPodAffinity":
			explanation = "has no node satisfying Pod affinity constraints"
		case "PlacementRejected":
			explanation = "does not satisfy placement requirements"
		default:
			explanation = "does not satisfy scheduling predicates"
		}
		message := subject + " " + explanation
		if blocker.Scope == MemberScope && domain != "" {
			message += " within " + domain
		}
		messages = append(messages, message+".")
	}
	sort.Strings(messages)
	if len(messages) == 0 {
		return prefix
	}
	return prefix + " " + strings.Join(messages, " ")
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

// SchedulingBlockers uses predicate identities and resource dimensions, never trial node names.
func (f *FitErrors) SchedulingBlockers(id TaskID, domain string) []SchedulingBlocker {
	keys := make(map[SchedulingBlocker]struct{})
	if f != nil {
		for _, node := range f.nodes {
			for _, status := range node.Status {
				if status == nil {
					continue
				}
				key := SchedulingBlocker{Scope: MemberScope, Reason: "PredicateRejected", TaskID: id, HyperNodeName: domain}
				switch status.Plugin {
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
		keys[SchedulingBlocker{Scope: MemberScope, Reason: "PredicateRejected", TaskID: id, HyperNodeName: domain}] = struct{}{}
	}
	result := make([]SchedulingBlocker, 0, len(keys))
	for key := range keys {
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
