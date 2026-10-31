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

package cache

import (
	"time"

	"k8s.io/apimachinery/pkg/types"
	"k8s.io/klog/v2"

	schedulingscheme "volcano.sh/apis/pkg/apis/scheduling/scheme"
	vcv1beta1 "volcano.sh/apis/pkg/apis/scheduling/v1beta1"
	"volcano.sh/volcano/pkg/scheduler/api"
)

// Refresh ongoing failures at the same interval as client-go's EventSeries
// heartbeat. Events are best effort and may expire or fail to reach the API.
const podGroupEventRefreshInterval = 30 * time.Minute

type podGroupDiagnostic struct {
	eventType string
	reason    string
	message   string
}

type recordedPodGroupEvent struct {
	diagnostic podGroupDiagnostic
	recordedAt time.Time
}

type podGroupEventCache map[types.UID]map[string]recordedPodGroupEvent

// RecordPodGroupEvent records scheduling diagnostics independently for each
// source. An empty source bypasses deduplication for one-off lifecycle events.
func (sc *SchedulerCache) RecordPodGroupEvent(podGroup *api.PodGroup, source, eventType, reason, message string) {
	if podGroup == nil {
		return
	}
	pg := &vcv1beta1.PodGroup{}
	if err := schedulingscheme.Scheme.Convert(&podGroup.PodGroup, pg, nil); err != nil {
		klog.Errorf("Error while converting PodGroup to v1beta1.PodGroup: %v", err)
		return
	}
	if source != "" && pg.UID != "" && !sc.shouldRecordPodGroupEvent(pg, source, podGroupDiagnostic{eventType, reason, message}) {
		return
	}
	// The recorder owns asynchronous delivery and retries. No cache lock is held
	// here, and the remembered diagnostic means submitted, not API-confirmed.
	sc.Recorder.Eventf(pg, eventType, reason, "%s", message)
}

func (sc *SchedulerCache) shouldRecordPodGroupEvent(pg *vcv1beta1.PodGroup, source string, diagnostic podGroupDiagnostic) bool {
	// JobUpdater workers and PodGroup informer handlers access this state
	// concurrently. Reuse the cache lock, including for deletion cleanup.
	sc.Lock()
	defer sc.Unlock()

	job := sc.Jobs[api.JobID(pg.Namespace+"/"+pg.Name)]
	if job == nil || job.PodGroup == nil || job.PodGroup.UID != pg.UID {
		// A session snapshot can outlive a deleted or replaced PodGroup. Do not
		// recreate its deduplication state after the informer has removed it.
		return true
	}
	now := time.Now()
	if sc.eventClock != nil {
		now = sc.eventClock.Now()
	}
	previous, exists := sc.podGroupEvents[pg.UID][source]
	if exists && previous.diagnostic == diagnostic && now.Sub(previous.recordedAt) < podGroupEventRefreshInterval {
		return false
	}
	if sc.podGroupEvents == nil {
		sc.podGroupEvents = make(podGroupEventCache)
	}
	if sc.podGroupEvents[pg.UID] == nil {
		sc.podGroupEvents[pg.UID] = make(map[string]recordedPodGroupEvent)
	}
	sc.podGroupEvents[pg.UID][source] = recordedPodGroupEvent{diagnostic: diagnostic, recordedAt: now}
	return true
}

// ClearPodGroupEvents allows a recovered diagnostic to be reported again.
// An empty source clears all diagnostics for the PodGroup.
func (sc *SchedulerCache) ClearPodGroupEvents(podGroup *api.PodGroup, source string) {
	if podGroup == nil {
		return
	}
	sc.Lock()
	defer sc.Unlock()
	if source == "" {
		delete(sc.podGroupEvents, podGroup.UID)
		return
	}
	delete(sc.podGroupEvents[podGroup.UID], source)
	if len(sc.podGroupEvents[podGroup.UID]) == 0 {
		delete(sc.podGroupEvents, podGroup.UID)
	}
}
