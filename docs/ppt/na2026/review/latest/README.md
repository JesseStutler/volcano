# Latest 预览

[PDF](../../../Volcano_KubeCon_NA_2026.pdf) · [PPT](../../../Volcano_KubeCon_NA_2026.pptx?raw=true) · [大纲](../../../Volcano_KubeCon_NA_2026_outline.zh-CN.md)

26 页，使用 NA 2026 官方模板。封面留白和标题已调整，文字分隔符已清理，英文备注改成无圆点段落并补充讲解例子。

重点页面：[工作负载](slide-04.png) · [协同框架](slide-05.png) · [NodeShard](slide-06.png) · [组结构引入](slide-08.png) · [Gang 抢占](slide-12.png) · [Kthena 配置](slide-16.png) / [映射](slide-17.png) · [KubeRay](slide-18.png) · [Grove](slide-19.png) · [社区](slide-26.png)。

[本轮重点预览](refinement.png)：第 17–19 页生态数量映射、第 25 页 xPU / DRA 方向。

[模板和文字检查](template-check.json)。[英文备注格式检查](notes-check.json)。

第 12 页的训练 gang 均需要两个 Pod，且各自留在一个 HyperNode 内。分散抢占四个 job 各一个 Pod 会打断四个 gang；按优先级选择 A、B 两组后，在 West 内模拟四个新 Pod 的放置，可行才提交。[示例数量与范围核对](focus-check.json)。

Roadmap 按 [v1.17 跟踪 issue](https://github.com/volcano-sh/volcano/issues/6166) 选取与本场相关的方向，不表示官方优先级排序。

## 技术核对

左右配图和页面 YAML 使用同一组最低 Pod 数量：Kthena 为 1 个 Prefill replica 加 3 个 Decode replicas，每个包含 Entry 和 Worker，共 8 Pods；KubeRay 为 1 个 head 加 2 组双 host worker，共 5 Pods；Grove 为 2 个 Prefill 加 4 个 Decode，共 6 Pods。KubeRay 页面补齐 head policy。蓝色表示最低组数，绿色表示每组 Pod 数，紫色表示总 Pod 数；YAML 下方给出计算规则。Kthena 明确展示 minRoleReplicas 和每组额外的 Entry，KubeRay 明确加上独立的 Head，Grove 的 minReplicas 对应组内 Pod 数。

xPU / DRA 补充 binpack、DRA-backed extended resources、ResourceClaim 抢占与回收。Extended resources 是已有上游路径，备注说明后续集成与验证。

Kthena 使用共享的 `template.networkTopology.rolePolicy`。KubeRay 示例开启 autoscaling，使 `minReplicas` 对应 `minSubGroups`。Grove 使用 `grove.io/podclique` 标签。

屏幕 YAML 是关键字段片段。[Kthena](../../examples/kthena-mapping.yaml)、[KubeRay](../../examples/kuberay-mapping.yaml)、[Grove](../../examples/grove-mapping.yaml) 的配套文件补充省略的 group / selector；包装键用于阅读对照，文件不是可直接 apply 的 manifest。

生态状态核查到 2026-10-30，DRA 方向核查到 2026-10-31：[源码版本与 PR 状态](../../fact-checks.json)。讲解提示见 [英文 Speaker Notes](../../speaker-notes.md)，技术来源见 [slide-sources.json](../../slide-sources.json)。

## 检查

检查全部 26 页导出结果、文字边界、流程箭头、连线文字避让、PPT 内嵌 PNG、YAML 块格式和映射数值。物理网络连线保留原 fabric 风格。

[二维码解码](qr-check.json) · [链接核对](qr-links-check.json) · [映射核对](mapping-check.json) / [左右图中 Pod 数量](mapping-diagram-check.json) · [PDF/PPT 校验值](checksums.json)。

官网和 GitHub 返回正常页面。Slack 二维码与项目 README 的 `#volcano` 频道地址一致；未登录访问会跳到工作区入口，本次未验证登录后的频道内容。
