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

package proportion

import (
	"context"

	fwk "k8s.io/kube-scheduler/framework"

	"volcano.sh/volcano/pkg/scheduler/api"
)

// EventsToRegister implements api.HintProvider. Unlike capacity, proportion is a
// global fair-share plugin: a queue's deserved is derived from the total cluster
// resources and every queue's weight and demand, so freeing resources in any
// queue, or adding or updating any queue, can shift another queue's share and
// unblock a rejected Job. The wakeup set therefore cannot be scoped to the Job's
// own queue, and a nil HintFn (wake on any of these events) is intentional.
func (pp *proportionPlugin) EventsToRegister(_ context.Context) ([]api.ClusterEventWithHint, error) {
	return []api.ClusterEventWithHint{
		{Event: api.ClusterEvent{Resource: api.QueueEvent, ActionType: fwk.Add | fwk.Update}},
		{Event: api.ClusterEvent{Resource: api.PodGroupEvent, ActionType: fwk.Update | fwk.Delete}},
		{Event: api.ClusterEvent{Resource: fwk.Pod, ActionType: fwk.Delete}},
	}, nil
}
