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

package cache

import (
	"fmt"
	"testing"

	fwk "k8s.io/kube-scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
)

// BenchmarkUnschedulableJobCacheHintSkipDispatch measures the sustained-event
// fanout path: every cached Job subscribes to the event, and every hint decides
// that the event is irrelevant. This deliberately uses a synthetic hint instead
// of resource-fit: real Pods always request one v1.ResourcePods slot, so a Pod
// deletion cannot model a resource-fit event that releases no requested resource.
func BenchmarkUnschedulableJobCacheHintSkipDispatch(b *testing.B) {
	for _, jobs := range []int{100, 500, 1000, 5000} {
		b.Run(fmt.Sprintf("jobs=%d", jobs), func(b *testing.B) {
			benchmarkHintSkipDispatch(b, jobs)
		})
	}
}

func BenchmarkUnschedulableJobCacheRecord(b *testing.B) {
	for _, tasks := range []int{1, 4, 16, 64} {
		b.Run(fmt.Sprintf("tasks=%d", tasks), func(b *testing.B) {
			benchmarkRecordUnschedulable(b, tasks)
		})
	}
}

func benchmarkRecordUnschedulable(b *testing.B, taskCount int) {
	const plugin = "benchmark-record"
	registry := NewHintRegistry()
	cache := NewUnschedulableJobCache(registry, DefaultMaxSkipDuration)
	event := api.ClusterEvent{Resource: fwk.Pod, ActionType: fwk.Delete}
	registerTestHint(registry, plugin, event, nil)

	job := api.NewJobInfo("benchmark/job")
	job.Name = "job"
	job.Namespace = "benchmark"
	taskIDs := make([]api.TaskID, 0, taskCount)
	for i := 0; i < taskCount; i++ {
		taskID := api.TaskID(fmt.Sprintf("task-%d", i))
		taskIDs = append(taskIDs, taskID)
		request := &api.Resource{MilliCPU: 1000, Memory: 1024}
		job.AddTaskInfo(&api.TaskInfo{
			UID:        taskID,
			Job:        job.UID,
			Name:       string(taskID),
			Namespace:  job.Namespace,
			Resreq:     request.Clone(),
			InitResreq: request.Clone(),
			NumaInfo:   &api.TopologyInfo{},
			TransactionContext: api.TransactionContext{
				Status: api.Pending,
			},
		})
	}
	rejections := []api.Rejection{{Plugin: plugin, Source: api.RejectionPredicate, Tasks: taskIDs}}

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.RecordUnschedulable(job, rejections)
	}
}

func benchmarkHintSkipDispatch(b *testing.B, jobCount int) {
	const plugin = "benchmark-skip"
	registry := NewHintRegistry()
	cache := NewUnschedulableJobCache(registry, DefaultMaxSkipDuration)
	event := api.ClusterEvent{Resource: fwk.Pod, ActionType: fwk.Delete}
	registerTestHint(registry, plugin, event, func(job *api.JobInfo, rejection api.Rejection, _, _ any) (api.HintResult, error) {
		// Touch the task data used by real hints so the benchmark includes the
		// record-snapshot lookup rather than measuring an empty callback alone.
		_ = job.Tasks[rejection.Tasks[0]].InitResreq.MilliCPU
		return api.HintSkip, nil
	})

	for i := 0; i < jobCount; i++ {
		jobID := api.JobID(fmt.Sprintf("job-%d", i))
		taskID := api.TaskID(fmt.Sprintf("task-%d", i))
		request := &api.Resource{MilliCPU: 1000}
		task := &api.TaskInfo{
			UID:        taskID,
			Job:        jobID,
			Name:       string(taskID),
			Namespace:  "benchmark",
			Resreq:     request.Clone(),
			InitResreq: request.Clone(),
			NumaInfo:   &api.TopologyInfo{},
			TransactionContext: api.TransactionContext{
				Status: api.Pending,
			},
		}
		job := api.NewJobInfo(jobID, task)
		job.Name = string(jobID)
		job.Namespace = "benchmark"
		cache.RecordUnschedulable(job, []api.Rejection{{
			Plugin: plugin,
			Source: api.RejectionPredicate,
			Tasks:  []api.TaskID{taskID},
		}})
	}

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.OnEvent(event, nil, nil)
	}
}
