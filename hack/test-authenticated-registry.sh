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
[[ -z "$(git status --porcelain)" ]]

expect_auth_failure() {
    local label=$1
    shift
    if "$@" > "$RESULTS_DIR/$label.log" 2>&1; then
        echo "Expected authentication failure: $label" >&2
        exit 1
    fi
    grep -Eqi 'unauthorized|authentication required|invalid username/password|invalid credentials' "$RESULTS_DIR/$label.log"
    printf '%s: correctly rejected\n' "$label" | tee -a "$RESULTS_DIR/auth-checks.txt"
}

case "$1" in
    restore)
        [[ "$(head -n 1 "$EVIDENCE_DIR/summary.md")" == "$(printf 'Source: `%s`' "$SOURCE_SHA")" ]]
        for component in "${components[@]}"; do
            digest=$(awk -v image="vc-$component" '$1 == "ghcr" && $2 == image {print $3}' "$EVIDENCE_DIR/digests.txt")
            [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
            skopeo copy --all --preserve-digests "docker://$GHCR_PREFIX/vc-$component@$digest" \
                "oci-archive:$IMAGES_DIR/vc-$component-$TAG.tar" 2>&1 | tee "$RESULTS_DIR/restore-$component.log"
            manifest="$RESULTS_DIR/vc-$component-source.json"
            skopeo inspect --raw "oci-archive:$IMAGES_DIR/vc-$component-$TAG.tar" > "$manifest"
            [[ "$(skopeo manifest-digest "$manifest")" == "$digest" ]]
            cmp "$EVIDENCE_DIR/vc-$component-source.json" "$manifest"
            ln "$IMAGES_DIR/vc-$component-$TAG.tar" "$IMAGES_DIR/vc-$component-latest.tar"
            ln "$IMAGES_DIR/vc-$component-$TAG.tar" "$IMAGES_DIR/vc-$component-v0.0.0-pr6296-test.tar"
        done
        sha256sum "$IMAGES_DIR"/*.tar > "$RESULTS_DIR/archives.sha256"
        { git rev-parse HEAD; skopeo --version; docker version; } > "$RESULTS_DIR/versions.txt"
        ;;
    anonymous)
        for port in 5443 5444; do
            expect_auth_failure "anonymous-$port" make push-images IMAGE_COMPONENTS=scheduler IMAGE_PREFIX="localhost:$port/volcanosh"
        done
        ;;
    publish-a)
        wrong_auth="$RUNNER_TEMP/wrong-registry-auth.json"
        wrong_value=$(printf 'wrong-user:wrong-password' | base64 -w0)
        jq -n --arg auth "$wrong_value" '{auths:{"localhost:5443":{auth:$auth}}}' > "$wrong_auth"
        expect_auth_failure wrong-credentials env REGISTRY_AUTH_FILE="$wrong_auth" \
            make push-images IMAGE_COMPONENTS=scheduler IMAGE_PREFIX=localhost:5443/volcanosh
        /usr/bin/time -o "$RESULTS_DIR/push-a-time.txt" -f 'elapsed_seconds=%e' \
            make --trace push-images IMAGE_PREFIX=localhost:5443/volcanosh TAG=latest 2>&1 | tee "$RESULTS_DIR/push-a.log"
        ;;
    verify)
        /usr/bin/time -o "$RESULTS_DIR/push-b-time.txt" -f 'elapsed_seconds=%e' \
            make --trace push-images IMAGE_PREFIX=localhost:5444/volcanosh TAG=v0.0.0-pr6296-test 2>&1 | tee "$RESULTS_DIR/push-b.log"
        # The second login must retain the first registry's independent credentials.
        make --trace push-images IMAGE_PREFIX=localhost:5443/volcanosh TAG=latest 2>&1 | tee "$RESULTS_DIR/repeat-a.log"
        for port in 5443 5444; do
            image_tag=latest
            if [[ "$port" == 5444 ]]; then image_tag=v0.0.0-pr6296-test; fi
            for component in "${components[@]}"; do
                destination="docker://localhost:$port/volcanosh/vc-$component:$image_tag"
                manifest="$RESULTS_DIR/vc-$component-$port.json"
                skopeo inspect --raw "$destination" > "$manifest"
                cmp "$RESULTS_DIR/vc-$component-source.json" "$manifest"
                jq -e 'any(.manifests[]; .platform.os == "linux" and .platform.architecture == "amd64") and
                    any(.manifests[]; .platform.os == "linux" and .platform.architecture == "arm64") and
                    ([.manifests[] | select(.annotations["vnd.docker.reference.type"] == "attestation-manifest")] | length >= 2)' "$manifest" >/dev/null
                # Download every platform and attestation, including the actual layer blobs.
                skopeo copy --all --preserve-digests "$destination" "oci-archive:$RUNNER_TEMP/roundtrip.tar" \
                    > "$RESULTS_DIR/download-$component-$port.log" 2>&1
                skopeo inspect --raw "oci-archive:$RUNNER_TEMP/roundtrip.tar" > "$RESULTS_DIR/vc-$component-$port-roundtrip.json"
                cmp "$manifest" "$RESULTS_DIR/vc-$component-$port-roundtrip.json"
                rm "$RUNNER_TEMP/roundtrip.tar"
                printf '%s vc-%s:%s %s\n' "$port" "$component" "$image_tag" "$(skopeo manifest-digest "$manifest")" >> "$RESULTS_DIR/digests.txt"
            done
        done
        if grep -Eq 'Building image|docker buildx build' "$RESULTS_DIR"/push-*.log "$RESULTS_DIR/repeat-a.log"; then
            echo 'Unexpected rebuild during publishing' >&2
            exit 1
        fi
        sha256sum --check "$RESULTS_DIR/archives.sha256"
        [[ -z "$(git status --porcelain)" ]]
        {
            printf 'Source: `%s` (unchanged)\n\nOriginal full build run: `%s`\n\n' "$SOURCE_SHA" "$BUILD_RUN_ID"
            printf 'Reused all six real images by digest; no rebuild.\n\n'
            printf 'Passed: trusted HTTPS, separate Docker login credentials, anonymous and wrong-password rejection, latest and version tags, repeated publishing, unchanged archives, exact manifests, amd64/arm64 and attestations, full blob downloads from both registries.\n\n'
            printf 'This simulates authenticated registry publishing. It does NOT test Docker Hub itself, its token service, namespace permissions, or rate limits.\n\n'
            cat "$RESULTS_DIR"/*-time.txt
        } | tee "$RESULTS_DIR/summary.md" >> "$GITHUB_STEP_SUMMARY"
        ;;
    *) exit 2 ;;
esac
