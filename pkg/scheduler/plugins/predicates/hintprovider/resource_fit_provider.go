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
	"context"
	"fmt"

	v1 "k8s.io/api/core/v1"
	"k8s.io/klog/v2"
	fwk "k8s.io/kube-scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
)

const ResourceFitHintProviderName = "predicates-resource-fit"

type ResourceFitHintProvider struct{}

func (p *ResourceFitHintProvider) EventsToRegister(context.Context) ([]api.ClusterEventWithHint, error) {
	return []api.ClusterEventWithHint{
		{
			Event:  api.ClusterEvent{Resource: fwk.Pod, ActionType: fwk.Delete | fwk.Update},
			HintFn: resourceFitPodHint,
		},
		{
			Event:  api.ClusterEvent{Resource: fwk.Node, ActionType: fwk.Add | fwk.Update},
			HintFn: resourceFitNodeHint,
		},
	}, nil
}

func resourceFitPodHint(_ klog.Logger, job *api.JobInfo, rejection api.Rejection, oldObj, newObj any) (api.HintResult, error) {
	oldPod, ok := oldObj.(*v1.Pod)
	if !ok || oldPod == nil {
		return api.HintWakeup, fmt.Errorf("expected old object to be *v1.Pod, got %T", oldObj)
	}

	if newObj == nil {
		// 1. Deleting a rejected task changes the Job and triggers a retry.
		if rejectionIncludesPod(rejection, oldPod) {
			return api.HintWakeup, nil
		}

		// 2. Deleting an unrelated pending or terminated Pod frees no node
		// resources; deleting a scheduled Pod may free requested resources.
		if oldPod.Spec.NodeName == "" || podTerminated(oldPod) {
			return api.HintSkip, nil
		}
		return resourceChangeHint(job, rejection, api.EmptyResource(), api.GetPodResourceRequest(oldPod)), nil
	}

	newPod, ok := newObj.(*v1.Pod)
	if !ok || newPod == nil {
		return api.HintWakeup, fmt.Errorf("expected new object to be *v1.Pod, got %T", newObj)
	}

	// 3. Updating a Pod that was already terminated does not free resources.
	if podTerminated(oldPod) {
		return api.HintSkip, nil
	}

	// 4. Updating an unrelated pending Pod does not affect node resources.
	if oldPod.Spec.NodeName == "" && !rejectionIncludesPod(rejection, oldPod) {
		return api.HintSkip, nil
	}

	// 5. A Pod becoming terminal releases all of its requests; otherwise retry
	// only when the update reduces a resource requested by a rejected task.
	if podTerminated(newPod) {
		return resourceChangeHint(job, rejection, api.EmptyResource(), api.GetPodResourceRequest(oldPod)), nil
	}

	return resourceChangeHint(job, rejection, api.GetPodResourceRequest(newPod), api.GetPodResourceRequest(oldPod)), nil
}

func resourceFitNodeHint(_ klog.Logger, job *api.JobInfo, rejection api.Rejection, oldObj, newObj any) (api.HintResult, error) {
	newNode, ok := newObj.(*v1.Node)
	if !ok || newNode == nil {
		return api.HintWakeup, fmt.Errorf("expected new object to be *v1.Node, got %T", newObj)
	}
	// 1. A newly added Node may provide capacity for a rejected task.
	if oldObj == nil {
		return api.HintWakeup, nil
	}
	oldNode, ok := oldObj.(*v1.Node)
	if !ok || oldNode == nil {
		return api.HintWakeup, fmt.Errorf("expected old object to be *v1.Node, got %T", oldObj)
	}

	// 2. A Node update triggers a retry only when requested allocatable
	// resources increase.
	return resourceChangeHint(job, rejection, api.NewResource(oldNode.Status.Allocatable), api.NewResource(newNode.Status.Allocatable)), nil
}

func resourceChangeHint(job *api.JobInfo, rejection api.Rejection, before, after *api.Resource) api.HintResult {
	if job == nil || len(rejection.Tasks) == 0 {
		return api.HintWakeup
	}
	for _, taskID := range rejection.Tasks {
		task := job.Tasks[taskID]
		if task != nil && requestedResourceIncreased(task.InitResreq, before, after) {
			return api.HintWakeup
		}
	}
	return api.HintSkip
}

func requestedResourceIncreased(request, before, after *api.Resource) bool {
	if request == nil || before == nil || after == nil {
		return true
	}
	if request.MilliCPU > 0 && after.MilliCPU > before.MilliCPU {
		return true
	}
	if request.Memory > 0 && after.Memory > before.Memory {
		return true
	}
	for name, quantity := range request.ScalarResources {
		if quantity > 0 && after.ScalarResources[name] > before.ScalarResources[name] {
			return true
		}
	}
	return false
}

func podTerminated(pod *v1.Pod) bool {
	return pod.Status.Phase == v1.PodSucceeded || pod.Status.Phase == v1.PodFailed
}

func rejectionIncludesPod(rejection api.Rejection, pod *v1.Pod) bool {
	taskID := api.TaskID(pod.UID)
	for _, rejectedTaskID := range rejection.Tasks {
		if rejectedTaskID == taskID {
			return true
		}
	}
	return false
}
