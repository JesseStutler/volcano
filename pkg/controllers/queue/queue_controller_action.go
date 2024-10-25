/*
Copyright 2019 The Volcano Authors.

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

package queue

import (
	"context"
	"fmt"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/klog/v2"

	"volcano.sh/apis/pkg/apis/bus/v1alpha1"
	schedulingv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	v1beta1apply "volcano.sh/apis/pkg/client/applyconfiguration/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/controllers/metrics"
	"volcano.sh/volcano/pkg/controllers/queue/state"
)

// syncQueue will record the number of podgroups of each state in the queues as metrics and update the state of the queue if updateStateFn is not nil.
func (c *queuecontroller) syncQueue(queue *schedulingv1beta1.Queue, action v1alpha1.Action, updateStateFn state.UpdateQueueStatusFn) error {
	klog.V(4).Infof("Begin to sync queue %s.", queue.Name)
	defer klog.V(4).Infof("End sync queue %s.", queue.Name)

	podGroups := c.getPodGroups(queue.Name)
	newQueueStatus := schedulingv1beta1.QueueStatus{}

	for _, pgKey := range podGroups {
		// Ignore error here, tt can not occur.
		ns, name, _ := cache.SplitMetaNamespaceKey(pgKey)

		pg, err := c.pgLister.PodGroups(ns).Get(name)
		if err != nil {
			if !errors.IsNotFound(err) {
				return err
			}

			klog.V(4).Infof("The podGroup %s is not found, skip it and continue to sync cache", pgKey)
			c.pgMutex.Lock()
			delete(c.podGroups[queue.Name], pgKey)
			c.pgMutex.Unlock()
			continue
		}

		switch pg.Status.Phase {
		case schedulingv1beta1.PodGroupPending:
			newQueueStatus.Pending++
		case schedulingv1beta1.PodGroupRunning:
			newQueueStatus.Running++
		case schedulingv1beta1.PodGroupUnknown:
			newQueueStatus.Unknown++
		case schedulingv1beta1.PodGroupInqueue:
			newQueueStatus.Inqueue++
		case schedulingv1beta1.PodGroupCompleted:
			newQueueStatus.Completed++
		}
	}

	// Update the metrics
	metrics.UpdatePgPendingPhaseNum(queue.Name, float64(newQueueStatus.Pending))
	metrics.UpdatePgRunningPhaseNum(queue.Name, float64(newQueueStatus.Running))
	metrics.UpdatePgUnknownPhaseNum(queue.Name, float64(newQueueStatus.Unknown))
	metrics.UpdatePgInqueuePhaseNum(queue.Name, float64(newQueueStatus.Inqueue))
	metrics.UpdatePgCompletedPhaseNum(queue.Name, float64(newQueueStatus.Completed))

	if updateStateFn != nil {
		updateStateFn(&newQueueStatus, podGroups)
	} else {
		newQueueStatus.State = queue.Status.State
	}

	newQueueStatus.Allocated = queue.Status.Allocated.DeepCopy()
	// queue.status.allocated will be updated after every session close in volcano scheduler, we should not depend on it because session may be time-consuming,
	// and queue.status.allocated can't be updated timely. We initialize queue.status.allocated and update it here explicitly
	// to avoid update queue err because update will fail when queue.status.allocated is nil.
	if newQueueStatus.Allocated == nil {
		newQueueStatus.Allocated = v1.ResourceList{}
	}

	// ignore update when status does not change
	if equality.Semantic.DeepEqual(newQueueStatus, queue.Status) {
		return nil
	}

	queueStatusApply := v1beta1apply.QueueStatus().WithState(newQueueStatus.State).WithAllocated(newQueueStatus.Allocated)
	queueApply := v1beta1apply.Queue(queue.Name).WithStatus(queueStatusApply)
	if _, err := c.vcClient.SchedulingV1beta1().Queues().ApplyStatus(context.TODO(), queueApply, metav1.ApplyOptions{FieldManager: controllerName}); err != nil {
		errMsg := fmt.Sprintf("Update queue state from %s to %s failed for %v", queue.Status.State, newQueueStatus.State, err)
		c.recorder.Event(queue, v1.EventTypeWarning, string(action), errMsg)
		klog.Errorf(errMsg)
		return err
	}

	return nil
}
