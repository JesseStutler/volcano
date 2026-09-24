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

package util

import (
	"flag"
	"fmt"
	"io"
	"os"
	"testing"

	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/klog/v2"

	"volcano.sh/volcano/cmd/scheduler/app/options"
	"volcano.sh/volcano/pkg/scheduler/api"
	commonutil "volcano.sh/volcano/pkg/util"
)

//go:noinline
func benchmarkPredicateFailure(task *api.TaskInfo, node *api.NodeInfo) error {
	return api.NewFitError(task, node, "predicate failed")
}

func BenchmarkPredicateNodesAllFail(b *testing.B) {
	klogFlags := flag.NewFlagSet("benchmark-klog", flag.ContinueOnError)
	klog.InitFlags(klogFlags)
	verbosity := os.Getenv("BENCH_KLOG_V")
	if verbosity == "" {
		verbosity = "0"
	}
	if err := klogFlags.Set("v", verbosity); err != nil {
		b.Fatalf("set klog verbosity: %v", err)
	}
	klog.LogToStderr(false)
	klog.SetOutput(io.Discard)

	for _, nodeCount := range []int{1000, 10000} {
		nodes := make([]*api.NodeInfo, nodeCount)
		for i := range nodes {
			nodes[i] = &api.NodeInfo{Name: fmt.Sprintf("node-%d", i)}
		}

		for _, enableErrorCache := range []bool{false, true} {
			b.Run(fmt.Sprintf("nodes=%d/cache=%t", nodeCount, enableErrorCache), func(b *testing.B) {
				options.ServerOpts = &options.ServerOption{
					MinPercentageOfNodesToFind: 5,
					MinNodesToFind:             1,
					PercentageOfNodesToFind:    100,
					ShardingMode:               commonutil.NoneShardingMode,
				}
				task := &api.TaskInfo{Job: "job1", TaskRole: "worker", Namespace: "ns", Name: "task"}

				b.ReportAllocs()
				b.ResetTimer()
				for range b.N {
					predicateNodes, _ := NewPredicateHelper().PredicateNodes(
						task, nodes, benchmarkPredicateFailure, enableErrorCache, sets.Set[string](nil),
					)
					if len(predicateNodes) != 0 {
						b.Fatalf("expected no predicate nodes, got %d", len(predicateNodes))
					}
				}
			})
		}
	}
}
