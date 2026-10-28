#!/usr/bin/env sh
# Copyright 2026 The Volcano Authors.
# Licensed under the Apache License, Version 2.0.
set -eu

guide_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
guide_port=${DRA_GUIDE_PORT:-8080}
guide_bind=${DRA_GUIDE_BIND:-0.0.0.0}
guide_name=${DRA_GUIDE_NAME:-dra-visual-guide}
guide_image=${DRA_GUIDE_IMAGE:-nginx:stable-alpine}

if ! command -v docker >/dev/null 2>&1; then
    printf '%s\n' '需要 Docker。也可在此目录运行 python3 -m http.server 8080。' >&2
    exit 1
fi

docker run --detach --name "$guide_name" --restart unless-stopped \
    --publish "$guide_bind:$guide_port:80" \
    --mount "type=bind,src=$guide_dir,dst=/usr/share/nginx/html,readonly" \
    "$guide_image"
printf '图解已启动：http://localhost:%s（远程访问时换成服务器地址）\n' "$guide_port"
printf '停止并移除：docker rm -f %s\n' "$guide_name"
