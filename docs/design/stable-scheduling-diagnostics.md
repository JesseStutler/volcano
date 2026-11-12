# Stable Pod and PodGroup Scheduling Diagnostics

**Draft for discussion.** This proposal covers the diagnostic changes in
[#6081](https://github.com/volcano-sh/volcano/issues/6081) and
[#6196](https://github.com/volcano-sh/volcano/issues/6196). It does not change
scheduling decisions, rollback, or retry policy.

## Problem

Three parts of the current reporting path expose temporary scheduling work:

1. `TaskSchedulingReason()` reads `LastTransaction` after rollback. A different
   trial node changes the Pod's message although it is still Pending. A discarded
   allocation can also alternate between `Schedulable` and `Unschedulable`.
2. `RecordJobStatusEvent()` falls back to the whole `job.FitError()` when a Pod has
   no message. A member skipped by gang early exit can therefore report another
   member's failure.
3. Gang close reporting and `FitError()` include trial-derived task counts.
   HyperNode diagnostics can also reflect the last attempted domain rather than
   why the group could not be placed.

Volcano already skips unchanged Pod conditions. These changing inputs defeat that
comparison and trigger `UpdateStatus` and `FailedScheduling` Events. Successful
Pod status changes then produce Pod watch traffic; Event writes are separate API
operations. The [existing HyperNode reproduction](https://github.com/volcano-sh/volcano/issues/6196#issuecomment-6577306168)
reported 50 successful Pod status updates and 30 Pod Event writes in 30 seconds.
Those are previously reported results, not measurements of this proposal.

## Proposed Behavior

A Pod reports its own failure or a stable reference to the PodGroup it is waiting
for. The PodGroup explains the group failure. Trial placements and rollback details
remain in scheduler debug logs.

For a three-member gang, assume A fails node affinity, B finds a placement that is
rolled back, and C is skipped after gang early exit:

| Object | Condition | Event | Message |
| --- | --- | --- | --- |
| Pod A | `PodScheduled=False`, reason `Unschedulable` | `Warning / FailedScheduling` | `No eligible node satisfies this Pod's node affinity.` |
| Pod B | `PodScheduled=False`, reason `Unschedulable` | `Warning / FailedScheduling` | `Waiting for PodGroup ns/job to satisfy gang requirements.` |
| Pod C | `PodScheduled=False`, reason `Unschedulable` | `Warning / FailedScheduling` | `Waiting for PodGroup ns/job to satisfy gang requirements.` |
| PodGroup ns/job | `Unschedulable=True`, reason `NotEnoughResources` | `Warning / Unschedulable` | `Gang requirements are not satisfied. Blockers: member node affinity.` |

The messages are illustrative; genuine Pod fit errors keep the existing detailed
formatter. Each object's condition and Event use the same explanation. B and C
remain stable if their trial node or evaluation order changes. A legitimately has
a different message because it has an individual failure.

Scheduling gates retain their existing condition. Queue restrictions and scheduler
errors keep their explicit explanation rather than being rewritten as gang
waiting. Real nomination, binding, eviction and recovery keep their existing
reporting paths. A live retained allocation may still use `Schedulable`; a
discarded placement is not a retained allocation.

**Reason compatibility:** using `Unschedulable` for rolled-back allocations changes
the existing `Schedulable` case and needs agreement, including autoscaling checks.
Keeping that legacy distinction would leave reason churn even after stabilizing
the message. No new public condition or Event reason is proposed.

## Design

Use the existing error producers and publication path. Pass a Kubernetes
`PodCondition` when an action has established what should be reported, and keep
nomination separate. There is no new diagnostic state machine or session
finalization phase.

![Scheduling diagnostics through existing Volcano paths](images/stable-scheduling-diagnostics/reporting.svg)

### Pass the condition explicitly

kube-scheduler passes a scheduling failure and nomination information to
[`handleSchedulingFailure()`](https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/scheduler/schedule_one.go#L1043-L1170),
which constructs `PodScheduled=False`. Its status updater accepts an optional
condition and checks nomination independently. The useful principle is explicit
reporting input, not reconstructing failure from an undone reservation.

Volcano publishes many Pods at session close rather than immediately after one
Pod's scheduling cycle. A small session-local map on `JobInfo` bridges that
difference using the existing Kubernetes type:

```go
// JobInfo: conditions prepared for this session's publication.
// No entry means no replacement for the current PodScheduled condition.
TaskSchedulingConditions map[TaskID]v1.PodCondition
```

Actions prepare conditions in memory; they do not write Pod status directly. The
map starts empty on each session snapshot and is not copied back into the shared
cache. It needs no custom outcome enum, validity flag, collector, or public API.

Keep `NodesFitErrors` for its existing scheduling uses, including role-based
predicate reuse. Do not change that map's meaning just to simplify reporting.
Convert its errors to a Pod condition only at the point where the action has
established a final, attributable failure. For example, failures on some nodes do
not establish no-fit if another node permits placement.

The normal allocation failure branch prepares the condition as follows
(pseudocode; existing scheduling and error handling are omitted):

```go
// Only after the permitted search establishes no feasible node for this Pod.
job.TaskSchedulingConditions[task.UID] = v1.PodCondition{
    Type:    v1.PodScheduled,
    Status:  v1.ConditionFalse,
    Reason:  api.PodReasonUnschedulable,
    Message: fitErrors.Error(),
}
```

When the gang attempt fails, prepare the stable group-waiting condition for members
whose placements were discarded or whose evaluation was stopped by that gang
decision. Preserve independently established failures, gates and restrictions.
An untouched task, including a valid unschedulable-cache skip, gets no replacement
unless another action establishes a new result. Missing fit errors alone must not
be interpreted as group waiting.

### Keep HyperNode trials local

`allocateForJob()` and `allocateForSubJob()` already own the candidate loops,
statement backups and winner recovery. Resolve diagnostic scope there, before
passing conditions to the publisher; do not add a generic reducer to `Session`.

Per-domain fit errors remain local to the attempt. Save any publishable conditions
alongside the existing candidate backup, and use them only when that candidate is
selected and recovered. A recovered subjob is still tentative until its parent
decision completes. Failed recovery remains an operational error.

If no complete group placement is found, report group waiting for members without
a confirmed individual failure. A failure in one domain does not establish that
the Pod fails in every permitted domain. Publish an individual failure only when
the existing evaluation establishes it over the applicable scope; otherwise keep
the scoped explanation on the group and in logs. Do not evaluate extra nodes just
to obtain more diagnostic detail.

Collect group failure categories in an allocation-local set using the existing
plugin/resource failure information. Sort and deduplicate before assigning the
group message to `JobFitErrors`. Read structured reasons before formatting; do not
strip node names or counts from already-rendered messages. This applies equally
to one domain and multiple domains.

For example, two domains failing aggregate GPU capacity and another failing
member affinity produce:

> No eligible HyperNode can satisfy the gang requirements. Blockers: insufficient HyperNode GPU capacity; unsatisfied member node affinity.

Keep insufficient aggregate domain capacity distinct from insufficient per-node
resources for a complete placement. Candidate identities, counts and traversal
order are log detail. An established placement's domain can still be named because
it is a real constraint. Unknown plugin failures retain their actual explanation.
Only an exhausted search supports the claim that no eligible domain works; early
exit and operational errors retain their own meaning.

Later actions must replace an earlier prepared condition when they establish a
different final failure, retain a placement, or make progress. In particular,
preempt/reclaim/backfill must not leave an allocation error on a now-retained task.
Rejected alternative candidates cannot overwrite the selected result. These are
updates at the existing decision sites, not a new end-of-session reconciliation.

### Reuse the existing publisher

In `cache.RecordJobStatusEvent()`, read the prepared Pod condition instead of
calling the transaction-based `TaskSchedulingReason()`. Remove its whole-job
fallback for Pods. Adapt `taskUnschedulable()` to accept an optional condition,
while preserving its independent nomination handling:

```go
// Per-task publication, abbreviated. Scheduling-gated Pods are still skipped.
var condition *v1.PodCondition
if c, ok := job.TaskSchedulingConditions[task.UID]; ok {
    condition = &c
}
// Obtain nominatedNodeName from the existing live Pipeline/eviction path.
// An empty value does not clear an existing nomination through this path.

updateCondition := condition != nil &&
    podConditionHaveUpdate(&pod.Status, condition)
updateNomination := nominatedNodeName != "" &&
    podNominatedNodeNameNeedUpdate(&pod.Status, nominatedNodeName)
if !updateCondition && !updateNomination {
    return nil
}
// Keep the existing copy, Event, UpdateStatus, error handling and nomination sync.
```

For nomination-only updates, retain the current or prepared explanation rather
than synthesizing an empty message. A failed write remains retryable. Binding/error
callers continue to provide their explicit condition. `LastTransaction` may remain
for internal uses, but is no longer read to construct Pod or PodGroup diagnostics.

The gang plugin and cache publisher use one group-message formatter based on the
actual group state and `JobFitErrors`. Remove the reporting-only tentative count
in `gang.OnSessionClose()` and the trial-dependent pending-reason histogram in
`FitError()`. Keep configured minimum membership and actual task-phase facts.
Leave scheduling readiness and resource accounting unchanged.

When the existing cache-skip path performs no new group evaluation, preserve the
current group diagnostic. An empty error string alone is not evidence of recovery.

Existing comparisons still control status writes. Unchanged Pod conditions and
nomination skip the Pod Event/status path. Unchanged PodGroup Event delivery remains
the separate responsibility of #6108; this change supplies stable content to that
path. kube-scheduler itself records failed-scheduling Events independently of its
no-op status check, so it is not an Event deduplication model to copy wholesale.

## Scope of Code Changes

The changes stay in four existing areas:

- **`api/job_info.go`:** add the native condition map for session publication,
  retire transaction-based Pod rendering, and simplify the group message. Keep
  snapshot initialization and shared-cache ownership explicit.
- **Allocation and related actions:** prepare conditions at final decision sites;
  keep HyperNode trial errors local and aggregate group categories in the existing
  loops. Reuse error detail from `api/unschedule_info.go`.
- **`plugins/gang/gang.go`:** use the shared group message instead of reconstructing
  trial progress from `LastTransaction`.
- **`cache/cache.go`:** accept optional Pod conditions, remove the group-to-Pod
  fallback, and preserve nomination and existing write comparisons.

`framework.CloseSession()`, statement commit/discard/recovery and the unschedulable
job cache keep their current lifecycle. Existing transaction/topology logs carry
trial node, domain and rollback details at debug verbosity.

## Compatibility and Verification

Keep #6106/#6127's deterministic selection where its formatter remains in use.
#6107 continues to own configurable detail for genuine fit errors; detailed mode
must not reintroduce discarded placements. #6108 and downstream PR #29 retain
ownership of PodGroup Event suppression, recurrence and refresh. The #6081
informer-lag work remains deferred; no extra write-suppression cache is introduced.

Before implementing, agree on the rolled-back allocation reason change and the
category-summary boundary with #6107. Validate the implementation with:

- The #6196 Allocate/Pipeline reproducer: trial-node changes and trial-versus-skip
  alternation must stop changing Pod conditions after informer convergence.
- The A/B/C example, including failures on some nodes followed by placement on
  another, so residual fit errors cannot become an individual failure.
- Single/nested/multiple HyperNode attempts, parent rollback and winner recovery;
  equivalent final facts must produce the same summary regardless of order.
- Real preemption, nomination-only updates, binding, gates, Queue restrictions,
  API errors, cache skips and UID recreation, preserving existing behavior.

Compare affected and patched builds on a real cluster. Count successful Pod status
changes, status requests by response code, Pod watch notifications and Event API
requests separately. Confirm trials still run while unchanged diagnostic writes
stop, and measure added bookkeeping cost at the #6081 workload scale.
Measure PodGroup Event reduction separately with #6108. No new cluster results
are claimed by this documentation-only proposal.

## References

The design builds on the public [Pod ownership discussion](https://github.com/volcano-sh/volcano/issues/6081#issuecomment-6577040419)
and [HyperNode reporting proposal](https://github.com/volcano-sh/volcano/issues/6196#issuecomment-6599802637).
Source inspection is pinned to upstream `8a05cdba9405e66a5f3bacf7234a98677f62c6ab`:

- [TaskSchedulingReason](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/api/job_info.go#L981-L1022)
  and [allocation candidate loops](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/actions/allocate/allocate.go#L455-L686).
- [Gang condition construction](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/plugins/gang/gang.go#L228-L278),
  [Pod writes](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/cache/cache.go#L1203-L1258)
  and [group/task publication](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/cache/cache.go#L1792-L1845).
- Earlier designs: [Scheduling Reason](scheduling-reason.md) and
  [Unschedulable Job Cache](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/docs/design/unschedulable-job-cache.md).
