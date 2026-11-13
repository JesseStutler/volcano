#!/usr/bin/env bash

# Copyright 2026 The Volcano Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

components=(scheduler agent-scheduler controller-manager hypernode-controller-manager webhook-manager agent)
mkdir -p "$IMAGES_DIR" "$RESULTS_DIR"
[[ "$(git rev-parse HEAD)" == "$SOURCE_SHA" ]]

if [[ "$1" == build ]]; then
    {
        git rev-parse HEAD
        docker version
        docker buildx version
        skopeo --version
        jq --version
    } > "$RESULTS_DIR/versions.txt"
    docker buildx create --name release-publishing-test --driver docker-container --use
    if [[ "$BUILD_MODE" == full ]]; then
        /usr/bin/time -o "$RESULTS_DIR/build-time.txt" -f 'elapsed_seconds=%e' \
            make release BUILDX_OUTPUT_TYPE=oci RELEASE_VER="$TAG" IMAGE_PREFIX="$GHCR_PREFIX" \
            2>&1 | tee "$RESULTS_DIR/build.log"
    else
        fixture_dir=$(mktemp -d)
        printf 'FROM scratch\nCOPY marker /marker\n' > "$fixture_dir/Dockerfile"
        printf 'release publishing fixture\n' > "$fixture_dir/marker"
        /usr/bin/time -o "$RESULTS_DIR/build-time.txt" -f 'elapsed_seconds=%e' \
            docker buildx build --platform "$DOCKER_PLATFORMS" --provenance=mode=min \
            --output "type=oci,dest=$IMAGES_DIR/vc-scheduler-$TAG.tar" "$fixture_dir" \
            2>&1 | tee "$RESULTS_DIR/build.log"
        for component in "${components[@]:1}"; do
            cp "$IMAGES_DIR/vc-scheduler-$TAG.tar" "$IMAGES_DIR/vc-$component-$TAG.tar"
        done
    fi
    sha256sum "$IMAGES_DIR"/*.tar > "$RESULTS_DIR/archives.sha256"
    du -h "$IMAGES_DIR" > "$RESULTS_DIR/archive-sizes.txt"
    exit 0
fi

[[ "$1" == publish ]]
destinations=("localhost:5000/pr6296-test" "$GHCR_PREFIX")
names=(local ghcr)
if [[ -n "$DOCKERHUB_NAMESPACE" ]]; then
    destinations+=("$DOCKERHUB_NAMESPACE")
    names+=(dockerhub)
fi

for index in "${!destinations[@]}"; do
    prefix=${destinations[$index]}
    name=${names[$index]}
    /usr/bin/time -o "$RESULTS_DIR/push-$name-time.txt" -f 'elapsed_seconds=%e' \
        make --trace push-images IMAGE_PREFIX="$prefix" 2>&1 | tee "$RESULTS_DIR/push-$name.log"
    if grep -q 'Building image\|docker buildx build' "$RESULTS_DIR/push-$name.log"; then
        echo 'Unexpected image build during publishing' >&2
        exit 1
    fi
    for component in "${components[@]}"; do
        local_manifest="$RESULTS_DIR/vc-$component-source.json"
        remote_manifest="$RESULTS_DIR/vc-$component-$name.json"
        skopeo inspect --raw "oci-archive:$IMAGES_DIR/vc-$component-$TAG.tar" > "$local_manifest"
        jq -e 'any(.manifests[]; .platform.os == "linux" and .platform.architecture == "amd64") and
            any(.manifests[]; .platform.os == "linux" and .platform.architecture == "arm64") and
            ([.manifests[] | select(.annotations["vnd.docker.reference.type"] == "attestation-manifest")] | length >= 2)' \
            "$local_manifest" >/dev/null
        skopeo inspect --raw "docker://$prefix/vc-$component:$TAG" > "$remote_manifest"
        cmp "$local_manifest" "$remote_manifest"
        while read -r digest; do
            child_manifest="$RESULTS_DIR/vc-$component-$name-${digest#sha256:}.json"
            skopeo inspect --raw "docker://$prefix/vc-$component@$digest" > "$child_manifest"
            [[ "$(skopeo manifest-digest "$child_manifest")" == "$digest" ]]
        done < <(jq -r '.manifests[].digest' "$local_manifest")
        printf '%s vc-%s %s\n' "$name" "$component" "$(skopeo manifest-digest "$remote_manifest")" >> "$RESULTS_DIR/digests.txt"
    done
done

make push-images IMAGE_PREFIX="$GHCR_PREFIX" 2>&1 | tee "$RESULTS_DIR/repeat-publish.log"
if make push-images IMAGE_PREFIX=localhost:5000/pr6296-negative IMAGE_COMPONENTS=scheduler \
    DOCKER_PLATFORMS=linux/s390x > "$RESULTS_DIR/missing-platform.log" 2>&1; then
    echo 'Missing architecture was accepted' >&2
    exit 1
fi
grep -q 'Missing platform linux/s390x' "$RESULTS_DIR/missing-platform.log"
if make push-images IMAGE_PREFIX=localhost:5000/pr6296-negative IMAGE_COMPONENTS=scheduler \
    TAG=missing-archive > "$RESULTS_DIR/missing-archive.log" 2>&1; then
    echo 'Missing archive was accepted' >&2
    exit 1
fi
sha256sum --check "$RESULTS_DIR/archives.sha256"
{
    printf 'Source: `%s`\n\nMode: `%s`\n\nTag: `%s`\n\n' "$SOURCE_SHA" "$BUILD_MODE" "$TAG"
    printf 'Passed: architecture and attestation checks, exact index and child-manifest digests, repeat publishing, missing architecture/archive rejection, unchanged archives.\n\n'
    if [[ "$BUILD_MODE" == smoke ]]; then
        printf 'Smoke mode uses one small fixture under six component filenames; it does not build Volcano components.\n\n'
    fi
    if [[ -z "$DOCKERHUB_NAMESPACE" ]]; then
        printf 'Docker Hub publishing was NOT tested: no test namespace was selected.\n\n'
    fi
    printf 'This run tests publishing; it does not deploy Volcano or run the release workflow unit/verification steps.\n\n'
    cat "$RESULTS_DIR"/*-time.txt
} | tee "$RESULTS_DIR/summary.md" >> "$GITHUB_STEP_SUMMARY"
