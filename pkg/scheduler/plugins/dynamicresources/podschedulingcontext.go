/*
Copyright 2022 The Kubernetes Authors.

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

package dynamicresources

import (
	"context"
	"fmt"
	v1 "k8s.io/api/core/v1"
	"k8s.io/client-go/kubernetes"

	resourceapi "k8s.io/api/resource/v1alpha3"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	resourcelisters "k8s.io/client-go/listers/resource/v1alpha3"
	"k8s.io/klog/v2"
)

// TODO: In 'classic' DRA, PodSchedulingContext is used by the scheduler and Resource Controller to negotiate scheduling, it will be removed in k8s v1.32.
type podSchedulingState struct {
	// A pointer to the PodSchedulingContext object for the pod, if one exists
	// in the API server.
	//
	// Conceptually, this object belongs into the scheduler k8sframework
	// where it might get shared by different plugins. But in practice,
	// it is currently only used by dynamic provisioning and thus
	// managed entirely here.
	schedulingCtx *resourceapi.PodSchedulingContext

	// selectedNode is set if (and only if) a node has been selected.
	selectedNode *string

	// potentialNodes is set if (and only if) the potential nodes field
	// needs to be updated or set.
	potentialNodes *[]string
}

func (p *podSchedulingState) isDirty() bool {
	return p.selectedNode != nil ||
		p.potentialNodes != nil
}

// init checks whether there is already a PodSchedulingContext object.
// Must not be called concurrently,
func (p *podSchedulingState) init(ctx context.Context, pod *v1.Pod, podSchedulingContextLister resourcelisters.PodSchedulingContextLister) error {
	if podSchedulingContextLister == nil {
		return nil
	}
	schedulingCtx, err := podSchedulingContextLister.PodSchedulingContexts(pod.Namespace).Get(pod.Name)
	switch {
	case apierrors.IsNotFound(err):
		return nil
	case err != nil:
		return err
	default:
		// We have an object, but it might be obsolete.
		if !metav1.IsControlledBy(schedulingCtx, pod) {
			return fmt.Errorf("PodSchedulingContext object with UID %s is not owned by Pod %s/%s", schedulingCtx.UID, pod.Namespace, pod.Name)
		}
	}
	p.schedulingCtx = schedulingCtx
	return nil
}

// publish creates or updates the PodSchedulingContext object, if necessary.
// Must not be called concurrently.
func (p *podSchedulingState) publish(ctx context.Context, pod *v1.Pod, clientset kubernetes.Interface) error {
	if !p.isDirty() {
		return nil
	}

	var err error
	logger := klog.FromContext(ctx)
	if p.schedulingCtx != nil {
		// Update it.
		schedulingCtx := p.schedulingCtx.DeepCopy()
		if p.selectedNode != nil {
			schedulingCtx.Spec.SelectedNode = *p.selectedNode
		}
		if p.potentialNodes != nil {
			schedulingCtx.Spec.PotentialNodes = *p.potentialNodes
		}
		if loggerV := logger.V(6); loggerV.Enabled() {
			// At a high enough log level, dump the entire object.
			loggerV.Info("Updating PodSchedulingContext", "podSchedulingCtx", klog.KObj(schedulingCtx), "podSchedulingCtxObject", klog.Format(schedulingCtx))
		} else {
			logger.V(5).Info("Updating PodSchedulingContext", "podSchedulingCtx", klog.KObj(schedulingCtx))
		}
		_, err = clientset.ResourceV1alpha3().PodSchedulingContexts(schedulingCtx.Namespace).Update(ctx, schedulingCtx, metav1.UpdateOptions{})
		if apierrors.IsConflict(err) {
			// We don't use SSA by default for performance reasons
			// (https://github.com/kubernetes/kubernetes/issues/113700#issuecomment-1698563918)
			// because most of the time an Update doesn't encounter
			// a conflict and is faster.
			//
			// We could return an error here and rely on
			// backoff+retry, but scheduling attempts are expensive
			// and the backoff delay would cause a (small)
			// slowdown. Therefore we fall back to SSA here if needed.
			//
			// Using SSA instead of Get+Update has the advantage that
			// there is no delay for the Get. SSA is safe because only
			// the scheduler updates these fields.
			spec := resourceapiapply.PodSchedulingContextSpec()
			spec.SelectedNode = p.selectedNode
			if p.potentialNodes != nil {
				spec.PotentialNodes = *p.potentialNodes
			} else {
				// Unchanged. Has to be set because the object that we send
				// must represent the "fully specified intent". Not sending
				// the list would clear it.
				spec.PotentialNodes = p.schedulingCtx.Spec.PotentialNodes
			}
			schedulingCtxApply := resourceapiapply.PodSchedulingContext(pod.Name, pod.Namespace).WithSpec(spec)

			if loggerV := logger.V(6); loggerV.Enabled() {
				// At a high enough log level, dump the entire object.
				loggerV.Info("Patching PodSchedulingContext", "podSchedulingCtx", klog.KObj(pod), "podSchedulingCtxApply", klog.Format(schedulingCtxApply))
			} else {
				logger.V(5).Info("Patching PodSchedulingContext", "podSchedulingCtx", klog.KObj(pod))
			}
			_, err = clientset.ResourceV1alpha3().PodSchedulingContexts(pod.Namespace).Apply(ctx, schedulingCtxApply, metav1.ApplyOptions{FieldManager: "kube-scheduler", Force: true})
		}

	} else {
		// Create it.
		schedulingCtx := &resourceapi.PodSchedulingContext{
			ObjectMeta: metav1.ObjectMeta{
				Name:            pod.Name,
				Namespace:       pod.Namespace,
				OwnerReferences: []metav1.OwnerReference{*metav1.NewControllerRef(pod, schema.GroupVersionKind{Version: "v1", Kind: "Pod"})},
			},
		}
		if p.selectedNode != nil {
			schedulingCtx.Spec.SelectedNode = *p.selectedNode
		}
		if p.potentialNodes != nil {
			schedulingCtx.Spec.PotentialNodes = *p.potentialNodes
		}
		if loggerV := logger.V(6); loggerV.Enabled() {
			// At a high enough log level, dump the entire object.
			loggerV.Info("Creating PodSchedulingContext", "podSchedulingCtx", klog.KObj(schedulingCtx), "podSchedulingCtxObject", klog.Format(schedulingCtx))
		} else {
			logger.V(5).Info("Creating PodSchedulingContext", "podSchedulingCtx", klog.KObj(schedulingCtx))
		}
		_, err = clientset.ResourceV1alpha3().PodSchedulingContexts(schedulingCtx.Namespace).Create(ctx, schedulingCtx, metav1.CreateOptions{})
	}
	if err != nil {
		return err
	}
	p.potentialNodes = nil
	p.selectedNode = nil
	return nil
}

func statusForClaim(schedulingCtx *resourceapi.PodSchedulingContext, podClaimName string) *resourceapi.ResourceClaimSchedulingStatus {
	if schedulingCtx == nil {
		return nil
	}
	for _, status := range schedulingCtx.Status.ResourceClaims {
		if status.Name == podClaimName {
			return &status
		}
	}
	return nil
}
