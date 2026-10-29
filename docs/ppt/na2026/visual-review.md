# 本轮视觉与内容调整

主要参照第 10 页沿用的 **Place Groups at Different Topology Levels**。保留六张 EU / China 原图；新增图用同类交换机、节点、网络连线和分组边界，减少整块底色与抽象卡片。

| 页 | 改动 |
|---|---|
| 4 | 取消横向三栏：左侧训练 rank 与 collective，右上 agent 调用链，右下推理 P/D 角色与 KV transfer |
| 6、11、15 | NodeShard、anti-affinity、KubeRay 的行内 YAML 全部展开 |
| 10 | YAML 使用 `highestTierName`；保留原图，补 core / spine / leaf 与数字层级的对应 |
| 11 | 画出共享网络下的两个 Supernode，各自容纳一个完整实例 |
| 13 | 增加 RBG 推进中、Kubeflow 计划深化、LWS multi-group 方向；与已有基础接入分开说明 |
| 15、16 | 展示具体副本成员、协作组与放置域；KubeRay topology 和 SubGroup 关系仍标明推进状态 |

RBG 的 [gang 文档](https://github.com/sgl-project/rbg/blob/main/doc/features/gang-scheduling.md) 已有 RoleInstance → SubGroup 映射；[LWS](https://github.com/kubernetes-sigs/lws/blob/main/README.md) 已有副本组与多角色工作负载基础。生态页右侧表达 maintainer 的后续集成计划，不把现有基础写成尚未支持。

## 检查

22 页 PDF / PPT、讲者备注与文本边界已检查。8 份 YAML 片段均可解析，没有 flow mapping / flow sequence；它们仍是省略字段的讲解片段。新增连线固定端点，未穿过文字。SVG 保留编辑能力，PPT 使用对应 PNG。六张复用 PNG 的内容未改变。

保留上一轮加深后的正文与连线；去掉新增图的深色底部横条和代码标题底色。会场投影效果仍需现场确认。

## 重点页前后对照

左侧为上版，右侧为本轮。依次为第 4、11、13、15 页。

![重点页前后对照](review/before-after.png)
