# Latest 预览

[PDF](../../../Volcano_KubeCon_NA_2026.pdf) · [PPT](../../../Volcano_KubeCon_NA_2026.pptx?raw=true) · [大纲](../../../Volcano_KubeCon_NA_2026_outline.zh-CN.md)

26 页，使用 NA 2026 官方模板。封面留白和标题已调整，文字分隔符已清理，英文备注改成无圆点段落并补充讲解例子。

重点页面：[工作负载](slide-04.png) · [协同框架](slide-05.png) · [NodeShard](slide-06.png) · [组结构引入](slide-08.png) · [Gang 抢占](slide-12.png) · [Kthena 配置](slide-16.png) / [映射](slide-17.png) · [KubeRay](slide-18.png) · [Grove](slide-19.png) · [社区](slide-26.png)。

[本轮重点预览](refinement.png)：第 12 页 gang 抢占、第 20 页 RBG 集成范围、第 23 页横向 benchmark 实验流程、第 25 页 v1.17 Roadmap。

[模板和文字检查](template-check.json)。[英文备注格式检查](notes-check.json)。

第 12 页的训练 gang 均需要两个 Pod，且各自留在一个 HyperNode 内。分散抢占四个 job 各一个 Pod 会打断四个 gang；按优先级选择 A、B 两组后，在 West 内模拟四个新 Pod 的放置，可行才提交。[示例数量与范围核对](focus-check.json)。

Roadmap 按 [v1.17 跟踪 issue](https://github.com/volcano-sh/volcano/issues/6166) 选取与本场相关的方向，不表示官方优先级排序。

## 技术核对

Kthena 使用共享的 `template.networkTopology.rolePolicy`。KubeRay 示例开启 autoscaling，使 `minReplicas` 对应 `minSubGroups`。Grove 使用 `grove.io/podclique` 标签。

屏幕 YAML 是关键字段片段。[Kthena](../../examples/kthena-mapping.yaml)、[KubeRay](../../examples/kuberay-mapping.yaml)、[Grove](../../examples/grove-mapping.yaml) 的配套文件补充省略的 group / selector；包装键用于阅读对照，文件不是可直接 apply 的 manifest。

状态核查到 2026-10-30：[源码版本与 PR 状态](../../fact-checks.json)。讲解提示见 [英文 Speaker Notes](../../speaker-notes.md)，技术来源见 [slide-sources.json](../../slide-sources.json)。

## 检查

检查全部 26 页导出结果、文字边界、流程箭头、连线文字避让、PPT 内嵌 PNG、YAML 块格式和映射数值。物理网络连线保留原 fabric 风格。

[二维码解码](qr-check.json) · [链接核对](qr-links-check.json) · [映射核对](mapping-check.json) · [PDF/PPT 校验值](checksums.json)。

官网和 GitHub 返回正常页面。Slack 二维码与项目 README 的 `#volcano` 频道地址一致；未登录访问会跳到工作区入口，本次未验证登录后的频道内容。
