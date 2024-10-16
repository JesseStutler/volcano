package dynamicresources

import (
	"context"
	"fmt"
	"strings"

	k8sframework "k8s.io/kubernetes/pkg/scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/framework"
)

const (
	PluginName = "DynamicResources"
)

// When the dynamicResources struct in the k8s scheduler package becomes public, we can directly embed it to replace the dynamicResources we copied.
// Like this:
//
//	type dynamicResourcesPlugin struct {
//		dynamicresources.DynamicResources
//	}
type dynamicResourcesPlugin struct {
	dynamicResources

	// whether to enable using BindContext to pass CycleState, PreBindFn, ReservedNodesFn and UnReservedNodesFn
	enableBindContext bool
}

func New() framework.Plugin {

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

func (d *dynamicResourcesPlugin) RegisterPreBindFn(task *api.TaskInfo, node *api.NodeInfo) error {

}

func (d *dynamicResourcesPlugin) RegisterReserveNodesFn(task *api.TaskInfo, node *api.NodeInfo) error {

}

func (d *dynamicResourcesPlugin) RegisterUnReserveNodesFn(task *api.TaskInfo, node *api.NodeInfo) error {

}

func (d *dynamicResourcesPlugin) OnSessionOpen(ssn *framework.Session) {
	// TODO: Init here

	d.RegisterPrePredicateFn(ssn)
	d.RegisterPredicateFn(ssn)
}

func (d *dynamicResourcesPlugin) OnSessionClose(ssn *framework.Session) {

}
