package dynamicresources

import (
	"context"
	"fmt"
	"strings"

	utilFeature "k8s.io/apiserver/pkg/util/feature"
	"k8s.io/kubernetes/pkg/features"
	k8sframework "k8s.io/kubernetes/pkg/scheduler/framework"
	"k8s.io/kubernetes/pkg/scheduler/framework/plugins/feature"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/plugins/util/k8s"
)

const (
	PluginName = "DynamicResources"
)

// When the dynamicResources struct in the k8s scheduler package becomes public, we can directly embed it to replace the dynamicResources we copied.
// Like this:
//
//	type dynamicResourcesPlugin struct {
//		*dynamicresources.DynamicResources
//	}
//
// Since "classic" DRA, which also called control plane controller DRA will be withdrawn in v1.32, we only implement the new structed parameters DRA
// related extension points, including PreEnqueue, PreFilter, Filter, Reserve, PreBind, Unreserve, PostFilter.
// TODO: PostFilter and Reserve have not been implemented yet
type dynamicResourcesPlugin struct {
	*dynamicResources
}

func New(arguments framework.Arguments) framework.Plugin {
	return &dynamicResourcesPlugin{}
}

func (d *dynamicResourcesPlugin) Name() string {
	return PluginName
}

func (d *dynamicResourcesPlugin) RegisterPrePredicateFn(ssn *framework.Session) {
	ssn.AddPrePredicateFn(d.Name(), func(task *api.TaskInfo) error {
		// 1. Check each ResourceClaim for the pod exists
		// PreEnqueue is used to verify whether a Pod can be added to scheduler queue, but Volcano uses PodGroup as the granularity
		// to determine whether it can be added to a Queue, so it is more appropriate to place PreEnqueue in PrePredicate here.
		status := d.PreEnqueue(context.TODO(), task.Pod)
		if !status.IsSuccess() {
			return fmt.Errorf("failed to check each ResourceClaim for the pod exists with err: %s", strings.Join(status.Reasons(), "."))
		}

		// 2. Run Prefilter
		// Init cycle state for pod to share it with other extension points
		state := k8sframework.NewCycleState()
		_, status = d.PreFilter(context.TODO(), state, task.Pod)
		// TODO: complete the error return status here
		switch status.Code() {
		case k8sframework.Error:
		case k8sframework.UnschedulableAndUnresolvable:
		default:
			ssn.CycleStatesMap[task.UID] = state
		}

		return nil
	})
}

func (d *dynamicResourcesPlugin) RegisterPredicateFn(ssn *framework.Session) {
	ssn.AddPredicateFn(d.Name(), func(task *api.TaskInfo, node *api.NodeInfo) error {
		state, exist := ssn.CycleStatesMap[task.UID]
		if !exist {
			return api.NewFitError(task, node, "scheduling state is not exist")
		}
		nodeInfo, exist := ssn.NodeMap[node.Name]
		if !exist {
			return api.NewFitError(task, node, "node info not found")
		}
		status := d.Filter(context.TODO(), state, task.Pod, nodeInfo)
		switch status.Code() {
		case k8sframework.Error:
		case k8sframework.UnschedulableAndUnresolvable:
		default:
		}

		return nil
	})
}

func (d *dynamicResourcesPlugin) RegisterPreBindFn(ssn *framework.Session) {
	ssn.AddPreBindFns(d.Name(), func(task *api.TaskInfo, node *api.NodeInfo) error {
		state, exist := ssn.CycleStatesMap[task.UID]
		if !exist {
			return api.NewFitError(task, node, "scheduling state is not exist")
		}
		status := d.PreBind(context.TODO(), state, task.Pod, node.Name)
		switch status.Code() {
		case k8sframework.Error:
		case k8sframework.UnschedulableAndUnresolvable:
		default:
		}

		return nil
	})
}

func (d *dynamicResourcesPlugin) RegisterEventHandler(ssn *framework.Session) {
	ssn.AddEventHandler(&framework.EventHandler{
		AllocateFunc: func(event *framework.Event) {
			state, exist := ssn.CycleStatesMap[event.Task.UID]
			if !exist {
				event.Err = fmt.Errorf("scheduling context of task <%s/%s> is not exist", event.Task.Namespace, event.Task.Name)
			}
			status := d.Reserve(context.TODO(), state, event.Task.Pod, event.Task.Name)
			switch status.Code() {
			case k8sframework.Error:
			case k8sframework.UnschedulableAndUnresolvable:
			default:
			}
		},
		DeallocateFunc: func(event *framework.Event) {
			state, exist := ssn.CycleStatesMap[event.Task.UID]
			if !exist {
				event.Err = fmt.Errorf("scheduling context of task <%s/%s> is not exist", event.Task.Namespace, event.Task.Name)
			}
			d.Unreserve(context.TODO(), state, event.Task.Pod, event.Task.Name)
		},
	})
}

func (d *dynamicResourcesPlugin) OnSessionOpen(ssn *framework.Session) {
	featureGates := feature.Features{
		EnableDynamicResourceAllocation: utilFeature.DefaultFeatureGate.Enabled(features.DynamicResourceAllocation),
	}
	handle := k8s.NewFrameworkHandle(ssn.NodeMap, ssn.KubeClient(), ssn.InformerFactory())
	plugin, _ := NewDRAPlugin(context.TODO(), nil, handle, featureGates)
	draPlugin := plugin.(*dynamicResources)
	d.dynamicResources = draPlugin

	ssn.BindContextEnabledPlugins = append(ssn.BindContextEnabledPlugins, PluginName)
	d.RegisterPrePredicateFn(ssn)
	d.RegisterPredicateFn(ssn)
	d.RegisterPreBindFn(ssn)
	d.RegisterEventHandler(ssn)
}

func (d *dynamicResourcesPlugin) OnSessionClose(ssn *framework.Session) {}
