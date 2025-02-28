package podgroup

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	appsv1 "k8s.io/api/apps/v1"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"
	quotav1 "k8s.io/apiserver/pkg/quota/v1"
	utilfeature "k8s.io/apiserver/pkg/util/feature"
	featuregatetesting "k8s.io/component-base/featuregate/testing"
	"k8s.io/utils/ptr"
	lwsv1 "sigs.k8s.io/lws/api/leaderworkerset/v1"

	scheduling "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/features"
)

func TestSyncLeaderWorkerSetPodGroups(t *testing.T) {
	featuregatetesting.SetFeatureGateDuringTest(t, utilfeature.DefaultFeatureGate, features.LeaderWorkerSetSupport, true)

	testCases := []struct {
		name              string
		lws               *lwsv1.LeaderWorkerSet
		existingLws       *lwsv1.LeaderWorkerSet
		existingPGs       []*scheduling.PodGroup
		existingLeaderSts *appsv1.StatefulSet
		expectedError     error
		expectedPGCount   int
		expectedPGNames   []string
		expectedResources v1.ResourceList
	}{
		{
			name: "create a normal LeaderWorkerSet",
			lws: NewLeaderWorkerSet("test-lws", "test", 2, 4,
				WithLeaderSpec(defaultPodSpec("50m", "")),
				WithWorkerSpec(defaultPodSpec("50m", "")),
			),
			expectedPGCount: 2,
			expectedPGNames: []string{"test-lws-0", "test-lws-1"},
			expectedResources: v1.ResourceList{
				v1.ResourceCPU: resource.MustParse("400m"),
			},
		},
		{
			name: "scale down",
			lws: NewLeaderWorkerSet("test-lws", "test", 2, 4,
				WithLeaderSpec(defaultPodSpec("50m", "")),
				WithWorkerSpec(defaultPodSpec("50m", "")),
			),
			existingPGs: defaultLwsPgList(NewLeaderWorkerSet("test-lws", "test", 4, 4,
				WithLeaderSpec(defaultPodSpec("50m", "")),
				WithWorkerSpec(defaultPodSpec("50m", "")),
			), 4),
			expectedPGCount: 2,
			expectedPGNames: []string{"test-lws-0", "test-lws-1"},
			expectedResources: v1.ResourceList{
				v1.ResourceCPU: resource.MustParse("400m"),
			},
		},
		{
			name: "rolling update and specify maxSurge",
			lws: NewLeaderWorkerSet("test-lws", "test", 2, 4,
				WithRolloutStrategy(intstr.FromInt32(2), intstr.FromInt32(0)),
			),
			existingLeaderSts: &appsv1.StatefulSet{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-lws",
					Namespace: "test",
				},
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr.To[int32](4),
				},
			},
			existingPGs: defaultLwsPgList(NewLeaderWorkerSet("test-lws", "test", 2, 4,
				WithRolloutStrategy(intstr.FromInt32(2), intstr.FromInt32(0)),
			), 2),
			expectedPGCount: 4,
			expectedPGNames: []string{"test-lws-0", "test-lws-1", "test-lws-2", "test-lws-3"},
		},
		{
			name: "update lws",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			fakeController := newFakePgController()

			if tc.existingLws != nil {
				err := fakeController.lwsInformerFactory.Leaderworkerset().V1().LeaderWorkerSets().Informer().GetIndexer().Add(tc.existingLws)
				assert.NoError(t, err)
			}

			if tc.existingLeaderSts != nil {
				err := fakeController.informerFactory.Apps().V1().StatefulSets().Informer().GetIndexer().Add(tc.existingLeaderSts)
				assert.NoError(t, err)
			}

			for _, pg := range tc.existingPGs {
				err := fakeController.pgInformer.Informer().GetIndexer().Add(pg)
				assert.NoError(t, err)
			}

			err := fakeController.syncLeaderWorkerSetPodGroups(tc.lws)

			if tc.expectedError != nil {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)

				selector := metav1.LabelSelector{
					MatchLabels: map[string]string{
						lwsv1.SetNameLabelKey: tc.lws.Name,
					},
				}
				pgs, err := fakeController.vcClient.SchedulingV1beta1().PodGroups(tc.lws.Namespace).List(context.TODO(), metav1.ListOptions{
					LabelSelector: selector.String(),
				})
				assert.NoError(t, err)

				// expect nums of podgroups equal to replicas of lws
				assert.Equal(t, tc.expectedPGCount, len(pgs.Items))

				// expect podgroup names match the expected names
				actualPGNames := make([]string, len(pgs.Items))
				for index, pg := range pgs.Items {
					actualPGNames[index] = pg.Name
				}
				assert.ElementsMatch(t, tc.expectedPGNames, actualPGNames)

				// expect total resources of podgroups match the expected resources
				if tc.expectedResources != nil {
					totalResources := v1.ResourceList{}
					for _, pg := range pgs.Items {
						totalResources = quotav1.Add(totalResources, *pg.Spec.MinResources)
					}
					assert.True(t, quotav1.Equals(totalResources, tc.expectedResources),
						"total resources of podgroups does not match expected resources, expected %v, got %v",
						tc.expectedResources, totalResources)
				}
			}
		})
	}
}
