"""r8 is a light edit of r5. Keep explanatory paragraphs and their positions.

Remove only the explicitly listed peripheral comments, plus their footer rules.
Do not use font-size, length, or position as a blanket text-deletion rule.
"""
from lxml import etree
import re


def light_edit(arts):
    removed={}
    comments={
      4:'Schedule complete groups and their locality; keep latency-sensitive capacity ready.',
      13:'Carry roles, replicas, and placement intent from the controller into Volcano.',
      16:'Cooperate at one topology level; isolate replicas at a finer level.',
      18:'The harness controls the scenario and records observations; KWOK does not execute GPU work.',
      19:'Harness available. Next: cross-scheduler runs and representative scenarios.',
      21:'Bring a controller mapping, a placement requirement, or a reproducible workload to the community.',
    }
    extra_comments={
      14:{'Pod templates omitted.'},
      19:{'¹ Planned comparison set; match workload semantics and record unsupported constraints.'},
    }
    wording={
      'TRAINING':'Training','INFERENCE':'Inference','AGENTS':'Agents',
      'PHYSICAL FABRIC':'Physical fabric',
      'PROPOSED · SUBGROUP RELATIONSHIPS':'Proposed SubGroup relationships',
      'IN PROGRESS':'In progress','PLANNED':'Planned',
      'SCENARIO':'Scenario','CLUSTER UNDER TEST':'Cluster under test','OBSERVATION':'Observation',
      'ONE WORKLOAD, REPLAYED':'One workload, replayed','CROSS-SCHEDULER TESTING':'Planned comparisons',
      'TEST SHAPE':'Test shape','WHAT TO VARY':'What to vary','WHAT TO OBSERVE':'What to observe',
      'WORKSTREAM':'Workstream','NEXT STEP':'Next step','WHAT TO VALIDATE':'What to validate',
      'Kubernetes scheduler¹':'Kubernetes scheduler','Other schedulers¹':'Other schedulers',
      'Grouping view, not a topology guarantee. Gang support is merged; replica topology is still in progress.':'Gang support is merged. Replica topology is in progress.',
      'Gang / SubGroup mapping is available; topologyConstraint is not yet supported.':'Gang and SubGroup mapping are available. Topology support is pending.',
      'Find the best-fit scenarios and their tradeoffs; validate topology-aware gang placement.':'Find the best-fit scenarios and test topology-aware gang placement.',
    }
    for n,a in arts.items():
        removed[n]=[];targets=extra_comments.get(n,set())|({comments[n]} if n in comments else set())
        out=[]
        for fragment in a.front:
            wrapper=etree.fromstring(('<g>'+fragment+'</g>').encode())
            for e in list(wrapper):
                if e.tag!='text':continue
                label=' '.join(' '.join(e.itertext()).split())
                # Keep the explanation; replace stitched semicolons with sentences.
                for part in e.iter():
                    if part.text:part.text=re.sub(r';\s+([a-z])',lambda m:'. '+m.group(1).upper(),part.text)
                if label in targets:
                    removed[n].append(label);wrapper.remove(e)
                elif label in wording:
                    for child in list(e):e.remove(child)
                    e.text=wording[label]
            out.append(''.join(etree.tostring(e,encoding='unicode') for e in wrapper))
        a.front=out
        if n in comments:
            assert comments[n] in removed[n],(n,'r5 comment not found')
            a.routes=[r for r in a.routes if not (r['points'][0][0]==0 and r['points'][-1][0]==1480 and r['points'][0][1]>=510)]
            a.edges=[s for s in a.edges if not any(f'M0,{y} L1480,{y}' in s for y in [511,513])]
    return removed
