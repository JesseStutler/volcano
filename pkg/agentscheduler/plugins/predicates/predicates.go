package predicates

import (
	k8sframework "k8s.io/kubernetes/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/agentscheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/api"
	vfwk "volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/plugins/predicates"
)

const (
	// PluginName indicates name of volcano scheduler plugin.
	PluginName = "predicates"
)

type predicatesPlugin struct {
	*predicates.PredicatesPlugin
}

func New(arguments vfwk.Arguments) framework.Plugin {
	plugin := predicates.New(arguments).(*predicates.PredicatesPlugin)

	return &predicatesPlugin{
		PredicatesPlugin: plugin,
	}
}

func (pp *predicatesPlugin) Name() string {
	return PluginName
}

func (pp *predicatesPlugin) OnSchedulingStart(fwk *framework.Framework) {
	pp.PredicatesPlugin.InitPlugin()

	contextProvider := func(t *api.TaskInfo) (*k8sframework.CycleState, []k8sframework.NodeInfo) {
		return state, nil // Node list is not needed for PredicateFn
	}
	fwk.AddPrePredicateFn(PluginName, pp.PredicatesPlugin.GetPrePredicateFn())
	fwk.AddPredicateFn(PluginName, pp.PredicatesPlugin.GetPredicateFn())
}

func (pp *predicatesPlugin) PrePredicate(task *api.TaskInfo, state *k8sframework.CycleState, nodeInfoList []k8sframework.NodeInfo) error {
	contextProvider := func(t *api.TaskInfo) (*k8sframework.CycleState, []k8sframework.NodeInfo) {
		return state, nodeInfoList
	}

	prePredicateFn := pp.PredicatesPlugin.GetPrePredicateFn(contextProvider)
	return prePredicateFn(task)
}

func (pp *predicatesPlugin) Predicate(task *api.TaskInfo, node *api.NodeInfo, state *k8sframework.CycleState) error {
	contextProvider := func(t *api.TaskInfo) (*k8sframework.CycleState, []k8sframework.NodeInfo) {
		return state, nil // Node list is not needed for PredicateFn
	}

	// Get the actual predicate function and execute it.
	predicateFn := pp.PredicatesPlugin.GetPredicateFn(contextProvider)
	return predicateFn(task, node)
}

// OnSchedulingEnd is called when a schedule cycle end
func (pp *predicatesPlugin) OnSchedulingEnd(fwk *framework.Framework) {
}
