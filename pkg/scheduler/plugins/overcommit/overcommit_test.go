/*
Copyright 2024 The Volcano Authors.

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

package overcommit

import (
	"strconv"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	"k8s.io/client-go/tools/record"
	"k8s.io/utils/ptr"

	"volcano.sh/apis/pkg/apis/scheduling"
	schedulingv1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/api"
	"volcano.sh/volcano/pkg/scheduler/cache"
	"volcano.sh/volcano/pkg/scheduler/conf"
	"volcano.sh/volcano/pkg/scheduler/framework"
	"volcano.sh/volcano/pkg/scheduler/plugins/proportion"
	"volcano.sh/volcano/pkg/scheduler/uthelper"
	"volcano.sh/volcano/pkg/scheduler/util"
)

func TestOvercommitPlugin(t *testing.T) {
	n1 := util.BuildNode("n1", api.BuildResourceList("2", "4Gi"), make(map[string]string))
	n2 := util.BuildNode("n2", api.BuildResourceList("4", "16Gi"), make(map[string]string))
	hugeResource := api.BuildResourceList("20000m", "20G")
	normalResource := api.BuildResourceList("2000m", "2G")
	smallResource := api.BuildResourceList("200m", "0.5G")

	// pg that requires normal resources
	pg1 := util.BuildPodGroup("pg1", "test-namespace", "c1", 2, nil, schedulingv1.PodGroupPhase(scheduling.PodGroupInqueue))
	pg1.Spec.MinResources = &normalResource
	// pg that requires small resources
	pg2 := util.BuildPodGroup("pg2", "test-namespace", "c1", 2, nil, schedulingv1.PodGroupPhase(scheduling.PodGroupInqueue))
	pg2.Spec.MinResources = &hugeResource
	// pg that no requires resources
	pg3 := util.BuildPodGroup("pg2", "test-namespace", "c1", 2, nil, schedulingv1.PodGroupPhase(scheduling.PodGroupInqueue))

	queue1 := util.BuildQueue("c1", 1, nil)
	queue2 := util.BuildQueue("c1", 1, smallResource)

	tests := []struct {
		uthelper.TestCommonStruct
		arguments           framework.Arguments
		expectedEnqueueAble bool
	}{
		{
			TestCommonStruct: uthelper.TestCommonStruct{
				Name:      "overCommitFactor is more than 0",
				Plugins:   map[string]framework.PluginBuilder{PluginName: New},
				PodGroups: []*schedulingv1.PodGroup{pg1},
				Queues:    []*schedulingv1.Queue{queue1},
				Nodes:     []*v1.Node{n1, n2},
			},
			arguments: framework.Arguments{
				overCommitFactor: 1.2,
			},
			expectedEnqueueAble: true,
		},
		{
			TestCommonStruct: uthelper.TestCommonStruct{
				Name:      "overCommitFactor is less than 0",
				Plugins:   map[string]framework.PluginBuilder{PluginName: New},
				PodGroups: []*schedulingv1.PodGroup{pg1},
				Queues:    []*schedulingv1.Queue{queue1},
				Nodes:     []*v1.Node{n1, n2},
			},
			arguments: framework.Arguments{
				overCommitFactor: 0.8,
			},
			expectedEnqueueAble: true,
		},
		{
			TestCommonStruct: uthelper.TestCommonStruct{
				Name:      "when the required resources of pg are too large",
				Plugins:   map[string]framework.PluginBuilder{PluginName: New},
				PodGroups: []*schedulingv1.PodGroup{pg2},
				Queues:    []*schedulingv1.Queue{queue1},
				Nodes:     []*v1.Node{n1, n2},
			},
			arguments: framework.Arguments{
				overCommitFactor: 1.2,
			},
			expectedEnqueueAble: false,
		},
		{
			TestCommonStruct: uthelper.TestCommonStruct{
				Name:      "when pg does not fill MinResources",
				Plugins:   map[string]framework.PluginBuilder{PluginName: New},
				PodGroups: []*schedulingv1.PodGroup{pg3},
				Queues:    []*schedulingv1.Queue{queue2},
				Nodes:     []*v1.Node{n1, n2},
			},
			arguments: framework.Arguments{
				overCommitFactor: 1.2,
			},
			expectedEnqueueAble: true,
		},
	}

	for _, test := range tests {
		t.Run(test.Name, func(t *testing.T) {
			trueValue := true
			tiers := []conf.Tier{
				{
					Plugins: []conf.PluginOption{
						{
							Name:               PluginName,
							EnabledJobEnqueued: &trueValue,
							Arguments:          test.arguments,
						},
					},
				},
			}
			ssn := test.RegisterSession(tiers, nil)
			defer test.Close()
			for _, job := range ssn.Jobs {
				ssn.JobEnqueued(job)
				isEnqueue := ssn.JobEnqueueable(job)
				if !equality.Semantic.DeepEqual(test.expectedEnqueueAble, isEnqueue) {
					t.Errorf("case: %s error,  expect %v, but get %v", test.Name, test.expectedEnqueueAble, isEnqueue)
				}
			}
		})
	}

}

func TestJobEnqueueable(t *testing.T) {
	const failureEvent = "Normal Unschedulable resource in cluster is overused: overused cpu"
	type attempt struct {
		cpu            string
		skip           bool
		expectedPermit bool
	}
	tests := []struct {
		name            string
		queueCapability v1.ResourceList
		attempts        []attempt
		expected        []string
	}{
		{
			name:     "unchanged failure across sessions",
			attempts: []attempt{{cpu: "2"}, {cpu: "2"}},
			expected: []string{failureEvent},
		},
		{
			name:     "failure can recur after the plugin permits admission",
			attempts: []attempt{{cpu: "2"}, {cpu: "1", expectedPermit: true}, {cpu: "2"}},
			expected: []string{failureEvent, failureEvent},
		},
		{
			name:     "skipped evaluation is not recovery",
			attempts: []attempt{{cpu: "2"}, {cpu: "2", skip: true}, {cpu: "2"}},
			expected: []string{failureEvent},
		},
		{
			name:     "admission without min resources clears the failure",
			attempts: []attempt{{cpu: "2"}, {expectedPermit: true}, {cpu: "2"}},
			expected: []string{failureEvent, failureEvent},
		},
		{
			name:            "one plugin recovers while another keeps rejecting",
			queueCapability: api.BuildResourceList("1", "512Ki"),
			attempts:        []attempt{{cpu: "2"}, {cpu: "1"}, {cpu: "2"}, {cpu: "1"}},
			expected: []string{
				failureEvent,
				"Normal Unschedulable queue resource quota insufficient: insufficient memory",
				failureEvent,
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			framework.RegisterPluginBuilder(PluginName, New)
			t.Cleanup(framework.CleanupPluginBuilders)
			recorder := record.NewFakeRecorder(len(tt.attempts) * 2)
			sc := cache.NewCustomMockSchedulerCache("volcano", nil, nil, &util.FakeStatusUpdater{}, nil, recorder)
			t.Cleanup(func() { cache.ShutdownMockSchedulerCache(sc) })
			sc.AddOrUpdateNode(util.BuildNode("node", api.BuildResourceList("1", "1Gi"), nil))
			sc.AddQueueV1beta1(util.BuildQueue("default", 1, tt.queueCapability))
			pg := util.BuildPodGroup("job", "test", "default", 1, nil, schedulingv1.PodGroupPending)
			pg.UID = "job-uid"
			sc.AddPodGroupV1beta1(pg)
			tiers := []conf.Tier{{Plugins: []conf.PluginOption{{Name: PluginName, EnabledJobEnqueued: ptr.To(true), Arguments: framework.Arguments{overCommitFactor: 1.0}}}}}
			if tt.queueCapability != nil {
				framework.RegisterPluginBuilder(proportion.PluginName, proportion.New)
				tiers[0].Plugins = append(tiers[0].Plugins, conf.PluginOption{Name: proportion.PluginName, EnabledJobEnqueued: ptr.To(true)})
			}
			for index, attempt := range tt.attempts {
				next := pg.DeepCopy()
				next.ResourceVersion = strconv.Itoa(index + 1)
				next.Spec.MinResources = nil
				if attempt.cpu != "" {
					resources := api.BuildResourceList(attempt.cpu, "1Mi")
					next.Spec.MinResources = &resources
				}
				sc.UpdatePodGroupV1beta1(pg, next)
				pg = next
				ssn := framework.OpenSession(sc, tiers, nil)
				job := ssn.Jobs[api.JobID("test/job")]
				require.NotNil(t, job)
				if !attempt.skip {
					// The enqueue action skips plugin checks for best-effort jobs.
					permit := job.PodGroup.Spec.MinResources == nil || ssn.JobEnqueueable(job)
					assert.Equal(t, attempt.expectedPermit, permit)
					if job.PodGroup.Spec.MinResources == nil {
						ssn.JobEnqueued(job)
					}
				}
				framework.CloseSession(ssn)
			}
			var actual []string
			for len(recorder.Events) > 0 {
				event := <-recorder.Events
				if strings.HasPrefix(event, "Normal Unschedulable ") {
					actual = append(actual, event)
				}
			}
			assert.Equal(t, tt.expected, actual)
		})
	}
}
