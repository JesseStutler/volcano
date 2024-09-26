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

func (c *queuecontroller) syncQueue(queue *schedulingv1beta1.Queue, updateStateFn state.UpdateQueueStatusFn) error {
	klog.V(4).Infof("Begin to sync queue %s.", queue.Name)
	defer klog.V(4).Infof("End sync queue %s.", queue.Name)

	podGroups := c.getPodGroups(queue.Name)
	queueStatus := schedulingv1beta1.QueueStatus{}

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
			queueStatus.Pending++
		case schedulingv1beta1.PodGroupRunning:
			queueStatus.Running++
		case schedulingv1beta1.PodGroupUnknown:
			queueStatus.Unknown++
		case schedulingv1beta1.PodGroupInqueue:
			queueStatus.Inqueue++
		case schedulingv1beta1.PodGroupCompleted:
			queueStatus.Completed++
		}
	}

	// Update the metrics
	metrics.UpdatePgPendingPhaseNum(queue.Name, float64(queueStatus.Pending))
	metrics.UpdatePgRunningPhaseNum(queue.Name, float64(queueStatus.Running))
	metrics.UpdatePgUnknownPhaseNum(queue.Name, float64(queueStatus.Unknown))
	metrics.UpdatePgInqueuePhaseNum(queue.Name, float64(queueStatus.Inqueue))
	metrics.UpdatePgCompletedPhaseNum(queue.Name, float64(queueStatus.Completed))

	if updateStateFn != nil {
		updateStateFn(&queueStatus, podGroups)
	} else {
		queueStatus.State = queue.Status.State
	}

	queueStatus.Allocated = queue.Status.Allocated.DeepCopy()
	// queue.status.allocated will be updated after every session close in volcano scheduler, we should not depend on it because session may be time-consuming,
	// and queue.status.allocated can't be updated timely. We initialize queue.status.allocated and update it here explicitly
	// to avoid update queue err because update will fail when queue.status.allocated is nil.
	if queueStatus.Allocated == nil {
		queueStatus.Allocated = v1.ResourceList{}
	}

	// ignore update when status does not change
	if equality.Semantic.DeepEqual(queueStatus, queue.Status) {
		return nil
	}

	queueStatusApply := v1beta1apply.QueueStatus().WithState(queueStatus.State).WithAllocated(queueStatus.Allocated)
	queueApply := v1beta1apply.Queue(queue.Name).WithStatus(queueStatusApply)
	if _, err := c.vcClient.SchedulingV1beta1().Queues().ApplyStatus(context.TODO(), queueApply, metav1.ApplyOptions{FieldManager: controllerName}); err != nil {
		klog.Errorf("Failed to apply status of Queue %s: %v.", queue.Name, err)
		return err
	}

	return nil
}

func (c *queuecontroller) openQueue(queue *schedulingv1beta1.Queue, updateStateFn state.UpdateQueueStatusFn) error {
	klog.V(4).Infof("Begin to open queue %s.", queue.Name)

	newQueue := queue.DeepCopy()
	newQueue.Status.State = schedulingv1beta1.QueueStateOpen

	if queue.Status.State != newQueue.Status.State {
		if _, err := c.vcClient.SchedulingV1beta1().Queues().Update(context.TODO(), newQueue, metav1.UpdateOptions{}); err != nil {
			c.recorder.Event(newQueue, v1.EventTypeWarning, string(v1alpha1.OpenQueueAction),
				fmt.Sprintf("Open queue failed for %v", err))
			return err
		}

		c.recorder.Event(newQueue, v1.EventTypeNormal, string(v1alpha1.OpenQueueAction), "Open queue succeed")
	} else {
		return nil
	}

	q, err := c.vcClient.SchedulingV1beta1().Queues().Get(context.TODO(), newQueue.Name, metav1.GetOptions{})
	if err != nil {
		return err
	}

	newQueue = q.DeepCopy()
	if updateStateFn != nil {
		updateStateFn(&newQueue.Status, nil)
	} else {
		return fmt.Errorf("internal error, update state function should be provided")
	}

	if queue.Status.State != newQueue.Status.State {
		if _, err := c.vcClient.SchedulingV1beta1().Queues().UpdateStatus(context.TODO(), newQueue, metav1.UpdateOptions{}); err != nil {
			c.recorder.Event(newQueue, v1.EventTypeWarning, string(v1alpha1.OpenQueueAction),
				fmt.Sprintf("Update queue status from %s to %s failed for %v",
					queue.Status.State, newQueue.Status.State, err))
			return err
		}
	}

	return nil
}

func (c *queuecontroller) closeQueue(queue *schedulingv1beta1.Queue, updateStateFn state.UpdateQueueStatusFn) error {
	klog.V(4).Infof("Begin to close queue %s.", queue.Name)

	newQueue := queue.DeepCopy()
	newQueue.Status.State = schedulingv1beta1.QueueStateClosed

	if queue.Status.State != newQueue.Status.State {
		if _, err := c.vcClient.SchedulingV1beta1().Queues().Update(context.TODO(), newQueue, metav1.UpdateOptions{}); err != nil {
			c.recorder.Event(newQueue, v1.EventTypeWarning, string(v1alpha1.CloseQueueAction),
				fmt.Sprintf("Close queue failed for %v", err))
			return err
		}

		c.recorder.Event(newQueue, v1.EventTypeNormal, string(v1alpha1.CloseQueueAction), "Close queue succeed")
	} else {
		return nil
	}

	q, err := c.vcClient.SchedulingV1beta1().Queues().Get(context.TODO(), newQueue.Name, metav1.GetOptions{})
	if err != nil {
		return err
	}

	newQueue = q.DeepCopy()
	podGroups := c.getPodGroups(newQueue.Name)
	if updateStateFn != nil {
		updateStateFn(&newQueue.Status, podGroups)
	} else {
		return fmt.Errorf("internal error, update state function should be provided")
	}

	if queue.Status.State != newQueue.Status.State {
		if _, err := c.vcClient.SchedulingV1beta1().Queues().UpdateStatus(context.TODO(), newQueue, metav1.UpdateOptions{}); err != nil {
			c.recorder.Event(newQueue, v1.EventTypeWarning, string(v1alpha1.CloseQueueAction),
				fmt.Sprintf("Update queue status from %s to %s failed for %v",
					queue.Status.State, newQueue.Status.State, err))
			return err
		}
	}

	return nil
}
