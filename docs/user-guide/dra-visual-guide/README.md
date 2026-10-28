# DRA 图解：从整卡到 vGPU 共享

读 DRA API 时最容易卡住的地方，是几个对象都有设备信息，却不知道它们怎么连起来。
这份图解从一个 Pod 申请一张 GPU 开始，再逐步加入 Pool、容量共享和 HAMi 的实际用法。

**[打开在线图解](https://dra-field-guide-jesse.heartybread19.chatgpt.site)**（Sites 私有站点，需所有者登录）。
也可以下载整个目录，直接用浏览器打开 [index.html](index.html)，无需联网或安装依赖。

每个场景是一张独立页面，左侧导航可以跳转。页面上先看图，再点资源查看对应的 YAML；
图中的资源也可以点击。YAML 支持复制、下载，SVG 和 PNG 可以单独保存。

## 选一个场景

| 场景 | 主要看什么 | 文件 |
|---|---|---|
| [01 · 先申请一张 GPU](01-node-local.html) | Pod、Claim、Class、Slice、Node 怎么连接 | [YAML](examples/01-node-local.yaml) · [PNG](assets/01-node-local.png) |
| [02 · Class 可以重叠](02-overlapping-classes.html) | 两个 Class 能同时匹配同一张卡 | [YAML](examples/02-overlapping-classes.yaml) · [PNG](assets/02-overlapping-classes.png) |
| [03 · 两个 Pod 共用 Claim](03-shared-claim.html) | 两次引用，一份 allocation | [YAML](examples/03-shared-claim.yaml) · [PNG](assets/03-shared-claim.png) |
| [04 · 一个 Pool，多个 Slice](04-pool-slices.html) | Pool 是库存分组，Slice 是发布库存的对象 | [YAML](examples/04-pool-slices.yaml) · [PNG](assets/04-pool-slices.png) |
| [05 · 按显存和算力分配](05-consumable-capacity.html) | 两个独立 Claim 消耗同一设备的容量；可以改数字试算 | [YAML](examples/05-consumable-capacity.yaml) · [PNG](assets/05-consumable-capacity.png) |
| [06 · HAMi：两份 vGPU](06-hami-native.html) | 实际 driver/Class 名称、cores/memory、运行时限制 | [用户 YAML](examples/06-hami-native.yaml) · [库存示意](observations/06-hami-inventory.yaml) · [PNG](assets/06-hami-native.png) |
| [07 · HAMi：兼容旧式 YAML](07-hami-webhook.html) | Pod limits 如何经 webhook 转成 Claim | [提交 YAML](examples/07-hami-webhook.yaml) · [转换示意](observations/07-hami-webhook-result.yaml) · [PNG](assets/07-hami-webhook.png) |

GitHub 不会直接渲染 HTML，可以使用在线站点、下载离线打开，或按下面的方式部署。

## 一条命令部署

服务器已经有 Docker 时，在仓库根目录运行：

```sh
./docs/user-guide/dra-visual-guide/serve.sh
```

访问 `http://服务器地址:8080`。脚本会启动 Nginx 容器，监听全部网卡的 8080 端口，
并只读挂载此目录。首次运行需要拉取镜像；端口需允许客户端访问。
HTML 已生成，部署不用 Python、Node.js 或 npm。

修改端口或只供本机访问：

```sh
DRA_GUIDE_PORT=9000 DRA_GUIDE_BIND=127.0.0.1 ./docs/user-guide/dra-visual-guide/serve.sh
```

停止并移除容器：

```sh
docker rm -f dra-visual-guide
```

再次部署前先移除同名容器。已有容器会直接读取目录里的新文件，修改文件后刷新即可。
如果团队要求固定镜像，可用 `DRA_GUIDE_IMAGE` 指定审核过的 Nginx tag 或 digest；
`DRA_GUIDE_NAME` 可修改容器名称。

不用 Docker，也可以本地预览：

```sh
cd docs/user-guide/dra-visual-guide
python3 -m http.server 8080 --bind 127.0.0.1
```

或者将本目录的 HTML、`assets/`、`examples/`、`observations/` 和 README 复制到任意静态网站。
全部链接是相对路径，放在网站的子目录也可以使用。

## 示例的运行范围

前五页使用假想驱动 `gpu.example.com`，用于解释 API；手工创建这些对象不会生成 GPU。
Node 通常由 kubelet 注册，ResourceSlice 由真实驱动发布。各场景是独立例子，有同名对象，
不要把所有 YAML 一起 apply。

HAMi 两页根据社区源码整理：

- NVIDIA HAMi-Core driver **v0.1.1**，commit `9475a1b344e7e5fb8310d47de398199101f8d0ba`。
- HAMi-DRA chart / webhook，commit `420a4031762301ca1a3335e34875780b6de94fb5`。
- API 基线为 Kubernetes **1.36**。`DRAConsumableCapacity` 在该版本为 beta、默认启用；
  1.34–1.35 需要显式启用，还要配套支持它的 scheduler、driver 和 CDI runtime。

`observations/` 中的库存、分配和 webhook 转换结果是**只读教学示意**。
HAMi 库存假定 GPU 有 24Gi 显存，名称和属性做了简化；webhook 的生成名字也已简化。
用户提交文件在 `examples/06-hami-native.yaml` 和 `examples/07-hami-webhook.yaml`。
运行前需要按官方说明安装 HAMi-DRA，不能用库存示意替代驱动安装。

第 3 页的同 Claim 多 Pod 复用是通用 DRA 概念，不是 HAMi 已验证能力。
HAMi 示例采用一个 Pod 对应一个独立 Claim，使用默认调度器；切到 Volcano 前，
需要确认目标版本支持 consumable capacity。我们校验了 API 对象，没有在真实 GPU 集群执行。

## 更新内容

- 修改文字和场景导航：[scenarios.json](scenarios.json)。
- 修改页面布局：[page.template.html](page.template.html)、[guide.css](assets/guide.css)。
- 修改交互：[guide.js](assets/guide.js)。
- 修改图和生成逻辑：[build.py](build.py)。
- 修改 YAML：`examples/` 或 `observations/`。

之后在本目录执行：

```sh
python3 build.py
```

只依赖 Python 标准库，生成 8 个 HTML 页面和 8 个 SVG。YAML 会内嵌进页面，
所以离线查看和切换对象不需要启动服务。改图后还需从 SVG 重新导出对应 PNG，
保持下载的图片与页面一致。页面不依赖 CDN、外部字体或第三方脚本。

## 查原文

各页末尾有直接对应的源码链接。主要依据：

- [Kubernetes 1.36 DRA](https://v1-36.docs.kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/)
- [ResourceSlice API](https://v1-36.docs.kubernetes.io/docs/reference/kubernetes-api/resource/resource-slice-v1/)
- [ResourceClaim API](https://v1-36.docs.kubernetes.io/docs/reference/kubernetes-api/resource/resource-claim-v1/)
- [HAMi v0.1.1 容量发布与运行时配置](https://github.com/Project-HAMi/k8s-dra-driver/blob/9475a1b344e7e5fb8310d47de398199101f8d0ba/cmd/hami-kubelet-plugin/hami_core.go)
- [HAMi-DRA 安装说明](https://github.com/Project-HAMi/HAMi-DRA/blob/420a4031762301ca1a3335e34875780b6de94fb5/README.md)
