package podgroup

import (
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes/fake"
	"k8s.io/utils/ptr"
	lwsv1 "sigs.k8s.io/lws/api/leaderworkerset/v1"
	lwsclientset "sigs.k8s.io/lws/client-go/clientset/versioned/fake"
	lwsinformer "sigs.k8s.io/lws/client-go/informers/externalversions"
	scheduling "volcano.sh/apis/pkg/apis/scheduling/v1beta1"

	vcclientset "volcano.sh/apis/pkg/client/clientset/versioned/fake"
	"volcano.sh/apis/pkg/client/clientset/versioned/scheme"
	vcinformers "volcano.sh/apis/pkg/client/informers/externalversions"
	"volcano.sh/volcano/pkg/controllers/framework"
)

func init() {
	schemeBuilder := runtime.SchemeBuilder{
		scheduling.AddToScheme,
	}

	utilruntime.Must(schemeBuilder.AddToScheme(scheme.Scheme))
}

func newFakePgController() *pgcontroller {
	kubeClient := fake.NewClientset()
	vcClient := vcclientset.NewClientset()
	lwsClient := lwsclientset.NewClientset()

	kubeInformerFactory := informers.NewSharedInformerFactory(kubeClient, 0)
	vcInformerFactory := vcinformers.NewSharedInformerFactory(vcClient, 0)
	lwsInformerFactory := lwsinformer.NewSharedInformerFactory(lwsClient, 0)

	controller := &pgcontroller{}
	opt := &framework.ControllerOption{
		KubeClient:               kubeClient,
		VolcanoClient:            vcClient,
		SharedInformerFactory:    kubeInformerFactory,
		VCSharedInformerFactory:  vcInformerFactory,
		LWSSharedInformerFactory: lwsInformerFactory,
		WorkerThreadsForPG:       5,
	}

	controller.Initialize(opt)

	return controller
}

func defaultLeaderWorkerSet(name, namespace string, replicas, size int32) *lwsv1.LeaderWorkerSet {
	return &lwsv1.LeaderWorkerSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: lwsv1.LeaderWorkerSetSpec{
			Replicas: ptr.To(replicas),
			LeaderWorkerTemplate: lwsv1.LeaderWorkerTemplate{
				Size: ptr.To(size),
				LeaderTemplate: &v1.PodTemplateSpec{
					ObjectMeta: metav1.ObjectMeta{
						Name:      "leader",
						Namespace: namespace,
					},
				},
				WorkerTemplate: v1.PodTemplateSpec{
					ObjectMeta: metav1.ObjectMeta{
						Name:      "worker",
						Namespace: namespace,
					},
				},
			},
		},
	}
}

func defaultPodSpec(cpu, mem string) v1.PodSpec {
	res := v1.ResourceList{}
	if cpu != "" {
		res[v1.ResourceCPU] = resource.MustParse(cpu)
	}
	if mem != "" {
		res[v1.ResourceMemory] = resource.MustParse(mem)
	}

	spec := v1.PodSpec{
		Containers: []v1.Container{
			{
				Name:  "nginx",
				Image: "nginx:1.14.2",
				Resources: v1.ResourceRequirements{
					Limits:   res,
					Requests: res,
				},
			},
		},
	}

	return spec
}

func defaultLwsPg(lws *lwsv1.LeaderWorkerSet, index int) *scheduling.PodGroup {
	lwsProvider := NewLeaderWorkerSetProvider(lws, index)

	pg := &scheduling.PodGroup{
		ObjectMeta: lwsProvider.GetObjectMeta(),
		Spec:       lwsProvider.GetSpec(),
	}

	return pg
}

func defaultLwsPgList(lws *lwsv1.LeaderWorkerSet, count int) []*scheduling.PodGroup {
	pgs := make([]*scheduling.PodGroup, count)
	for i := 0; i < count; i++ {
		pgs[i] = defaultLwsPg(lws, i)
	}
	return pgs
}

func NewLeaderWorkerSet(name, namespace string, replicas, size int32, opts ...LeaderWorkerSetOption) *lwsv1.LeaderWorkerSet {
	lws := defaultLeaderWorkerSet(name, namespace, replicas, size)
	for _, opt := range opts {
		opt(lws)
	}
	return lws
}

type LeaderWorkerSetOption func(*lwsv1.LeaderWorkerSet)

func WithRolloutStrategy(maxSurge, maxUnavailable intstr.IntOrString) LeaderWorkerSetOption {
	return func(lws *lwsv1.LeaderWorkerSet) {
		lws.Spec.RolloutStrategy = lwsv1.RolloutStrategy{
			Type: lwsv1.RollingUpdateStrategyType,
			RollingUpdateConfiguration: &lwsv1.RollingUpdateConfiguration{
				MaxSurge:       maxSurge,
				MaxUnavailable: maxUnavailable,
			},
		}
	}
}

func WithLabels(labels map[string]string) LeaderWorkerSetOption {
	return func(lws *lwsv1.LeaderWorkerSet) {
		if lws.Labels == nil {
			lws.Labels = make(map[string]string)
		}
		for k, v := range labels {
			lws.Labels[k] = v
		}
	}
}

func WithAnnotations(annotations map[string]string) LeaderWorkerSetOption {
	return func(lws *lwsv1.LeaderWorkerSet) {
		if lws.Annotations == nil {
			lws.Annotations = make(map[string]string)
		}
		for k, v := range annotations {
			lws.Annotations[k] = v
		}
	}
}

func WithLeaderSpec(spec v1.PodSpec) LeaderWorkerSetOption {
	return func(lws *lwsv1.LeaderWorkerSet) {
		lws.Spec.LeaderWorkerTemplate.LeaderTemplate.Spec = spec
	}
}

func WithWorkerSpec(spec v1.PodSpec) LeaderWorkerSetOption {
	return func(lws *lwsv1.LeaderWorkerSet) {
		lws.Spec.LeaderWorkerTemplate.WorkerTemplate.Spec = spec
	}
}
