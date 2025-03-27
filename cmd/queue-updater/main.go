package main

import (
	"context"
	"os"

	"k8s.io/client-go/rest"
	"k8s.io/klog/v2"

	vcclient "volcano.sh/apis/pkg/client/clientset/versioned"
	"volcano.sh/volcano/cmd/queue-updater/app"
)

func main() {
	// 使用集群内配置
	config, err := rest.InClusterConfig()
	if err != nil {
		klog.Fatal(err)
	}

	vcClient, err := vcclient.NewForConfig(config)
	if err != nil {
		klog.Fatal(err)
	}

	ctx := context.Background()
	updater := app.NewQueueUpdater(vcClient)

	if err := updater.UpdateQueueStatus(ctx); err != nil {
		klog.Errorf("Failed to update queue status: %v", err)
		os.Exit(1)
	}

	klog.Info("Queue status updated successfully")
}
