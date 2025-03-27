package app

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog/v2"

	vcclient "volcano.sh/apis/pkg/client/clientset/versioned"
)

type QueueUpdater struct {
	vcClient vcclient.Interface
}

func NewQueueUpdater(vcClient vcclient.Interface) *QueueUpdater {
	return &QueueUpdater{
		vcClient: vcClient,
	}
}

func (qu *QueueUpdater) UpdateQueueStatus(ctx context.Context) error {
	queues, err := qu.vcClient.SchedulingV1beta1().Queues().List(ctx, metav1.ListOptions{})
	if err != nil {
		return err
	}

	for _, queue := range queues.Items {
		newQueue := queue.DeepCopy()
		if newQueue.Status.Allocated == nil {
			newQueue.Status.Allocated = make(v1.ResourceList)
		}

		// 获取当前的 Pods 数量
		currentPods := newQueue.Status.Allocated.Pods().Value()
		// 设置新的 Pods 数量（当前值 + 1）
		newQueue.Status.Allocated[v1.ResourcePods] = *resource.NewQuantity(currentPods+1, resource.DecimalSI)

		_, err = qu.vcClient.SchedulingV1beta1().Queues().UpdateStatus(
			ctx,
			newQueue,
			metav1.UpdateOptions{},
		)
		if err != nil {
			klog.Errorf("Failed to update queue %s status: %v", queue.Name, err)
			continue
		}
		klog.V(4).Infof("Successfully updated queue %s allocated pods", queue.Name)
	}

	return nil
}
