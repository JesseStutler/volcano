# Unschedulable Job Cache E2E Validation Guide

> [!CAUTION]
> **TEMPORARY VALIDATION DOCUMENT — DROP THIS COMMIT BEFORE SUBMITTING THE FINAL PR.**
>
> This file exists only to guide manual Kind-cluster validation and automated result checking. It must not be included in the final code submission. Before submitting, drop the commit whose subject starts with `TEMP(DROP BEFORE SUBMIT)` and verify this file no longer exists.

## Purpose

The suite verifies both halves of the feature contract at Job and Task
granularity:

1. A repeatedly unschedulable Volcano Job is recorded in the Unschedulable Job Cache and skipped in a later scheduler session.
2. A matching cluster event invalidates the cached record and causes the Job or
  rejected Task to be scheduled without waiting for the five-minute watchdog.

The quota-plugin group runs the same contracts independently with `proportion`
and `capacity`. This proves that each plugin registers and executes its own
Queue and Pod hints rather than relying on another enabled quota plugin.

Merely observing that the Job eventually runs is insufficient. Each case also checks scheduler metrics to prove that a later scheduling session skipped allocation and that the matching event explicitly woke the cached Job.

## Prerequisites

- A working Kind environment supported by `hack/run-e2e-kind.sh`.
- Volcano images built or available in `_output/images`.
- Permission to create and delete Kind clusters.
- Enough local resources for the standard Volcano E2E cluster.

The Make target enables the feature gate automatically:

```bash
make e2e-test-unschedulablejobcache FORCE_REBUILD=false
```

Equivalent runner invocation:

```bash
E2E_TYPE=UNSCHEDULABLEJOBCACHE \
FEATURE_GATES="UnschedulableJobCache=true" \
./hack/run-e2e-kind.sh
```

## Expected suite result

Ginkgo should execute exactly eleven specs in
`test/e2e/unschedulablejobcache/` and report:

```text
11 Passed | 0 Failed | 0 Pending | 0 Skipped
```

A failure should generate logs under `ARTIFACTS_PATH` when that environment variable is set.

## Quota plugin hint cases

Ginkgo groups these specs under `Quota plugin hints`, with separate
`proportion` and `capacity` subgroups. Each subgroup runs the following three
cases.

### Cases 1-2: Queue update wakes a Job-level enqueue rejection

Spec name within each plugin subgroup:

```text
wakes a Job when its Queue capability increases
```

#### Setup and rejection

- Select only the quota plugin named by the subgroup.
- Create a Queue whose capability is `100m` CPU.
- Create a one-task Job in that Queue whose PodGroup minimum request is `200m`.
- The Node has enough resources, but the quota plugin rejects the whole Job at
  the `JobEnqueueable` extension point.
- The Job remains unbound and the Job-specific skip counter increases with
  `stage="enqueue"`.

#### Trigger and expected recovery

- Increase the same Queue's capability to `1` CPU.
- The plugin's Queue hint sees a relaxed capability and wakes the cached Job.
- The wakeup counter increases with `resource="Queue"`.
- The Job reaches Running or Succeeded within one minute.

These are Cases 1 and 2 because the contract is run once for `proportion` and
once for `capacity`.

### Cases 3-4: Queue update wakes a Task-level allocatable rejection

Spec name within each plugin subgroup:

```text
wakes a rejected task when its Queue capability increases
```

#### Setup and rejection

- Configure the scheduler to run only `enqueue` and create a Queue with `1` CPU
  capability.
- Create a Job with one `600m` Task and wait for its PodGroup to reach
  `Inqueue`. This proves Job-level admission succeeded.
- Reduce Queue capability to `500m` only after admission.
- Switch the scheduler action list to `allocate` only.
- The quota plugin rejects the concrete Task at the `Allocatable` extension
  point and records `RejectionAllocatable`.
- The Task remains unbound and the skip counter increases with
  `stage="allocate"`.

The action split is essential: starting with a `500m` capability would reject
the whole Job during enqueue and would not validate Task-level caching.

#### Trigger and expected recovery

- Restore Queue capability to `1` CPU.
- The plugin's Queue hint wakes the cached Task rejection.
- The wakeup counter increases with `resource="Queue"`.
- The Task reaches Running or Succeeded within one minute.

### Cases 5-6: Pod deletion wakes a Task-level quota rejection

Spec name within each plugin subgroup:

```text
wakes a rejected task when a quota-consuming Pod is deleted
```

#### Setup and rejection

- Admit a `600m` Task into a Queue with `1` CPU capability while only `enqueue`
  runs.
- Directly bind a separate `600m` blocker Pod to a Node and associate it with
  the same Queue and a PodGroup.
- Start `allocate` only. The blocker and target need `1.2` CPU in total, so the
  target Task is rejected by the quota plugin's `Allocatable` check.
- The Task remains unbound and the allocate skip counter increases.

#### Trigger and expected recovery

- Delete the blocker Pod.
- For `proportion`, `podHint` detects released CPU in a dimension requested by
  the rejected Task.
- For `capacity`, `podHint` confirms that the Pod's Queue is in the recorded
  rejection Queue path.
- The wakeup counter increases with `resource="Pod"`.
- The Task reaches Running or Succeeded within one minute.

## Generic event hints and cache behavior

These five specs are grouped separately from the quota-plugin-specific cases.

## Case 7: Node update wakes an entire multi-replica Job

Spec name:

```text
wakes a multi-replica Job when one rejected task is helped by a Node update
```

### Setup

- Create one PodGroup-backed Volcano Job with two replicas and `minAvailable=2`.
- Give both replicas required Node affinity for a unique label value based on the test namespace.
- Initially, no untainted worker Node has that label.

### Expected behavior before the event

- The Job reaches Pending.
- The Job receives an Unschedulable scheduling result.
- Both replicas remain unbound (`spec.nodeName` is empty).
- Within one minute, the Job-specific metric below increases:

```text
volcano_unschedulable_job_cache_skips_total{job_namespace="...",job_name="node-label-wakeup",stage="allocate"}
```

An increase proves that a subsequent scheduler session suppressed allocation instead of re-running predicates.

### Trigger

Patch one untainted worker Node to add the required label.

### Expected behavior after the event

- The Node label update matches the predicate plugin's QueueingHint subscription.
- The Job-specific `volcano_unschedulable_job_cache_wakeups_total` metric increases for the Node event.
- The cache record is invalidated.
- The entire Job is re-evaluated after a hint for any rejected replica wakes the Job-level cache entry.
- Both replicas reach Running or Succeeded within one minute, satisfying `minAvailable=2`.
- Both replicas are bound to the Node that received the label.
- The original Node label value is restored during cleanup.

The one-minute deadline is intentionally shorter than the five-minute cache watchdog. Passing only after watchdog expiry is a failure.

## Case 8: Pod deletion wakes a resource-fit-blocked Job

Spec name:

```text
skips a resource-blocked Job until a scheduled Pod is deleted
```

### Setup

- Restrict the test context to one untainted Node with one schedulable CPU slot.
- Create a blocker Pod that consumes that CPU.
- Create a one-task Volcano Job requesting one CPU with `minAvailable=1`.

### Expected behavior before the event

- The blocker Pod is Running.
- The Job reaches Pending.
- The Job receives an Unschedulable scheduling result caused by resource fit.
- The Job task remains unbound.
- Within one minute, the Job-specific metric below increases:

```text
volcano_unschedulable_job_cache_skips_total{job_namespace="...",job_name="pod-delete-wakeup",stage="allocate"}
```

### Trigger

Delete the scheduled blocker Pod.

### Expected behavior after the event

- The scheduled Pod deletion is dispatched as a resource-release event.
- The Job-specific `volcano_unschedulable_job_cache_wakeups_total` metric increases for the Pod event.
- The resource-fit hint invalidates the Job's cached rejection.
- The Job reaches Running or Succeeded within one minute.

Again, completion after the five-minute watchdog is not acceptable.

## Case 9: A cached Job does not affect a schedulable Job

Spec name:

```text
does not affect Jobs that can be scheduled normally
```

### Setup and expected behavior

- Create a Job whose Node affinity matches no Node.
- Wait until it is Unschedulable and its allocate skip counter increases.
- Verify its task remains unbound.
- While that Job remains cached, create a second Job with no blocking constraint.
- Verify the second Job reaches `minAvailable` within one minute.
- Verify the first Job remains unbound.

This proves cache decisions remain scoped to the rejected Job and do not suppress unrelated schedulable workloads.

## Case 10: A cached Job remains eligible for preemption

Spec name:

```text
does not suppress preemption for a cached high-priority Job
```

### Setup and expected behavior

- Fill the only schedulable CPU slot with a preemptable low-priority Job.
- Create a high-priority Job requesting that slot while the scheduler runs
  `allocate` without `preempt`.
- Verify the high-priority Job becomes unschedulable, is skipped by the cache,
  and remains unbound.
- Enable the `preempt` action while the cache record still exists.
- Verify preemption selects the low-priority victim and the high-priority Job
  reaches Running or Succeeded.

This proves `preempt` continues to inspect cached Jobs even when `allocate` is
suppressed for them.

## Case 11: The watchdog retries a cached Job

Spec name:

```text
retries a cached Job after the watchdog duration expires
```

This spec temporarily rolls the scheduler with
`--unschedulable-job-cache-max-skip-duration=5s`, then restores the original
Deployment arguments during cleanup. The other specs and the production default
continue to use five minutes.

### Setup and expected behavior

- Create a Job with required Node affinity that no Node satisfies.
- Verify it becomes unschedulable and is subsequently skipped.
- Do not generate any matching Node event.
- Verify `volcano_unschedulable_job_cache_watchdog_expirations_total` increases
  for the Job within 30 seconds.
- Verify the still-blocked Job is evaluated, rejected, cached and skipped again.

The watchdog counter distinguishes timeout recovery from an event-driven wakeup.

## Feature-gate A/B comparison

The eleven E2E cases above verify correctness. To quantify the feature's benefit,
run the same unschedulable workload twice with only the feature gate changed.

### Controlled workload

Use the same values in both runs:

- Kind and Kubernetes versions;
- Volcano image and scheduler configuration;
- scheduler `--schedule-period`;
- number and size of Nodes;
- number of Jobs and replicas;
- observation duration.

A representative workload is 100 Jobs with 4 replicas each and required
NodeAffinity for a label that no Node has. All Jobs should become Unschedulable
but remain present during the observation window.

Run A:

```bash
FEATURE_GATES="UnschedulableJobCache=false" ./hack/run-e2e-kind.sh
```

Run B:

```bash
FEATURE_GATES="UnschedulableJobCache=true" ./hack/run-e2e-kind.sh
```

Prefer fresh Kind clusters for A and B. This prevents old Prometheus counters,
cached records, completed Jobs, and Node mutations from contaminating the
comparison.

### Measurement window

1. Create all Jobs.
2. Wait until every Job has reached Unschedulable at least once.
3. Read the metric baseline.
4. Keep the workload unchanged for a fixed interval, for example 60 seconds.
5. Read the same metrics again and calculate deltas.

Do not include Job creation and the first failed scheduling attempt in the
steady-state comparison: both feature configurations must perform that initial
evaluation.

### Primary metrics

Predicate executions:

```text
volcano_scheduling_stage_duration_milliseconds_count{stage="Predicate"}
```

The counter is incremented once per `PredicateNodes()` execution. During the
steady-state window:

- cache disabled: the delta should continue increasing as every scheduler
  session retries the blocked tasks;
- cache enabled: the delta should be near zero after the initial rejections are
  cached.

Accumulated predicate cost:

```text
volcano_scheduling_stage_duration_milliseconds_sum{stage="Predicate"}
```

Whole-session cost:

```text
volcano_e2e_scheduling_latency_milliseconds_count
volcano_e2e_scheduling_latency_milliseconds_sum
```

Calculate the average scheduling-session duration in the observation window:

```text
delta(e2e_scheduling_latency_milliseconds_sum)
------------------------------------------------
delta(e2e_scheduling_latency_milliseconds_count)
```

Cache activity, used as a validity check for run B:

```text
volcano_unschedulable_job_cache_skips_total{stage="allocate"}
```

This counter must increase in run B and must be absent or remain zero in run A.

### Optional process-level metrics

If collected by the scheduler metrics endpoint, also compare deltas for:

```text
process_cpu_seconds_total
process_resident_memory_bytes
go_goroutines
```

CPU is expected to decrease. Memory may increase slightly because the feature
stores rejections and reverse indexes; report this trade-off rather than
expecting memory to decrease.

### Calculated result

For each cumulative counter, use the delta between the end and baseline rather
than the absolute value. Report predicate-work reduction as:

```text
1 - predicate_count_delta_enabled / predicate_count_delta_disabled
```

Example:

```text
disabled predicate count delta: 24,000
enabled predicate count delta:      80
reduction:                       99.67%
```

The exact reduction depends on the scheduler period and observation timing, but
the enabled run should show an order-of-magnitude reduction for a stable set of
unschedulable Jobs.

### Correctness after the steady-state window

After measuring, add the previously missing Node label. For run B:

- `volcano_unschedulable_job_cache_wakeups_total{resource="Node"}` must increase;
- the Jobs must become schedulable within one minute, before watchdog expiry.

This proves the optimization reduces redundant retries without sacrificing
event-driven recovery.

### A/B acceptance criteria

An automated reviewer should require:

1. Both runs use identical workload and timing parameters.
2. Every Job was observed Unschedulable before the baseline was recorded.
3. Run B's allocate skip counter increased.
4. Run B's predicate count delta is materially lower than run A's; use at least
   90% reduction as a practical default threshold for a stable synthetic
   workload.
5. Run B's predicate duration sum is lower than run A's.
6. After the matching Node event, run B records a wakeup and schedules the Jobs
   within one minute.
7. Any memory increase is reported alongside the CPU/predicate reduction.

## Pod-churn dispatch cost experiment

This experiment evaluates the concern raised in the design review: resource
indexing avoids running Pod hints for Jobs that do not subscribe to Pod events,
but one `Pod/Delete` still considers every cached Job that does subscribe to Pod
events. If $N_{pod}$ Jobs subscribe to Pod events arriving at rate $R_{pod}$,
the dispatch upper bound is:

```text
O(N_pod * R_pod)
```

This does not automatically mean the cache regresses. A hint is much cheaper
than a full node scan, and a Job that wakes is removed from the reverse index
until it is evaluated and cached again. The break-even point must therefore be
measured rather than inferred from invocation count alone.

### Codex task constraints

- Run this experiment from
  `JesseStutler/volcano:unschedulable-job-cache-impl-e2e-validation`.
- Do not commit generated manifests, workload generators, raw metrics, profiles,
  logs, or experimental instrumentation.
- Put all temporary files under `$TMPDIR/unschedulable-cache-churn/` and write
  the final Markdown report there as `RESULTS.md`.
- Use a fresh Kind cluster for every feature-gate A/B pair, or fully recreate
  the scheduler, namespace, Jobs, PodGroups, churn Pods, and metric baselines.
- Keep the scheduler watchdog at its default five minutes. Every measurement
  window must finish before watchdog expiry.
- Do not change scheduler actions, plugins, node resources, or schedule period
  between the disabled and enabled run of one matrix point.

### Workload under test

Create $N$ one-task Volcano Jobs that cannot fit on any Node because each Task's
CPU request is greater than every Node's allocatable CPU. This intentionally
produces `predicates-resource-fit` rejections, whose provider subscribes to
`Pod/Delete`.

Requirements:

1. Use `minAvailable=1` and one pending Task per Job.
2. Confirm every Job has produced an Unschedulable result.
3. With the feature enabled, confirm the allocate skip counter has increased
   before starting churn.
4. Keep the Jobs and their PodGroups present for the whole measurement window.
5. Configure a measurement window of 60 seconds after a 20-second warm-up.

Generate churn with short-lived Pods that set `spec.nodeName` directly. Direct
binding avoids adding scheduler placement work to the event-source workload.
Use unique Pod names and record successful creates/deletes so the report uses
the achieved deletion rate, not only the requested rate.

Run two churn modes:

1. **Unrelated-dimension churn**: rejected Jobs request CPU only; churn Pods
   request memory only. Every deletion reaches subscribed Jobs, but the
   resource-fit hint should return `HintSkip`. This isolates dispatch, Job clone,
   subscription matching, and lightweight hint cost without expected wakeups.
2. **Relevant-dimension churn**: rejected Jobs request CPU; churn Pods request a
   small amount of CPU. Their deletion can return `HintWakeup`, causing Jobs to
   be re-evaluated and cached again. This measures dispatch plus false-positive
   wake/re-filter/recache cost under sustained resource release.

Ensure churn Pods are observed by the scheduler informer before deletion. Batch
creation/deletion is acceptable, but the report must include the achieved
deletions per second and failed API operations.

### Test matrix

Run the smoke matrix first:

| Cached Jobs $N$ | Requested deletes/s $R$ | Churn modes | Feature gate |
|---:|---:|---|---|
| 100 | 0, 1, 10, 50 | unrelated, relevant | off, on |
| 500 | 0, 1, 10, 50 | unrelated, relevant | off, on |
| 1000 | 0, 1, 10, 50 | unrelated, relevant | off, on |

If the machine and API server remain stable, add $N=5000$ for $R=0,10,50$.
Repeat every non-zero churn point three times. Randomize whether the disabled or
enabled run is performed first to reduce warm-cache and host-load bias.

$R=0$ is the static baseline and must reproduce the expected benefit of avoiding
periodic filter retries. The non-zero values identify where event processing
erodes or reverses that benefit.

### Metrics collection

Discover the scheduler Service and save each metrics snapshot:

```bash
SVC=$(kubectl -n volcano-system get svc -l app=volcano-scheduler \
  -o jsonpath='{.items[0].metadata.name}')
kubectl get --raw \
  "/api/v1/namespaces/volcano-system/services/http:${SVC}:8080/proxy/metrics" \
  > "$TMPDIR/unschedulable-cache-churn/metrics-${RUN}-${POINT}.txt"
```

Capture a baseline immediately before the 60-second window and an end snapshot
immediately afterward. Calculate deltas for counters and report start/end or
maximum values for gauges.

Required metrics:

```text
process_cpu_seconds_total
process_resident_memory_bytes
go_goroutines
volcano_scheduling_stage_duration_milliseconds_count{stage="Predicate"}
volcano_scheduling_stage_duration_milliseconds_sum{stage="Predicate"}
volcano_e2e_scheduling_latency_milliseconds_count
volcano_e2e_scheduling_latency_milliseconds_sum
volcano_unschedulable_job_cache_skips_total{stage="allocate"}
volcano_unschedulable_job_cache_wakeups_total{resource="Pod"}
```

Also report:

- actual successful Pod deletions and achieved deletes/s;
- number of Jobs still pending at the end;
- scheduler restarts and error-log count;
- API create/delete failures;
- wall-clock duration.

The wakeup metric is not a hint-invocation counter: it increments only when an
event actually invalidates a record. Do not use it as $N_{pod} * R_{pod}$.

### CPU profiles

For at least these points, collect a 30-second scheduler CPU profile in both A
and B runs:

- $N=1000$, $R=0$;
- $N=1000$, $R=50$, unrelated-dimension churn;
- $N=1000$, $R=50$, relevant-dimension churn.

Temporarily enable the scheduler pprof endpoint if needed, wait for rollout,
then collect through the scheduler Service and save both the raw profile and
`go tool pprof -top` output. The profile analysis must report samples attributed
to cache/event paths such as `OnEvent`, `shouldWake`, `getJobInfo`/`Clone`, and
the resource-fit Pod hint, along with predicate/filter paths.

If exact hint invocation counts are needed, Codex may add a temporary local
counter solely for this experiment. Keep the patch outside all commits and save
it next to `RESULTS.md` for review.

### Calculations

For every matrix point calculate:

```text
cpu_ratio = cpu_seconds_delta_enabled / cpu_seconds_delta_disabled
cpu_change = 1 - cpu_ratio

predicate_ratio = predicate_count_delta_enabled / predicate_count_delta_disabled

average_session_ms =
  delta(e2e_scheduling_latency_milliseconds_sum) /
  delta(e2e_scheduling_latency_milliseconds_count)
```

For repeated points report median and range. Do not compare absolute cumulative
counter values between clusters.

### Results table

`RESULTS.md` must contain one row per run and one aggregate row per matrix point:

| N | Requested R | Actual R | Mode | Cache | CPU delta | Predicate count delta | Predicate ms delta | Avg session ms | Skips | Pod wakeups | RSS end | Errors |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|

Include host CPU/memory, Kind/Kubernetes versions, Volcano commit, scheduler
configuration, Node allocatable, Job request, and generator source in an appendix.

### Interpretation and recommendation

Classify each target matrix point:

- **Net win**: enabled CPU is lower and average session latency does not regress
  by more than 10%.
- **Neutral**: CPU change is within +/-10% and no material latency regression.
- **Regression**: enabled CPU is more than 10% higher, average session latency is
  more than 10% higher, the scheduler restarts, or the API/event backlog grows.

Do not use these percentages as merge gates before realistic cluster values for
$N$ and $R$ are agreed. They are triage thresholds for choosing the next design.

The report must recommend one of:

1. **Keep the current resource index** when the cache remains a net win at the
   realistic $N/R$ points and profiles show hint cost is small.
2. **Add event coalescing/debouncing** when bursts dominate and many equivalent
   Pod deletes are processed before the next scheduling session.
3. **Add a secondary index** (for example Queue or requested resource dimension)
   when unrelated subscribed Jobs dominate each event's cost.
4. **Combine coalescing and secondary indexing** when both burst rate and
   candidate fan-out cause material regressions.

For any proposed optimization, explain its correctness boundary: events may
cause extra retries, but must not suppress a wake that could make a Job
schedulable. Include the raw data and profiles before recommending code changes.

## Automated result-checking checklist

An automated reviewer should verify all of the following:

1. The command exits with status 0.
2. Ginkgo ran exactly eleven specs and all passed.
3. No spec took five minutes waiting for the cache watchdog.
4. Both quota plugins passed all three plugin-specific cases.
5. Cases 1-2 observed `stage="enqueue"` skips, Queue wakeups, and successful
   Job scheduling after capability increased.
6. Cases 3-4 first observed the PodGroup in `Inqueue`, then observed
   `stage="allocate"` skips, Queue wakeups, and successful Task scheduling.
7. Cases 5-6 observed allocate skips, Pod wakeups, and successful Task
   scheduling after the quota-consuming Pod was deleted.
8. Case 7 observed an allocate skip counter increment before patching the Node.
9. Case 7 scheduled both replicas specifically onto the patched Node and
   satisfied `minAvailable=2`.
10. Case 7 observed a Node-event wakeup counter increment after patching the
  Node.
11. Case 8 observed an allocate skip before deleting the blocker Pod, a Pod
  wakeup afterward, and successful scheduling within one minute.
12. Case 9 observed a cache skip for the blocked Job while the normal Job
  scheduled successfully and the blocked Job remained unbound.
13. Case 10 observed the high-priority Job cached before preemption and then
  scheduled it by evicting the low-priority victim.
14. Case 11 observed watchdog expiration without a matching event and a later
  cache skip proving the Job was retried.
15. No scheduler ConfigMap, namespace, Queue, PodGroup, blocker Pod, placeholder
  Pod, or temporary Node label cleanup error occurred.
16. The scheduler was installed with `UnschedulableJobCache=true`; Case 11 alone
  temporarily used a 5-second max skip duration and restored the Deployment.

## Useful diagnostics

Check scheduler feature-gate arguments:

```bash
kubectl -n volcano-system get pods -l app=volcano-scheduler \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{.spec.containers[0].args}{"\n"}{end}'
```

Inspect cache behavior metrics:

```bash
kubectl get --raw \
  '/api/v1/namespaces/volcano-system/services/http:integration-scheduler-service:8080/proxy/metrics' \
  | grep -E 'volcano_unschedulable_job_cache_(skips|wakeups)_total'
```

Run only one spec while debugging:

```bash
KUBECONFIG="$KUBECONFIG" ginkgo -v \
  --focus='Quota plugin hints proportion' \
  ./test/e2e/unschedulablejobcache/
```

or:

```bash
KUBECONFIG="$KUBECONFIG" ginkgo -v \
  --focus='Generic event hints and cache behavior' \
  ./test/e2e/unschedulablejobcache/
```

## Mandatory cleanup before final submission

After manual or automated validation succeeds:

```bash
git log --oneline -5
```

Find the commit with subject:

```text
TEMP(DROP BEFORE SUBMIT): add unschedulable cache e2e validation guide
```

Drop that commit, then confirm:

```bash
test ! -e UNSCHEDULABLE_JOB_CACHE_E2E_VALIDATION.md
git status --short
```

The final PR must contain the core implementation commit and the E2E test commit, but must not contain this temporary validation-document commit.
