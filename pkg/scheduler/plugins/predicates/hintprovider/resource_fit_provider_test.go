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

package hintprovider

import (
	"testing"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/klog/v2"
	"volcano.sh/volcano/pkg/scheduler/api"
)

func TestResourceFitPodHint(t *testing.T) {
	targetPod := podWithCPU("target", "2")
	task := api.NewTaskInfo(targetPod)
	job := api.NewJobInfo("job", task)
	rejection := api.Rejection{Tasks: []api.TaskID{task.UID}}

	tests := []struct {
		name     string
		oldPod   *v1.Pod
		newPod   *v1.Pod
		expected api.HintResult
	}{
		{
			name:     "scheduled pod deletion frees resources",
			oldPod:   scheduledPodWithCPU("deleted", "1"),
			expected: api.HintWakeup,
		},
		{
			name:     "unscheduled pod deletion does not free node resources",
			oldPod:   podWithCPU("deleted", "1"),
			expected: api.HintSkip,
		},
		{
			name:     "rejected pending pod deletion changes the job",
			oldPod:   podWithCPU("target", "2"),
			expected: api.HintWakeup,
		},
		{
			name:     "rejected pending pod request decreases",
			oldPod:   podWithCPU("target", "2"),
			newPod:   podWithCPU("target", "1"),
			expected: api.HintWakeup,
		},
		{
			name:     "scheduled pod request decreases",
			oldPod:   scheduledPodWithCPU("resized", "2"),
			newPod:   scheduledPodWithCPU("resized", "1"),
			expected: api.HintWakeup,
		},
		{
			name:     "scheduled pod update does not change resources",
			oldPod:   scheduledPodWithCPU("updated", "1"),
			newPod:   scheduledPodWithCPU("updated", "1"),
			expected: api.HintSkip,
		},
		{
			name:   "scheduled pod terminates",
			oldPod: scheduledPodWithCPU("completed", "1"),
			newPod: func() *v1.Pod {
				pod := scheduledPodWithCPU("completed", "1")
				pod.Status.Phase = v1.PodSucceeded
				return pod
			}(),
			expected: api.HintWakeup,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var newObj any
			if test.newPod != nil {
				newObj = test.newPod
			}
			result, err := resourceFitPodHint(klog.Background(), job, rejection, test.oldPod, newObj)
			if err != nil {
				t.Fatalf("resourceFitPodHint() error = %v", err)
			}
			if result != test.expected {
				t.Fatalf("resourceFitPodHint() = %v, want %v", result, test.expected)
			}
		})
	}
}

func TestResourceFitNodeHint(t *testing.T) {
	task := api.NewTaskInfo(podWithCPU("target", "2"))
	job := api.NewJobInfo("job", task)
	rejection := api.Rejection{Tasks: []api.TaskID{task.UID}}

	oldNode := nodeWithResources("1", "1Gi")
	cpuIncreased := nodeWithResources("2", "1Gi")
	memoryIncreased := nodeWithResources("1", "2Gi")

	result, err := resourceFitNodeHint(klog.Background(), job, rejection, oldNode, cpuIncreased)
	if err != nil {
		t.Fatalf("resourceFitNodeHint() error = %v", err)
	}
	if result != api.HintWakeup {
		t.Fatalf("resourceFitNodeHint() = %v, want %v", result, api.HintWakeup)
	}

	result, err = resourceFitNodeHint(klog.Background(), job, rejection, oldNode, memoryIncreased)
	if err != nil {
		t.Fatalf("resourceFitNodeHint() error = %v", err)
	}
	if result != api.HintSkip {
		t.Fatalf("resourceFitNodeHint() = %v, want %v", result, api.HintSkip)
	}

	result, err = resourceFitNodeHint(klog.Background(), job, rejection, nil, oldNode)
	if err != nil {
		t.Fatalf("resourceFitNodeHint() error = %v", err)
	}
	if result != api.HintWakeup {
		t.Fatalf("resourceFitNodeHint() for node add = %v, want %v", result, api.HintWakeup)
	}
}

func podWithCPU(name, cpu string) *v1.Pod {
	return &v1.Pod{
		ObjectMeta: metav1.ObjectMeta{Name: name, UID: types.UID("uid-" + name)},
		Spec: v1.PodSpec{Containers: []v1.Container{{
			Name: "container",
			Resources: v1.ResourceRequirements{Requests: v1.ResourceList{
				v1.ResourceCPU: resource.MustParse(cpu),
			}},
		}}},
	}
}

func scheduledPodWithCPU(name, cpu string) *v1.Pod {
	pod := podWithCPU(name, cpu)
	pod.Spec.NodeName = "node"
	return pod
}

func nodeWithResources(cpu, memory string) *v1.Node {
	return &v1.Node{Status: v1.NodeStatus{Allocatable: v1.ResourceList{
		v1.ResourceCPU:    resource.MustParse(cpu),
		v1.ResourceMemory: resource.MustParse(memory),
	}}}
}
