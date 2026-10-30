# Latest 预览

[PDF](../../../Volcano_KubeCon_NA_2026.pdf) · [PPT](../../../Volcano_KubeCon_NA_2026.pptx?raw=true) · [大纲](../../../Volcano_KubeCon_NA_2026_outline.zh-CN.md)

26 页。架构、NodeShard、PG/SG、HyperNode、拓扑及 Kthena 图继续复用 China/EU 素材。

重点页面：[工作负载](slide-04.png) · [协同框架](slide-05.png) · [NodeShard](slide-06.png) · [组结构引入](slide-08.png) · [Gang 抢占](slide-12.png) · [Kthena 配置](slide-16.png) / [映射](slide-17.png) · [KubeRay](slide-18.png) · [Grove](slide-19.png) · [社区](slide-26.png)。

[本轮五页集中预览](refinement.png)：第 4、5、6、9、12 页。

## 技术核对

Kthena 使用共享的 `template.networkTopology.rolePolicy`。KubeRay 示例开启 autoscaling，使 `minReplicas` 对应 `minSubGroups`。Grove 使用 `grove.io/podclique` 标签。

屏幕 YAML 是关键字段片段。[Kthena](../../examples/kthena-mapping.yaml)、[KubeRay](../../examples/kuberay-mapping.yaml)、[Grove](../../examples/grove-mapping.yaml) 的配套文件补充省略的 group / selector；包装键用于阅读对照，文件不是可直接 apply 的 manifest。

状态核查到 2026-10-30：[源码版本与 PR 状态](../../fact-checks.json)。相关功能限制和来源在讲者备注中。

## 检查

检查全部 26 页导出结果、文字边界、流程箭头、连线文字避让、PPT 内嵌 PNG、YAML 块格式和映射数值。物理网络连线保留原 fabric 风格。

[二维码解码](qr-check.json) · [映射核对](mapping-check.json) · [PDF/PPT 校验值](checksums.json)。
