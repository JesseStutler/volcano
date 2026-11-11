# Stable Pod and PodGroup scheduling diagnostics

Status: Draft for downstream discussion. No runtime changes are included.

## Problem and scope

A failed gang attempt can leave every Pod Pending while changing the diagnostics
published on those Pods. A discarded allocation or Pipeline candidate is currently
used to describe a possible destination, and a Pod that was never evaluated can
inherit the whole PodGroup failure summary. HyperNode simulation repeats these
attempts across domains, exposing temporary choices as persistent state.

The proposal is to publish diagnostics from explicit scheduling outcomes: a Pod
reports its own blocker or that it is waiting for its PodGroup; the PodGroup reports
the group decision and aggregated blockers; debug logs retain trial placements,
per-domain details and rollback history. Retrying scheduling must remain possible
without changing an otherwise unchanged condition.

This addresses the diagnostic ownership and rollback-message portion of
[#6081](https://github.com/volcano-sh/volcano/issues/6081) and
[#6196](https://github.com/volcano-sh/volcano/issues/6196). It does not change gang
eligibility, early exit, scoring, victim selection, resource accounting, scheduling
retry policy, or transaction recovery. No CRD fields or new public condition types
are proposed.

### Relationship to existing work

| Work | Boundary of this proposal |
| --- | --- |
| [#6106](https://github.com/volcano-sh/volcano/issues/6106), implemented by merged [#6127](https://github.com/volcano-sh/volcano/pull/6127) | Retain deterministic representative-task selection where the existing formatter is used. Do not redo that fix. |
| [#6107](https://github.com/volcano-sh/volcano/issues/6107), configurable diagnostic verbosity | Leave the flag and existing detailed/summary formatter work separate. Correct ownership and exclusion of discarded candidates apply in either mode. Genuine Pod fit-error detail remains detailed by default. |
| [#6108](https://github.com/volcano-sh/volcano/issues/6108), downstream [PR #29](https://github.com/JesseStutler/volcano/pull/29) | Reuse its PodGroup event delivery policy when available; do not build another deduplication cache or modify that PR here. Stable content alone does not eliminate repeated PodGroup Event requests. |
| [#6066](https://github.com/volcano-sh/volcano/pull/6066) | Preserve the corrected nomination lifecycle. Empty nomination and changing messages are a separate failure mode. |
| #6081 informer-lag investigation | Remains deferred. Do not add last-written-object caches, synchronous informer updates or blanket retry suppression. |

The proposal develops the public discussion on
[diagnostic ownership](https://github.com/volcano-sh/volcano/issues/6081#issuecomment-6577040419)
and [explicit outcomes and HyperNode aggregation](https://github.com/volcano-sh/volcano/issues/6196#issuecomment-6599802637).
It retains the separate workstreams established in the
[#6081 breakdown](https://github.com/volcano-sh/volcano/issues/6081#issuecomment-6263823420).

## Evidence and current publication path

The #6196 report contains a kind reproduction with Volcano v1.16.0 and Kubernetes
v1.34.0: discarded Pipeline attempts changed Pod messages while nomination stayed
empty and no victim was evicted. A separate
[reported HyperNode reproduction](https://github.com/volcano-sh/volcano/issues/6196#issuecomment-6577306168)
used equal-score nodes and recorded 50 successful Pod status updates and 30 Pod
Event writes in a 30-second Allocate rollback observation. Removing trial node
names eliminated those writes in that diagnostic experiment. These are existing
reported results, not a new measurement or validation of this complete proposal.

The source inspection below uses upstream
[`8a05cdba9405e66a5f3bacf7234a98677f62c6ab`](https://github.com/volcano-sh/volcano/tree/8a05cdba9405e66a5f3bacf7234a98677f62c6ab).
The downstream PR's older base is only a destination for the design document.

1. Pending Pods enter a session through the scheduler cache. Allocate explores
   candidate placements, including nested job/subjob HyperNode attempts, and
   [discards dry-run statements](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/actions/allocate/allocate.go#L455-L686).
2. [`Statement.Discard()`](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/framework/statement.go#L376-L398)
   saves the transaction context before undoing operations.
   [`TaskSchedulingReason()`](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/api/job_info.go#L981-L1022)
   prefers that snapshot for reason/message construction, although nomination
   already uses the live transaction and eviction evidence.
3. [Gang session close](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/plugins/gang/gang.go#L228-L278)
   also uses `LastTransaction` to count tentatively schedulable tasks in the
   PodGroup condition. `JobInfo.FitError()` adds a pending-reason histogram and
   group/task dimensions. Thus removing node names alone does not remove every
   speculative input to published diagnostics.
4. Plugin close callbacks run before the
   [job updater](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/framework/session.go#L541-L550).
   [`RecordJobStatusEvent()`](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/cache/cache.go#L1792-L1845)
   falls back to the whole job's `FitError()` when a task message is empty.
   This can assign another member's failure to an unevaluated Pod.
5. [`taskUnschedulable()`](https://github.com/volcano-sh/volcano/blob/8a05cdba9405e66a5f3bacf7234a98677f62c6ab/pkg/scheduler/cache/cache.go#L1203-L1258)
   compares condition fields and nomination, then records `FailedScheduling` and
   calls `Pods.UpdateStatus` when either needs updating. Changed messages defeat
   this existing comparison.

An Event write updates an Event object, not the Pod. A successful persisted Pod
status change produces Pod watch traffic. Count status requests, successful status
changes, Event requests and Pod watch notifications separately; conflicts are
requests, but do not themselves persist another Pod change.

## Diagnostic ownership and visible behavior

| Final situation | Pod condition and Event content | PodGroup content | Debug logs |
| --- | --- | --- | --- |
| Pod has a confirmed individual scheduling failure | Its own fit/pre-filter error in the applicable search scope | Aggregate member-blocker categories | Node-level evaluation details |
| Pod found a usable placement, but the gang attempt was discarded | Stable message identifying the PodGroup it is waiting for | Gang blocker | Trial node, candidate domain and rollback cause |
| Pod was skipped because the gang requirement could no longer be met | The same group-waiting message | Gang blocker | Early-exit position and reason |
| A HyperNode fails the group's aggregate resource requirement before Pod evaluation | Group-waiting message, without claiming a Pod fit failure | Aggregate domain-capacity blocker | Domain identity, capacity, counts and thresholds |
| Explicit queue/admission restriction | Preserve an attributable explanation; refer to the group where the restriction applies to the group | Queue/admission blocker | Plugin details |
| Pod has scheduling gates | Preserve the existing gated condition; do not overwrite it with gang waiting | Appropriate existing group explanation | Gate details |
| Pipeline is retained after actual preemption | Preserve real nomination and the explanation for waiting on resource release | Group readiness/blocker as applicable | Preemption and reservation details |
| Binding succeeds or a real bind/scheduler error occurs | Existing success/error reporting | Existing lifecycle reporting | Operational details |

For example, with three members and `minMember: 3`:

- Pod A, conclusively rejected by node affinity: `No eligible node satisfies this Pod's node affinity.`
- Pod B, rolled back after finding a placement: `Waiting for PodGroup ns/job to satisfy gang requirements.`
- Pod C, skipped after early exit: `Waiting for PodGroup ns/job to satisfy gang requirements.`
- PodGroup: `Gang requirements are not satisfied. Blockers: member node affinity.`

These are illustrative messages, not new Kubernetes reason constants. Pod B and
Pod C should not alternate between a speculative-placement prefix and a group
error suffix. Pod A may correctly differ: members do not need identical messages
when their actual outcomes differ.

### Condition reasons require an explicit compatibility decision

Changing messages is insufficient if the reason still follows a discarded
`Allocated` versus `Pending` snapshot. Today a discarded allocation can produce
`Schedulable`, while a skipped Pod or discarded Pipeline produces `Unschedulable`.
An allocation-versus-skip alternation can therefore still cause status writes even
with identical waiting text.

The recommended contract is `PodScheduled=False, Reason=Unschedulable` for all
unbound Pods whose final outcome is gang waiting, including discarded allocations.
Keep the existing `Schedulable` reason for a live allocation retained for dispatch,
and retain `SchedulerError`, scheduling-gate behavior and existing Event reasons.
Internal feasibility remains available to scheduling logic and debug logs.

This changes the meaning of `Schedulable` for rolled-back allocations and needs
agreement before implementation. It is a deliberate exception to the earlier
#6081 requirement to preserve reason behavior, not a silent message cleanup.
Autoscaling consumers may distinguish these reasons, so their behavior must be
tested. If strict legacy reason behavior is required, the first fix can stabilize
messages while retaining reasons, but it must not claim to solve
allocation-versus-skip condition churn.

## Explicit outcomes instead of transaction snapshots

Introduce session-owned diagnostic results keyed by Pod UID and group/subjob UID.
They describe what was established by evaluation, separately from the mutable
transaction used to reserve and recover resources. `LastTransaction` can remain
for internal uses; neither Pod nor PodGroup diagnostic rendering should read it.

The minimum information is:

| Result field | Purpose |
| --- | --- |
| Outcome | Distinguish not evaluated, individual rejection, placement found, group waiting, explicit blocker, operational failure and retained placement. |
| Evaluation scope and completeness | Distinguish an exhausted permitted search from a failed candidate or an early exit. |
| Attributable blockers | Typed plugin/category/resource facts, including whose constraint failed. |
| Final disposition | Distinguish a discarded trial from a retained allocation or Pipeline. |

These are internal concepts; exact Go types should follow the agreed implementation
boundary. Avoid a general diagnostics framework or a second cross-session cache.

### Collection and finalization

Each candidate attempt owns its diagnostic accumulator. Nested attempts must not
overwrite their parent's results. A discarded trial contributes failure evidence
to the parent reducer, not a node name to a public message. A recovered winning
statement carries its matching outcome; rejected alternatives cannot overwrite it.

After all configured actions have run, finalize the diagnostic view before gang
close callbacks construct conditions. Both gang reporting and the job updater
consume that view. Later successful scheduling or genuine nomination supersedes
an earlier failure; backfill, preempt and reclaim must participate where they
produce or replace relevant results. An internal error must retain an explicit
error outcome rather than falling through to a generic gang message.

The reducer must follow these rules:

1. A nonempty `NodesFitErrors` map does not prove a final Pod failure. Some nodes
   may fail while another permits placement. A placement found within the relevant
   attempt invalidates a claim that the Pod had no feasible node there.
2. Publish individual no-fit only when evaluation establishes it over the
   applicable permitted scope. A failure in the last visited HyperNode is not a
   global Pod failure. Group filtering that prevented evaluation provides no such
   evidence. For incomplete searches, retain group waiting and publish scoped
   evidence on the group or in logs.
3. Keep early exit and role-based predicate reuse. When a cached rejection is
   valid for an equivalent role and scope, report the underlying attributable
   cause; do not expose the optimization message as the Pod's failure.
4. Distinguish gang early exit from queue rejection, gates and operational errors.
   Missing evidence is not proof of gang waiting. An untouched Pod without a
   known blocker keeps its existing diagnostic rather than receiving an invented
   `all nodes unavailable` result.
5. Discard session diagnostic data when the session closes. Do not use old fit
   errors to suppress a new real blocker, recovery or nomination update.

Structured logs should retain session, Pod/PodGroup UID, action, domain, trial node,
operation and discard cause. Reuse existing V(3)/V(4) transaction and topology logs;
keep expensive per-node dumps behind higher verbosity. Do not replace API churn
with unconditional high-volume logging.

## HyperNode aggregation and PodGroup publication

Apply one reducer for both a single candidate domain and multiple candidates.
Build a deterministic union of supported blocker categories across rejected
attempts. Sort and deduplicate typed keys, rather than parsing formatted strings
or reporting only the final domain visited. A key includes the blocker scope,
plugin/category and resource where relevant. Candidate names, counts and traversal
order do not create new categories.

Keep meaningful distinctions, especially:

- Insufficient aggregate HyperNode capacity for the group's minimum resources.
- Insufficient per-node resources for a complete gang placement, including
  fragmentation despite sufficient aggregate capacity.
- Member affinity or other placement constraints.
- An explicit topology or admission constraint.

For example, if two domains fail group GPU capacity and a third fails a member
affinity check, publish a group summary such as:

> No eligible HyperNode can satisfy the gang requirements. Blockers: insufficient HyperNode GPU capacity; unsatisfied member node affinity.

This is a union of observed blockers explaining why no complete group placement
was found; it does not assert that every domain or every Pod failed every category.
Only say that no eligible domain works when the permitted search was exhausted.
If a search stopped early or failed operationally, report that actual outcome.
If a candidate ultimately succeeds, do not carry rejected-candidate failures into
the successful group's diagnostic.

An established placement may constrain later scheduling to a particular domain.
That real scope can appear in the public explanation. A domain selected only for
simulation cannot. Per-domain histograms, candidate identities and trial task
counts remain in logs. Unknown plugin failures need a deterministic fallback with
the plugin identity and its actual explanation; do not discard actionable errors
by mapping everything to an undifferentiated `other` category.

Use the same finalized group summary in the gang condition and cache Event path.
Remove speculative counts derived from `LastTransaction` and the pending
`Schedulable` histogram where they encode discarded trial progress. Preserve real
job-local facts such as configured minimum membership and actual task phases.
Keep existing PodGroup condition types/reasons and lifecycle transitions.

The new simulation summary is intentionally category-based in both verbosity
modes. This does not remove node counts from genuine individual fit diagnostics
handled by #6107. The interface between these formatters must be agreed with that
workstream; detailed mode must not reintroduce a discarded placement as truth.

## Status writes, Events and kube-scheduler practices

Keep Volcano's existing condition comparison and independent nomination check.
An unchanged diagnostic must not suppress a required nomination write, binding,
eviction, recovery or deletion-related work. Preserve `LastTransitionTime` when
condition status is unchanged and retain the PodGroup comparison that ignores
transition timestamps/IDs. Do not introduce a per-session timestamp into messages.

The following practices are visible in kube-scheduler
[v1.34.0 failure handling and updatePod](https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/scheduler/schedule_one.go#L1043-L1170)
and also in the inspected
[v1.37.1 source](https://github.com/kubernetes/kubernetes/blob/v1.37.1/pkg/scheduler/schedule_one.go#L1150-L1307):

- Carry an explicit scheduling failure and separate nomination information into
  publication, rather than deriving a failure from an undone reservation.
- Compare condition and nomination independently before writing status. The API
  cacher path delegates status patching separately.
- In the direct path, use a status patch helper that skips an empty patch and
  [retries selected API errors](https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/scheduler/util/utils.go#L101-L140).

Volcano can adopt the ownership and comparison principles without changing its
status transport in this proposal. Switching `UpdateStatus` to `Patch` does not
eliminate real message changes or the resulting Pod watch notifications.

kube-scheduler still records `FailedScheduling` on failure attempts independently
of whether a condition patch is needed. It is not evidence for transition-only
Events or universal count-free messages. Volcano's event-delivery decisions must
remain explicit.

For Pods, use the finalized message in the existing status/Event publication path;
stable condition and nomination inputs already skip that path. For PodGroups,
stable summaries compose with #6108's separate delivery policy, including recovery,
UID isolation and refresh behavior. Do not gate all Pod processing on whether the
PodGroup status changed. Failed status writes remain retryable; no additional
suppression state should mark them successfully published. Event delivery can
precede a failed status write today, so API-error retries may still repeat Events.
That is distinct from successful repeated writes caused by simulation churn.

## Implementation sequence after agreement

1. Agree on the outcome/attribution contract, the reason compatibility decision
   and the HyperNode summary boundary with #6107. Keep this PR documentation-only.
2. Add outcome collection and finalization for normal and topology allocation,
   including nested discard/recover and later action overrides. Route Pod messages
   through the finalized outcome and remove the whole-job fallback. Preserve
   nomination and transaction semantics.
3. Route PodGroup condition/Event summaries through the same finalized group
   result. Remove speculative reporting counts and aggregate HyperNode categories.
   Integrate with the existing #6106/#6107/#6108 work without replacing it.
4. Verify the agreed behavior on real clusters, then update the older
   [scheduling-reason design](scheduling-reason.md) and user-facing diagnostic
   guidance alongside the implementation.

A smaller first patch may remove candidate-node text from both Allocated and
Pipelined messages, but it is only a partial mitigation: prefix changes, inherited
group errors, reason changes and last-domain reporting would remain.

## Verification and acceptance

No cluster run is required for this documentation-only PR. Implementation must
re-run the #6196 kind reproducer against the affected release and the proposed
build, and add the following user-level scenarios. Record exact images/commits,
scheduler actions/plugins, feature gates, workload manifests and observation
windows. Do not infer API traffic from recorder-call counts.

| Scenario | Required result |
| --- | --- |
| Unchanged gang, equal-score trial nodes, repeated Allocate and Pipeline rollback | After initial publication and informer convergence, trial-node changes produce no additional successful Pod status changes or Pod Events. |
| A Pod alternates between a trial placement and being skipped | Same waiting message; no reason churn if the recommended reason contract is accepted. |
| One member fails; another is rolled back; another is never evaluated | Only the failing member carries its attributable failure; the others reference the group. |
| Some nodes reject a Pod but another succeeds | Do not report individual no-fit from leftover errors. |
| One versus multiple HyperNodes; reverse candidate order; fail then succeed | Same failure-category summary for equivalent failures; no stale failures after success. |
| Group capacity rejection, fragmented nodes, member affinity, pinned domain | Preserve the distinct scope/cause; no borrowed member errors or speculative domain names. |
| Nested job/subjob trials and recover; preempt/reclaim/backfill after allocate | Final diagnostics match the retained outcome, regardless of discarded intermediate attempts. |
| Resource or affinity repair; failure category changes; recovery then recurrence | Genuine changes become visible promptly; stale failures disappear. |
| Real preemption and resource release; nomination-only change; binding | Nomination and existing lifecycle Events remain correct even with unchanged failure text. |
| Gates, queue restrictions, scheduler errors, API conflicts/failures | Preserve explicit blockers and gate ownership; failed writes retry normally. |
| Same-name Pod/PodGroup recreation and scheduler restart | No diagnostic state leaks across UIDs; fresh current diagnostics appear. |

Measure Pod status update/patch attempts and response codes, persisted condition
changes, Pod watch notifications, PodGroup writes and Event create/patch/update
requests separately. Correlate watch changes with status fields and scheduler
identity so kubelet/controller writes are not counted as scheduler regressions.
Observe after initialization for at least 30 seconds and record completed
scheduling attempts, including continued trial/rollback activity in logs.

For the unchanged reproducer, expect zero additional simulation-induced Pod
condition/nomination changes after convergence. Do not promise zero writes under
informer lag or API failures, or when genuine detailed fit histograms change.
Measure PodGroup Event reduction separately with #6108; without it, unchanged
PodGroup Events may still be repeated. Preserve scheduling throughput and gang
correctness, and measure the CPU/memory cost of diagnostic accumulation at the
scale described in #6081.

Focused regression tests should cover outcome precedence, completeness, nested
candidate reduction, stable rendering and nomination-only writes. These tests
support, rather than replace, cluster verification of actual watch/API behavior.

## Decisions for alignment

1. Adopt `Unschedulable` for all final gang-waiting outcomes, or retain legacy
   `Schedulable` behavior and accept the remaining reason churn in the initial fix?
2. Agree that simulated HyperNode results use category summaries in both verbosity
   modes, while #6107 continues to own detail policy for genuine Pod fit failures?
3. Agree on the session finalization boundary before gang close reporting and the
   action/plugin coverage required for an atomic change of diagnostic ownership?

Implementation follows this agreement. The draft does not resolve or close the
upstream tracking issues.
