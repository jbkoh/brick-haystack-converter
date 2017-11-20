import json
from uuid import uuid4 as gen_uuid
from collections import defaultdict
import numpy as np
import rdflib
import rdflib
import pdb
import pandas as pd
from urllib.parse import quote_plus
from functools import reduce
from operator import itemgetter

import rdflib
from rdflib import Namespace, Graph

from jasonhelper import argparser


###### Helper functions

adder = lambda x,y: x + y

def print_g(g):
    print(g.serialize(format='turtle').decode('UTF-8'))

def find_tagset(tags, tagsets):
    score_dict = dict()
    for tagset, sets_of_tags in tagsets.items():
        cmn = sets_of_tags.intersection(tags)
        score_dict[tagset] = len(cmn) / len(sets_of_tags)
    max_score = max(score_dict.values())
    if max_score < 0.75:
        return None
    # TODO: Selection mechanism needs to be more smart.
    #       Currently mapping
    #       {'pressure', 'filter', 'discharge', 'his', 'weatherPoint', 'air', 'sp'}
    #       ->
    #       "Discharge_Air"
    cand = ''
    for tagset, score in score_dict.items():
        if score == max_score:
            if len(cand.split('_')) < len(tagset.split('_')):
                cand = tagset
    return cand


argparser.add_argument('-src', type=str, dest='srcfile', 
                       help='Haystack instance in JSON or Zinc')
args = argparser.parse_args()


################ Init base information ##############

# Load Brick
brick_tag_g = rdflib.Graph()
brick_tag_g.parse('brick/BrickTag.ttl', format='turtle')
res = brick_tag_g.query("""
select ?s where {
?s <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ <https://brickschema.org/schema/1.0.1/BrickFrame#Tag> .
}""")
brick_tags = [row[0].split('#')[-1] for row in res]
with open('brick/hb_map.json', 'r') as fp:
    hb_map = json.load(fp)
RDF = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
RDFS = Namespace('http://www.w3.org/2000/01/rdf-schema#')
BRICK = Namespace('https://brickschema.org/schema/1.0.1/Brick#')
BRICKFRAME = Namespace('https://brickschema.org/schema/1.0.1/BrickFrame#')
BF = BRICKFRAME
OWL = Namespace('http://www.w3.org/2002/07/owl#')
BLDG = Namespace('http://buildsys.org/ontologies/bldg#')
brick_tagset_g = Graph()
brick_tagset_g.parse('brick/Brick.ttl', format='turtle')
res = brick_tagset_g.query("""
select ?s where {
?s <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ <https://brickschema.org/schema/1.0.1/BrickFrame#TagSet> .
}""")
raw_brick_tagsets = [row[0].split('#')[-1].lower() for row in res]
brick_tagsets = dict()
for tagset in raw_brick_tagsets:
    brick_tagsets[tagset] = set(tagset.split('_'))


# Load Haystack
with open('haystack/tags.csv', 'r') as fp:
    raw_tags = fp.readlines()
h_tags = dict()
for row in raw_tags:
    [tag, tag_type] = row.split(',')
    h_tags[tag] = tag_type[:-1]
point_h_tags = set(['sp', 'sensor', 'cmd', 'point'])
equip_h_tags = set(['ahu', 'vav']) # TODO: Complete this

# Add Haystack tags to hb_map
not_found_h_tags = set([h_tag for h_tag in set(h_tags.keys())
                        if h_tag not in reduce(adder, hb_map.keys()) and 
                           'Ref' not in h_tag])
for brick_tag in brick_tags:
    brick_tag = brick_tag.lower()
    for h_tag in h_tags.keys():
        if brick_tag == h_tag:
            hb_map[h_tag] = [brick_tag]
            if h_tag in not_found_h_tags:
                not_found_h_tags.remove(h_tag)
with open('brick/hb_map.json', 'w') as fp:
    json.dump(hb_map, fp, indent=2)


################ ################ ################ 
################ Start Converting ################
################ ################ ################ 

# Load Haystack Instance into a list of dict (data)
srcfile = args.srcfile
ext = srcfile.split('.')[-1]
if ext == 'json':
    with open(srcfile, 'r') as fp:
        data = json.load(fp)
elif ext == 'csv':
    data = []
    df = pd.read_csv(srcfile)
    for (row_num, row) in df.iterrows():
        datum = dict()
        for tag, val in row.items():
            if isinstance(val, float):
                if np.isnan(val):
                    continue
            if tag in h_tags:
                if val == 'M':
                    val = 'm:'
                datum[tag] = val
        data.append(datum)


# Read rows to intantiate Brick
g = Graph() # init graph
entity_dict = defaultdict(list) # To validate if all entities are intantiated.
for row in data:
    entity_h_tags = set()
    identifier = gen_uuid()
    raw_ref_dict = []
    for (tag, value) in row.items():
        if tag == 'id':
            identifier = quote_plus(value)
        elif value in ['Marker' , 'm:']:
            entity_h_tags.add(tag)
        elif 'Ref' in tag:
            ref_type = tag[:-3]
            ref_id = quote_plus(value[1:]) # remove '@'
            entity_dict[ref_type].append(ref_id)
            raw_ref_dict.append((ref_type, ref_id)) 

    # Determine is-a relationship from the tag set.
    if identifier == '%401d552c40-54c9904c+%22AHU+03+Supply+Air+Pressure+Filter+DP%22':
        pdb.set_trace()
    print(entity_h_tags)
    entity_b_tags = set(reduce(adder, [hb_map[h_tag] for h_tag in entity_h_tags 
                                       if h_tag in hb_map], []))
    cand_tagset = find_tagset(entity_b_tags, brick_tagsets)
    if cand_tagset:
        g.add((BLDG[identifier], RDF['type'], BRICK[cand_tagset])) #TODO: 

    # TODO
    # entity_h_tagset = XX
    # entity_dict[entity_h_tagset].append(identifier)
    # g.add((BLDG[identifier], RDF['type'], BRICK[entity_h_tagset]))

    # Determine if it is a point.
    equip_flag = False
    point_flag = False
    if entity_h_tags.intersection(point_h_tags):
        point_flag = True
    else:
        if entity_h_tags.intersection(equip_h_tags):
            equip_flag = True

    # Encode Refs.
    rels = []
    for ref_type, entity in raw_ref_dict:
        if ref_type == 'equip':
            if point_flag:
                rel = 'isPointOf'
            elif equip_flag:
                rel = 'isPartOf' 
                # TODO: This is assumed here. There can be many relationships.
            else:
                continue
        elif ref_type == 'site':
            rel = 'hasLocation'
        g.add((BLDG[identifier], BF[rel], BLDG[entity]))

# Add missing entities from the instantiation




g.serialize('output.ttl', format='turtle')
