import json
from collections import defaultdict, OrderedDict
import pdb
import rdflib
from rdflib import *
import re
import itertools


def is_in_list(good_items, test_list):
    for row in good_items:
        if row in test_list:
            return True
    return False

def is_useful_line(splitted):
    if is_in_list(['{', '}', 'def', 'use'], splitted)\
            and not is_in_list(['new', 'Contains', 'also'], splitted):
        return True
    return False

files = [
    'haystack-phdef/ph-def-2018-08-10/phIoT/lib/AirPoint.phd',
    'haystack-phdef/ph-def-2018-08-10/phIoT/lib/WaterPoint.phd',
    'haystack-phdef/ph-def-2018-08-10/phIoT/lib/Point.phd',
    'haystack-phdef/ph-def-2018-08-10/phIoT/lib/Choices.phd',
]

tag_orders = {
    'WaterPoint': ['WaterPointSection', 'WaterType', 'Resource', 'WaterPointQuantity', 'PointType'],
    'AirPoint': ['AirPointSection', 'Resource', 'AirPointQuantity', 'PointType'],
}



# Parsing *.phd
head = defaultdict(dict)
stack = [head]
node_name = None
parents = {}
for filename in files:
    with open(filename, 'r') as fp:
        lines = fp.readlines()

    for line in lines:
        if '//' in line:
            line = line[:line.index('//')]
        splitted = line.split()
        if not is_useful_line(splitted):
            continue
        if splitted == ['{']:
            stack.append(stack[-1][node_name])
        elif splitted == ['}']:
            stack.pop()
        elif 'def' in splitted:
            try:
                _, node_name, _, parent = splitted
            except:
                pdb.set_trace()
            if node_name[-1] == '!':
                node_name = node_name[:-1]
            stack[-1][node_name] = defaultdict(dict)
            parents[node_name] = parent
        elif 'use' in splitted:
            _, node_name = splitted
            uses = stack[-1].get('use', [])
            uses.append(splitted[1])
            stack[-1]['use'] = uses
        else:
            assert False

hs_dict = dict(stack[0])
with open('haystack.json', 'w') as fp:
    json.dump(hs_dict, fp, indent=2)


g = rdflib.Graph()
HS= Namespace('https://project-haystack.org#')
BRICK = Namespace('https://brickschema.org#')
g.bind('hs', HS)
g.bind('brick', BRICK)
for child, parent in parents.items():
    child = HS[child]
    parent = HS[parent]
    g.add((child, RDFS.subClassOf, parent))

tagsets = []
for name, content in hs_dict.items():
    base_tags = re.findall('[A-Z][a-z]+', name)
    uses = content.get('use', [])
    cands = defaultdict(list)
    uses = tag_orders.get(name, uses)
    for use in uses:
        if use == 'Resource':
            if name == 'WaterPoint':
                cands[use] = ['water']
            elif name == 'AirPoint':
                cands[use] = ['air']
        else:
            cands[use] = list(hs_dict[use].keys())
    if 'Point' in name:
        points = list(hs_dict['PointType'].keys())
    combs = list(itertools.product(*(list(cands.values()))))
    combs = ['_'.join([tag for tag in tags if tag]) for tags in combs if tags]
    if name in ['WaterPoint', 'AirPoint']:
        tagsets += combs

with open('tagsets.json', 'w') as fp:
    json.dump(tagsets, fp, indent=2)



g.serialize('test.ttl', format='turtle')
