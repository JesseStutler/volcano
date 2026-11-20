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

// Blocker reasons classify a rejection without naming a trial Node. The three
// constraint reasons reuse the names of the predicate plugins that report them.
const (
	BlockerNodeAffinity          = "NodeAffinity"
	BlockerTaintToleration       = "TaintToleration"
	BlockerPodAffinity           = "InterPodAffinity"
	BlockerInsufficientResources = "InsufficientResources"
	BlockerPlacementRejected     = "PlacementRejected"
	BlockerPredicateRejected     = "PredicateRejected"
)

// GroupSchedulingDiagnostic holds a completed Job attempt. An empty result clears blockers.
type GroupSchedulingDiagnostic struct {
	Blockers []SchedulingBlocker
}

const (
	// GroupReadyMessage is shared by the ready PodGroup condition and Event.
	GroupReadyMessage = "PodGroup satisfies its gang requirements."
	// groupUnsatisfiedMessage starts every unschedulable PodGroup explanation.
	groupUnsatisfiedMessage = "Gang requirements are not satisfied."
	// pipelinedTaskMessage explains a member that keeps its Pipeline.
	pipelinedTaskMessage = "Waiting for resources to be released for this Pod."
	// gangWaitingFormat takes the PodGroup namespace and name.
	gangWaitingFormat = "Waiting for PodGroup %s/%s to satisfy gang requirements."
)

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

// PrePredicateFailureReason tells a plugin rejection from a scheduler error.
func PrePredicateFailureReason(err error) string {
	if _, rejected := err.(*PrePredicateError); rejected {
		return PodReasonUnschedulable
	}
	return PodReasonSchedulerError
}

// NominatedNodeName returns the node to publish as the Pod's nomination. Only a
// live Pipeline that evicted victims nominates a node. A rolled-back trial does not.
func (ti *TaskInfo) NominatedNodeName() string {
	if ti.Status == Pipelined && ti.EvictionOccurred {
		return ti.NodeName
	}
	return ""
}

// TaskSchedulingCondition selects the final explanation, after actions have finished.
// An absent Pending result leaves the condition observed through the informer intact.
func (ji *JobInfo) TaskSchedulingCondition(task *TaskInfo) *v1.PodCondition {
	if task.SchGated {
		return nil
	}
	diagnostic, recorded := ji.PendingTaskDiagnostics[task.UID]
	// A scheduler error belongs to the member that failed, whether it is still
	// Pending or holds an allocation.
	if recorded && diagnostic.Reason == PodReasonSchedulerError && diagnostic.Failure != nil && (task.Status == Pending || task.Status == Allocated) {
		return unscheduledCondition(diagnostic.Reason, diagnostic.Failure.Error())
	}
	switch task.Status {
	case Pipelined:
		return unscheduledCondition(PodReasonUnschedulable, pipelinedTaskMessage)
	case Allocated:
		return unscheduledCondition(PodReasonSchedulable, ji.gangWaitingMessage())
	case Pending:
		if !recorded {
			return nil
		}
		switch diagnostic.Kind {
		case PendingTaskFailure:
			if diagnostic.Failure == nil {
				return nil
			}
			return unscheduledCondition(diagnostic.Reason, taskFailureMessage(diagnostic.Failure))
		case PendingGangWaiting:
			return unscheduledCondition(PodReasonUnschedulable, ji.gangWaitingMessage())
		}
	}
	return nil
}

// unscheduledCondition builds the PodScheduled condition of a task that is not bound.
func unscheduledCondition(reason, message string) *v1.PodCondition {
	return &v1.PodCondition{Type: v1.PodScheduled, Status: v1.ConditionFalse, Reason: reason, Message: message}
}

// gangWaitingMessage is the stable explanation for a member that waits for its PodGroup.
func (ji *JobInfo) gangWaitingMessage() string {
	return fmt.Sprintf(gangWaitingFormat, ji.Namespace, ji.Name)
}

// blockerCause identifies one sentence of the PodGroup message. Blockers that
// differ only by the checked HyperNode share a cause.
type blockerCause struct {
	scope BlockerScope
	// pod is the namespace/name of the affected member. A HyperNode blocker leaves it empty.
	pod      string
	reason   string
	resource v1.ResourceName
}

// blockerDomain describes where the checks behind a cause ran.
type blockerDomain struct {
	// searched reports that a HyperNode search found the blocker.
	searched bool
	// established is the placement domain shared by all checks, or empty.
	established string
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
	if ji.GroupDiagnostic == nil || len(ji.GroupDiagnostic.Blockers) == 0 {
		return groupUnsatisfiedMessage
	}
	causes := ji.groupBlockerCauses()
	ordered := slices.SortedFunc(maps.Keys(causes), func(a, b blockerCause) int {
		return cmp.Or(cmp.Compare(a.scope, b.scope), cmp.Compare(a.pod, b.pod),
			cmp.Compare(a.reason, b.reason), cmp.Compare(a.resource, b.resource))
	})
	messages := []string{groupUnsatisfiedMessage}
	for _, cause := range ordered {
		messages = append(messages, cause.sentence(causes[cause]))
	}
	return strings.Join(messages, " ")
}

// groupBlockerCauses merges the blockers that publish the same sentence.
// A trial supplies context for the logs. Only an established placement
// shared by all checks for this cause can identify a domain in the message.
func (ji *JobInfo) groupBlockerCauses() map[blockerCause]blockerDomain {
	causes := make(map[blockerCause]blockerDomain)
	for _, blocker := range ji.GroupDiagnostic.Blockers {
		cause := blockerCause{scope: blocker.Scope, reason: blocker.Reason, resource: blocker.ResourceName}
		if blocker.Scope == MemberScope {
			task := ji.Tasks[blocker.TaskID]
			if task == nil {
				continue
			}
			cause.pod = fmt.Sprintf("%s/%s", task.Namespace, task.Name)
		}
		domain, exists := causes[cause]
		if !exists {
			domain.established = blocker.PlacementDomain
		} else if domain.established != blocker.PlacementDomain {
			domain.established = ""
		}
		domain.searched = domain.searched || blocker.HyperNodeName != ""
		causes[cause] = domain
	}
	return causes
}

// sentence explains the cause and where its checks ran.
func (c blockerCause) sentence(domain blockerDomain) string {
	switch {
	case domain.established != "":
		return fmt.Sprintf("%s within HyperNode %s.", c.explanation(), domain.established)
	case c.scope == MemberScope && domain.searched:
		return fmt.Sprintf("%s within the checked HyperNodes.", c.explanation())
	default:
		return fmt.Sprintf("%s.", c.explanation())
	}
}

// explanation describes what failed, without the scope of the checks.
func (c blockerCause) explanation() string {
	resource := c.resource
	if resource == "" {
		resource = "resource"
	}
	if c.scope == HyperNodeScope {
		if c.reason == BlockerInsufficientResources {
			return fmt.Sprintf("Insufficient HyperNode %s capacity", resource)
		}
		return "HyperNode placement requirements are not satisfied"
	}
	switch c.reason {
	case BlockerInsufficientResources:
		return fmt.Sprintf("Pod %s has insufficient %s capacity", c.pod, resource)
	case BlockerNodeAffinity:
		return fmt.Sprintf("Pod %s has no node satisfying node affinity", c.pod)
	case BlockerTaintToleration:
		return fmt.Sprintf("Pod %s has no node with tolerated taints", c.pod)
	case BlockerPodAffinity:
		return fmt.Sprintf("Pod %s has no node satisfying Pod affinity constraints", c.pod)
	case BlockerPlacementRejected:
		return fmt.Sprintf("Pod %s does not satisfy placement requirements", c.pod)
	default:
		return fmt.Sprintf("Pod %s does not satisfy scheduling predicates", c.pod)
	}
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
		constraints = append(constraints, taskConstraint(category))
	}
	sort.Strings(constraints)
	last := len(constraints) - 1
	if last == 0 {
		return fmt.Sprintf("No eligible node satisfies this Pod's %s.", constraints[0])
	}
	return fmt.Sprintf("No eligible node satisfies this Pod's %s and %s.", strings.Join(constraints[:last], ", "), constraints[last])
}

// taskConstraint names the Pod constraint that a failure category violates.
func taskConstraint(category SchedulingBlocker) string {
	switch category.Reason {
	case BlockerInsufficientResources:
		if category.ResourceName == "" {
			return "resource requests"
		}
		return fmt.Sprintf("%s request", category.ResourceName)
	case BlockerNodeAffinity:
		return "node affinity"
	case BlockerTaintToleration:
		return "taint tolerations"
	case BlockerPodAffinity:
		return "Pod affinity constraints"
	default:
		return "scheduling predicates"
	}
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
				key := SchedulingBlocker{Scope: MemberScope, Reason: blockerReason(status)}
				if len(status.InsufficientResources) == 0 {
					keys[key] = struct{}{}
					continue
				}
				for _, resource := range status.InsufficientResources {
					key.ResourceName = v1.ResourceName(resource)
					keys[key] = struct{}{}
				}
			}
		}
	}
	if len(keys) == 0 {
		keys[SchedulingBlocker{Scope: MemberScope, Reason: BlockerPredicateRejected}] = struct{}{}
	}
	return keys
}

// blockerReason maps a predicate status to the reason published for it.
func blockerReason(status *Status) string {
	if len(status.InsufficientResources) > 0 {
		return BlockerInsufficientResources
	}
	switch status.Plugin {
	// The resource-fit predicates may report a shortage without naming the resource.
	case "predicates-resource-fit", "NodeResourcesFit":
		return BlockerInsufficientResources
	case BlockerNodeAffinity, BlockerTaintToleration, BlockerPodAffinity:
		return status.Plugin
	default:
		return BlockerPredicateRejected
	}
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
