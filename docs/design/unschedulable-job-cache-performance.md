# Unschedulable Job Cache Performance Validation

This document records the local performance experiments used to evaluate the
Unschedulable Job Cache and its optional secondary candidate index. It separates
three different measurements: end-to-end scheduler behavior, event-dispatch
fan-out, and the cost of one hint compared with one predicate evaluation.

The results are directional rather than merge thresholds. End-to-end secondary-
index runs are one A/B pair per scheduler configuration; microbenchmarks use five
one-second repetitions.

## Cost model

Without precise HintKey selection, an event delivered to `N` Jobs in a matching
plugin/action index has the following upper-bound dispatch cost at event rate
`R`:

```text
R * N * T_hint
```

With the secondary index, only `K` candidate Jobs selected by the event's
necessary-condition keys reach the final HintFn:

```text
R * (T_index + K * T_hint), where K <= N
```

The complete comparison also includes the periodic work avoided by caching. At
session rate `S`, repeatedly evaluating unchanged unschedulable Jobs costs on
the order of:

```text
S * N * T_predicate
```

For event processing to keep up, the complete per-event cost
`T_index + K * T_hint` must be well below the inter-event interval `1/R`; it is
not sufficient to compare one HintFn invocation with `1/R`. If a hint genuinely
wakes a Job, the subsequent predicate evaluation is necessary scheduling work.
The optimization targets unrelated candidates and false-positive wakeups.

## Environment and workloads

The tests ran on an AMD EPYC 9845 host with 31 GiB memory. The end-to-end tests
used Kind v0.31.0, Kubernetes v1.34.0, a single 16-CPU Node, a one-second
scheduler period, and scheduler QPS/burst 5000/10000.

The initial cache implementation and Clone/lock optimization were tested at
commit `25e821762`. The secondary-index tests used PR 19 head `054bf1d72`, which
contains that optimization plus the generic and provider-specific indexes.

Two end-to-end workloads were used:

1. **Continuous schedulable workload:** 50 high-priority Gang Jobs with 20
   replicas and `minAvailable=16` (15 fit tasks and 5 impossible tasks), while
   750 low-priority four-replica Gang Jobs were submitted at 150 Jobs/s.
2. **Pod Delete churn:** 1,000 one-task Jobs each requested 100 CPUs on a
   16-CPU Node. Directly bound 100m-CPU Pods were created and deleted at 50/s.
   Each A/B run used a 20-second warm-up and 60-second measurement window.

The second workload deliberately makes every churn deletion irrelevant to
Resource Fit: releasing 100m CPU cannot make a 100-CPU task fit on a 16-CPU
Node. It is the extreme Delete scenario raised during design review.

## End-to-end cache benefit

The continuous schedulable-workload experiment includes the Clone/lock
optimization but predates the secondary index. It demonstrates the throughput
benefit of suppressing unchanged head-of-line Jobs while new schedulable Jobs
continue to arrive.

| Metric | Cache off | Cache on | Change |
|---|---:|---:|---:|
| Job throughput | 87.07/s | 127.84/s | +46.8% |
| Pod throughput | 348.26/s | 511.37/s | +46.8% |
| Job latency P95 | 3.668s | 2.136s | -41.8% |
| Average session | 1.818s | 0.771s | -57.6% |
| Predicate calls | 6,711 | 3,000 | -55.3% |
| Scheduler CPU | 11.36s | 6.05s | -46.7% |

This is the most representative throughput experiment so far: the cache does
not merely reduce empty-session work; it leaves more scheduler capacity for
continuously submitted, lower-priority schedulable Jobs.

## Secondary-index Pod Delete experiment

### Resource-Fit-only configuration

This configuration removed `proportion` so Jobs reached Volcano's built-in
Resource Fit check. The index records the rejected node, insufficient resource
dimensions, and whether a Pod release can ever make the task fit.

| Metric | Cache off | Cache on | Change |
|---|---:|---:|---:|
| Scheduler CPU / 60s | 26.90s | 17.88s | -33.5% |
| Average session | 182.16ms | 23.71ms | -87.0% (7.68x) |
| Sessions | 50 | 59 | +9 |
| Predicate count | 50,801 | 0 | -100% |
| Predicate duration sum | 2,114.3ms | 0 | -100% |
| Allocate skips | 0 | 59,000 | +59,000 |
| Pod wakeups | 0 | 0 | unchanged |
| RSS at window end | 114.83MiB | 145.72MiB | +30.89MiB |

The churn events selected no Resource Fit candidates (`K=0`) because the task
request exceeded total Node allocatable. The index therefore prevented both
HintFn fan-out and false-positive wakeups. The memory increase is the cost of
retaining 1,000 Job snapshots, rejections, and bounded index keys.

### Default configuration including proportion

| Metric | Cache off | Cache on | Change |
|---|---:|---:|---:|
| Scheduler CPU / 60s | 23.24s | 24.20s | +4.1% |
| Average session | 127.87ms | 143.67ms | +12.4% |
| Sessions | 53 | 53 | unchanged |
| Allocate skips | 0 | 760 | +760 |
| Pod wakeups | 0 | 52,240 | +52,240 |
| RSS at window end | 112.45MiB | 123.63MiB | +11.18MiB |

Scheduler logs showed that `proportion` rejected the Jobs before Resource Fit.
Its attempted secondary key used only the released resource dimension, so one
CPU-releasing deletion matched nearly every CPU-blocked Job and recreated broad
wakeups. This test did not demonstrate a benefit from the proportion index.

No isolated end-to-end A/B experiment was completed for the capacity secondary
index. Capacity and proportion retain their existing correctness HintFns, but
their secondary indexes are excluded from the Alpha implementation until a
selective, measured design is available.

## Secondary-index microbenchmarks

The dispatch benchmark caches 5,000 Jobs across 100 deterministic HintKey groups.
Selectivity is the fraction of Jobs whose keys intersect one event; it is not a
cache hit rate or wakeup rate.

| Dispatch mode | Candidate selectivity | Median time/event | Relative to dispatch without HintKeys |
|---|---:|---:|---:|
| Dispatch without HintKeys | 100% (5,000 Jobs) | 1.00-1.02ms | 1x |
| Indexed | 1% (50 Jobs) | 7.85-7.98us | about 128x faster |
| Indexed | 10% (500 Jobs) | 90-92us | about 11x faster |
| Indexed | 100% (5,000 Jobs) | 1.04-1.07ms | about 4% slower |

The 100% case shows the bounded overhead when the index cannot reduce the
candidate set. The benefit is proportional to how much smaller `K` is than
`N`. A Job with missing, erroneous, or excessive keys is dispatched without
HintKeys; an event with erroneous or excessive keys selects every Job ID in its
plugin/action index.

Recording and replacing one Job's index entries costs:

| Keys | Time/op | Bytes/op | Allocations/op |
|---:|---:|---:|---:|
| 1 | 2.1us | 1,896B | 19 |
| 16 | 11.3us | 8,984B | 59 |
| 64 | 41.5us | 33,688B | 163 |
| 256 | 156-160us | 130,584B | 555 |
| 257 (dispatch without HintKeys) | 39us | 38,192B | 30 |

The limit bounds per-plugin-event memory and record-time work. Exceeding it
trades performance for correctness-preserving coarse dispatch.

## Hint cost versus predicate cost

The real Resource Fit Pod HintSkip benchmark measured about `0.496us` for one
one-task cached Job. In the Resource-Fit-only cache-off run, the Predicate metric
averaged `2,114.3ms / 50,801 = 41.62us` per `PredicateNodes()` invocation. That
is about an 84x difference for this one-Node test.

This comparison supports the reviewer's expected order-of-magnitude difference
between a hint and a full predicate attempt, but it is not a claim of 84x
end-to-end throughput. Likewise, the 128x dispatch result applies only to the
synthetic 1% candidate case. These ratios must not be multiplied.

The observed end-to-end improvements are 7.68x lower average session time in
the Resource-Fit-only churn test and 46.8% higher Job/Pod throughput in the
continuous schedulable-workload test.

## Conclusions

- The Clone/lock optimization makes dispatch without HintKeys inexpensive, and
  the secondary index changes the fan-out term from all subscribed Jobs `N` to
  the event-specific candidate set `K`.
- Resource Fit has both a selective necessary-condition key and demonstrated
  end-to-end benefit. It is the only provider-specific secondary index in the
  Alpha implementation.
- The extreme irrelevant Pod Delete workload no longer wakes Resource-Fit-
  blocked Jobs; in the measured case `K=0` and Pod wakeups remained zero.
- The generic index still supports future providers, but wrapped kube-scheduler,
  capacity, and proportion hints use coarse plugin/event dispatch in the first
  version.
- Capacity needs an isolated performance experiment. Proportion needs a more
  selective rejection signature before indexing; a resource-dimension-only key
  is insufficient.
- Memory increases must be considered alongside CPU and throughput. The largest
  measured increase was 30.89MiB for 1,000 indexed Resource-Fit records.
