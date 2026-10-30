"""Companion excerpts for mappings whose full fields do not fit on a slide.
These omit Pod templates, metadata and resource requests; they are not manifests.
"""
from copy import deepcopy
import yaml


def write_examples(root):
    path=root/'examples'
    def save(name,data):
        (path/name).write_text(yaml.safe_dump(data,sort_keys=False,default_flow_style=False))
    kthena=yaml.safe_load((path/'kthena-modelserving-topology-spec.yaml').read_text())
    roles=yaml.safe_load((path/'kthena-roles.yaml').read_text())['roles']
    kthena['template']['roles']=roles
    save('kthena-modelserving-spec.yaml',kthena)
    pg={'minMember':8,'networkTopology':deepcopy(kthena['template']['networkTopology']['groupPolicy']),'subGroupPolicy':[]}
    for role in roles:
        pg['subGroupPolicy'].append({'name':role['name'],'labelSelector':{'matchLabels':{'modelserving.volcano.sh/name':'sample','modelserving.volcano.sh/role':role['name']}},'matchLabelKeys':['modelserving.volcano.sh/role-id'],'subGroupSize':1+role['workerReplicas'],'minSubGroups':kthena['template']['gangPolicy']['minRoleReplicas'][role['name']],'networkTopology':deepcopy(kthena['template']['networkTopology']['rolePolicy'])})
    save('kthena-mapping.yaml',{'modelServingSpec':kthena,'podGroupSpec':pg})
    ray=yaml.safe_load((path/'kuberay-raycluster-spec.yaml').read_text())
    worker=yaml.safe_load((path/'kuberay-subgroup-spec.yaml').read_text())['subGroupPolicy'][0]
    head={'name':'headgroup','subGroupSize':1,'minSubGroups':1,'labelSelector':{'matchLabels':{'ray.io/group':'headgroup'}},'matchLabelKeys':['ray.io/group']}
    save('kuberay-mapping.yaml',{'rayClusterSpec':ray,'podGroupSpec':{'minMember':5,'subGroupPolicy':[head,worker]}})
    for stale in ['ray-subgroup-spec.yaml','ray-worker-group.yaml']:
        (path/stale).unlink(missing_ok=True)
    grove=yaml.safe_load((path/'grove-podgang-spec.yaml').read_text())
    groups=[]
    for g in grove['podGroups']:
        groups.append({'name':g['name'],'subGroupSize':max(g['minReplicas'],1),'minSubGroups':1,'labelSelector':{'matchLabels':{'grove.io/podclique':g['name']}},'matchLabelKeys':['grove.io/podclique']})
    save('grove-mapping.yaml',{'podGangSpec':grove,'podGroupSpec':{'minMember':6,'subGroupPolicy':groups}})
