/*
Copyright 2026 The Volcano Authors.

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

package hypernode

import (
	"context"
	"fmt"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/utils/ptr"

	scheduling "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	e2eutil "volcano.sh/volcano/test/e2e/util"
)

// Equal scores let the scheduler try different placements during repeated rollback.
const diagnosticSchedulerConfig = `actions: "allocate, backfill"
tiers:
- plugins:
  - name: priority
  - name: gang
  - name: conformance
- plugins:
  - name: predicates
  - name: proportion
  - name: network-topology-aware
`

var _ = Describe("HyperNode scheduling diagnostics", Ordered, Serial, Label("scheduling-diagnostics"), func() {
	var ctx *e2eutil.TestContext
	var topology podGroupAntiAffinityTopology

	BeforeAll(func() {
		config := e2eutil.NewConfigMapCase(volcanoSystemNamespace(), volcanoSchedulerConfigMapName())
		Expect(config.ChangeBy(replaceSchedulerConfig(diagnosticSchedulerConfig))).To(Succeed())
		DeferCleanup(func() {
			Expect(config.UndoChanged()).To(Succeed())
			restartVolcanoScheduler()
		})
		restartVolcanoScheduler()
	})
	BeforeEach(func() {
		ctx = e2eutil.InitTestContext(e2eutil.Options{})
		DeferCleanup(func() {
			e2eutil.CleanupTestContext(ctx)
			Expect(waitForNoHyperNodes(ctx)).To(Succeed())
		})
		topology = setupPodGroupAntiAffinityTopology(ctx, "diag-"+ctx.Namespace)
	})

	It("keeps Pod diagnostics stable across retries and replaces the blocker after Pod recreation", func() {
		pg := createTopologyPodGroup(ctx, ctx.Namespace, "gang", nil, nil, &scheduling.NetworkTopologySpec{Mode: scheduling.HardNetworkTopologyMode, HighestTierAllowed: ptr.To(1)}, 3)
		b := createPodGroupPod(ctx, ctx.Namespace, "b", pg.Name, "")
		c := createPodGroupPod(ctx, ctx.Namespace, "c", pg.Name, "")
		a := createPodGroupPod(ctx, ctx.Namespace, "a", pg.Name, "no-such-node")
		waiting := fmt.Sprintf("Waiting for PodGroup %s/%s to satisfy gang requirements.", ctx.Namespace, pg.Name)

		// Event writes are asynchronous. Wait for each expected Event before taking
		// the baseline so first publication is outside the steady-state window.
		var baseline map[string]string
		var groupMessage string
		readDiagnostics := func(g Gomega) map[string]string {
			state := make(map[string]string)
			group, err := ctx.Vcclient.SchedulingV1beta1().PodGroups(ctx.Namespace).Get(context.TODO(), pg.Name, metav1.GetOptions{})
			g.Expect(err).NotTo(HaveOccurred())
			message := ""
			for _, condition := range group.Status.Conditions {
				if condition.Type == scheduling.PodGroupUnschedulableType && condition.Status == v1.ConditionTrue {
					message = condition.Message
				}
			}
			g.Expect(message).To(ContainSubstring("Pod " + ctx.Namespace + "/a "))
			g.Expect(message).To(ContainSubstring(topology.rackA))
			g.Expect(message).To(ContainSubstring(topology.rackB))
			state["group"] = message
			events, err := ctx.Kubeclient.CoreV1().Events(ctx.Namespace).List(context.TODO(), metav1.ListOptions{FieldSelector: "reason=FailedScheduling"})
			g.Expect(err).NotTo(HaveOccurred())
			for _, original := range []*v1.Pod{a, b, c} {
				pod, err := ctx.Kubeclient.CoreV1().Pods(ctx.Namespace).Get(context.TODO(), original.Name, metav1.GetOptions{})
				g.Expect(err).NotTo(HaveOccurred())
				condition := scheduledCondition(pod)
				g.Expect(condition).NotTo(BeNil())
				g.Expect(condition.Status).To(Equal(v1.ConditionFalse))
				g.Expect(condition.Reason).To(Equal(v1.PodReasonUnschedulable))
				g.Expect(pod.Status.NominatedNodeName).To(BeEmpty())
				if pod.Name == "a" {
					g.Expect(condition.Message).To(ContainSubstring("node affinity"))
				} else {
					g.Expect(condition.Message).To(Equal(waiting))
				}
				state[pod.Name] = pod.ResourceVersion
				found := false
				for _, event := range events.Items {
					if event.InvolvedObject.UID == pod.UID {
						state["event/"+event.Name] = event.ResourceVersion
						if event.Message == condition.Message {
							found = true
						}
					}
				}
				g.Expect(found).To(BeTrue(), "waiting for the FailedScheduling Event on %s", pod.Name)
			}
			return state
		}
		Eventually(func(g Gomega) { baseline = readDiagnostics(g) }, e2eutil.TwoMinute, time.Second).Should(Succeed())
		groupMessage = baseline["group"]
		Consistently(func(g Gomega) { g.Expect(readDiagnostics(g)).To(Equal(baseline)) }, 30*time.Second, time.Second).Should(Succeed())

		// Move the affinity failure to another UID, retaining the same Pod names.
		replace := func(pod *v1.Pod, selector string) *v1.Pod {
			e2eutil.DeletePod(ctx, pod)
			Expect(e2eutil.WaitPodGone(ctx, pod.Name, pod.Namespace)).To(Succeed())
			replacement := createPodGroupPod(ctx, ctx.Namespace, pod.Name, pg.Name, selector)
			Expect(replacement.UID).NotTo(Equal(pod.UID))
			return replacement
		}
		c = replace(c, "no-such-node")
		a = replace(a, "")
		Eventually(func(g Gomega) {
			group, err := ctx.Vcclient.SchedulingV1beta1().PodGroups(ctx.Namespace).Get(context.TODO(), pg.Name, metav1.GetOptions{})
			g.Expect(err).NotTo(HaveOccurred())
			message := ""
			for _, cond := range group.Status.Conditions {
				if cond.Type == scheduling.PodGroupUnschedulableType && cond.Status == v1.ConditionTrue {
					message = cond.Message
				}
			}
			g.Expect(message).NotTo(Equal(groupMessage))
			g.Expect(message).To(ContainSubstring("Pod " + ctx.Namespace + "/c "))
			g.Expect(message).NotTo(ContainSubstring("Pod " + ctx.Namespace + "/a "))
			for _, name := range []string{"a", "b", "c"} {
				pod, err := ctx.Kubeclient.CoreV1().Pods(ctx.Namespace).Get(context.TODO(), name, metav1.GetOptions{})
				g.Expect(err).NotTo(HaveOccurred())
				cond := scheduledCondition(pod)
				g.Expect(cond).NotTo(BeNil())
				if name == "c" {
					g.Expect(cond.Message).To(ContainSubstring("node affinity"))
				} else {
					g.Expect(cond.Message).To(Equal(waiting))
				}
			}
		}, e2eutil.TwoMinute, time.Second).Should(Succeed())

		c = replace(c, "kwok-node-7")
		for _, pod := range []*v1.Pod{a, b, c} {
			Expect(e2eutil.WaitPodScheduled(ctx, ctx.Namespace, pod.Name)).To(Succeed())
		}
		Eventually(func(g Gomega) {
			group, err := ctx.Vcclient.SchedulingV1beta1().PodGroups(ctx.Namespace).Get(context.TODO(), pg.Name, metav1.GetOptions{})
			g.Expect(err).NotTo(HaveOccurred())
			ready := false
			for _, cond := range group.Status.Conditions {
				if cond.Type == scheduling.PodGroupScheduled && cond.Status == v1.ConditionTrue {
					ready = true
				}
				if cond.Type == scheduling.PodGroupUnschedulableType {
					g.Expect(cond.Status).To(Equal(v1.ConditionFalse))
				}
			}
			g.Expect(ready).To(BeTrue())
		}, e2eutil.TwoMinute, time.Second).Should(Succeed())
	})
	It("binds a SubJob in the feasible rack after evaluating nested HyperNode placements", func() {
		pg := &scheduling.PodGroup{
			ObjectMeta: metav1.ObjectMeta{Name: "nested", Namespace: ctx.Namespace},
			Spec: scheduling.PodGroupSpec{
				MinMember: 3, Queue: e2eutil.DefaultQueue,
				NetworkTopology: &scheduling.NetworkTopologySpec{Mode: scheduling.HardNetworkTopologyMode, HighestTierAllowed: ptr.To(2)},
				SubGroupPolicy: []scheduling.SubGroupPolicySpec{{
					Name: "workers", LabelSelector: &metav1.LabelSelector{},
					SubGroupSize: ptr.To[int32](3), MinSubGroups: ptr.To[int32](1),
					NetworkTopology: &scheduling.NetworkTopologySpec{Mode: scheduling.HardNetworkTopologyMode, HighestTierAllowed: ptr.To(1)},
				}},
			},
		}
		_, err := ctx.Vcclient.SchedulingV1beta1().PodGroups(ctx.Namespace).Create(context.TODO(), pg, metav1.CreateOptions{})
		Expect(err).NotTo(HaveOccurred())
		// Only rack B contains the node requested by the third member.
		pods := []*v1.Pod{
			createPodGroupPod(ctx, ctx.Namespace, "b", pg.Name, ""),
			createPodGroupPod(ctx, ctx.Namespace, "c", pg.Name, ""),
			createPodGroupPod(ctx, ctx.Namespace, "a", pg.Name, "kwok-node-7"),
		}
		for _, pod := range pods {
			Expect(e2eutil.WaitPodScheduled(ctx, ctx.Namespace, pod.Name)).To(Succeed())
			Expect(rackBNodes).To(ContainElement(podNodeName(ctx, pod)))
		}
		Eventually(func(g Gomega) {
			current, err := ctx.Vcclient.SchedulingV1beta1().PodGroups(ctx.Namespace).Get(context.TODO(), pg.Name, metav1.GetOptions{})
			g.Expect(err).NotTo(HaveOccurred())
			var scheduled bool
			for _, cond := range current.Status.Conditions {
				if cond.Type == scheduling.PodGroupScheduled && cond.Status == v1.ConditionTrue {
					scheduled = true
				}
				if cond.Type == scheduling.PodGroupUnschedulableType {
					g.Expect(cond.Status).NotTo(Equal(v1.ConditionTrue))
				}
			}
			g.Expect(scheduled).To(BeTrue())
		}, e2eutil.TwoMinute, time.Second).Should(Succeed())
	})

})

func scheduledCondition(pod *v1.Pod) *v1.PodCondition {
	for i := range pod.Status.Conditions {
		if pod.Status.Conditions[i].Type == v1.PodScheduled {
			return &pod.Status.Conditions[i]
		}
	}
	return nil
}
