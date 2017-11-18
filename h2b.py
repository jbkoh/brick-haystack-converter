import json
from uuid import uuid4 as gen_uuid
import numpy as np
import rdflib
import argparse
import rdflib
import pdb

from functools import reduce
adder = lambda x,y: x + y

def str2slist(s):
    s.replace(' ', '')
    return s.split(',')

def str2ilist(s):
    s.replace(' ', '')
    return [int(c) for c in s.split(',')]

def str2bool(v):
    if v in ['true', 'True']:
        return True
    elif v in ['false', 'False']:
        return False
    else:
        assert(False)

parser = argparse.ArgumentParser()
parser.register('type','bool',str2bool)
parser.register('type','slist', str2slist)
parser.register('type','ilist', str2ilist)
parser.add_argument('-src', type=str, dest='srcfile', help='Haystack instance in JSON')
args = parser.parse_args()

################ Init base information ##############

# Load Brick
brick_tag_g = rdflib.Graph()
brick_tag_g.parse('brick/BrickTag.ttl', format='turtle')
res = brick_tag_g.query("""
select ?s where {
?s <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ <https://brickschema.org/schema/1.0.1/BrickFrame#Tag> .
}""")
brick_tags = [row[0].split('#')[-1] for row in res]
with open('brick/bh_map.json', 'r') as fp:
    bh_map = json.load(fp)

# Load Haystack
with open('haystack/tags.csv', 'r') as fp:
    raw_tags = fp.readlines()
h_tags = dict()
for row in raw_tags:
    [tag, tag_type] = row.split(',')
    h_tags[tag] = tag_type[:-1]

# Add Haystack tags to bh_map
not_found_h_tags = set([h_tag for h_tag in set(h_tags.keys())
                        if h_tag not in reduce(adder, bh_map.keys()) and 
                           'Ref' not in h_tag])
for brick_tag in brick_tags:
    brick_tag = brick_tag.lower()
    for h_tag in h_tags.keys():
        if brick_tag == h_tag:
            bh_map[h_tag] = [brick_tag]
            if h_tag in not_found_h_tags:
                not_found_h_tags.remove(h_tag)
with open('brick/bh_map.json', 'w') as fp:
    json.dump(bh_map, fp, indent=2)
print(sorted(not_found_h_tags))
pdb.set_trace()


################ Start Converting ##############

# Load Haystack Instance
with open(args.srcfile, 'r') as fp:
    data = json.load(fp)

for row in data:
    entity_tags = list()
    identifier = gen_uuid()
    for (tag, value) in row.items():
        if tag == 'id':
            identifier = value
        elif value in ['Marker' , 'm:']:
            entity_tags += tag
        elif 'r:' in value:
            ref = value[2:].split()[0]
        elif 'Ref' in tag:
            pass
        elif np.isnan(value):
            pass
    # Determine is-a relationship from the tag set.

