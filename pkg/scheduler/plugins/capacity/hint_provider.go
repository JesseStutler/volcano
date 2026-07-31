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

package capacity

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/klog/v2"
	fwk "k8s.io/kube-scheduler/framework"

	batch "volcano.sh/apis/pkg/apis/batch/v1alpha1"
	"volcano.sh/apis/pkg/apis/scheduling"
	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"

	"volcano.sh/volcano/pkg/scheduler/api"
)

// EventsToRegister implements api.HintProvider. A Job rejected by capacity is
// blocked by its own queue's or an ancestor's quota, so it can only become
// schedulable when quota frees within that queue scope: an update to a scoped
// Queue, a PodGroup in a scoped queue releasing resources, or a Pod in a scoped
// queue being deleted.
func (cp *capacityPlugin) EventsToRegister(_ context.Context) ([]api.ClusterEventWithHint, error) {
	return []api.ClusterEventWithHint{
		{Event: api.ClusterEvent{Resource: api.QueueEvent, ActionType: fwk.Update}, HintFn: queueHint},
		{Event: api.ClusterEvent{Resource: api.PodGroupEvent, ActionType: fwk.Update | fwk.Delete}, HintFn: podGroupHint},
		{Event: api.ClusterEvent{Resource: fwk.Pod, ActionType: fwk.Delete}, HintFn: podHint},
	}, nil
}

// queueInScope reports whether the named queue is the Job's queue or one of its
// ancestors, using the scope recorded on the rejection (falling back to the
// Job's own queue when no scope was recorded).
func queueInScope(rejection api.Rejection, queueName string, jobQueue api.QueueID) bool {
	qid := api.QueueID(queueName)
	if len(rejection.Queues) == 0 {
		return qid == jobQueue
	}
	for _, q := range rejection.Queues {
		if q == qid {
			return true
		}
	}
	return false
}

// queueHint wakes a Job when a Queue within its scope is updated, since only
// then can the queue's capability, deserved, guarantee, or open state change in
// the Job's favor.
func queueHint(_ klog.Logger, job *api.JobInfo, rejection api.Rejection, _, newObj any) (api.HintResult, error) {
	queue, ok := newObj.(*scheduling.Queue)
	if !ok || queue == nil {
		return api.HintWakeup, nil
	}
	if queueInScope(rejection, queue.Name, job.Queue) {
		return api.HintWakeup, nil
	}
	return api.HintSkip, nil
}

// podGroupHint wakes a Job when a PodGroup within its queue scope releases quota:
// a delete removes the PodGroup's demand entirely, and an update matters only
// when the PodGroup leaves a resource-consuming phase.
func podGroupHint(_ klog.Logger, job *api.JobInfo, rejection api.Rejection, oldObj, newObj any) (api.HintResult, error) {
	// Delete: oldObj holds the removed PodGroup, newObj is nil.
	if newObj == nil {
		pg, ok := oldObj.(*api.PodGroup)
		if !ok || pg == nil {
			return api.HintWakeup, nil
		}
		if queueInScope(rejection, pg.Spec.Queue, job.Queue) {
			return api.HintWakeup, nil
		}
		return api.HintSkip, nil
	}

	newPg, ok := newObj.(*api.PodGroup)
	if !ok || newPg == nil {
		return api.HintWakeup, nil
	}
	if !queueInScope(rejection, newPg.Spec.Queue, job.Queue) {
		return api.HintSkip, nil
	}
	if podGroupReleasedQuota(oldObj, newPg) {
		return api.HintWakeup, nil
	}
	return api.HintSkip, nil
}

// podGroupReleasedQuota reports whether newPg has left a resource-consuming
// phase (Inqueue/Running) relative to its previous state, freeing queue quota.
func podGroupReleasedQuota(oldObj any, newPg *api.PodGroup) bool {
	if consumingPhase(newPg.Status.Phase) {
		return false
	}
	oldPg, ok := oldObj.(*api.PodGroup)
	if !ok || oldPg == nil {
		return true
	}
	return consumingPhase(oldPg.Status.Phase)
}

func consumingPhase(phase scheduling.PodGroupPhase) bool {
	return phase == scheduling.PodGroupInqueue || phase == scheduling.PodGroupRunning
}

// podHint wakes a Job when a Pod within its queue scope is deleted, freeing that
// queue's allocated quota. The Pod's queue is read from the annotations the job
// and podgroup controllers stamp on every managed Pod; a Pod whose queue cannot
// be determined wakes the Job conservatively rather than risk keeping it cached.
func podHint(_ klog.Logger, job *api.JobInfo, rejection api.Rejection, oldObj, _ any) (api.HintResult, error) {
	pod, ok := oldObj.(*v1.Pod)
	if !ok || pod == nil {
		return api.HintWakeup, nil
	}
	queue := podQueue(pod)
	if queue == "" {
		return api.HintWakeup, nil
	}
	if queueInScope(rejection, queue, job.Queue) {
		return api.HintWakeup, nil
	}
	return api.HintSkip, nil
}

// podQueue returns the queue a Pod belongs to, read from the annotations set by
// the job controller (batch.QueueNameKey) or the podgroup mutating webhook
// (scheduling.QueueNameAnnotationKey). It returns "" when neither is present.
func podQueue(pod *v1.Pod) string {
	if q, ok := pod.Annotations[batch.QueueNameKey]; ok && q != "" {
		return q
	}
	if q, ok := pod.Annotations[schedulingv1beta1.QueueNameAnnotationKey]; ok && q != "" {
		return q
	}
	return ""
}
