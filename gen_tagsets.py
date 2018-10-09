import json
from collections import defaultdict
import pdb


def is_in_list(good_items, test_list):
    for row in good_items:
        if row in test_list:
            return True
    return False

def is_useful_line(splitted):
    if is_in_list(['{', '}', 'def', 'use'], splitted)\
            and not is_in_list(['new'], splitted):
        return True
    return False


# Parsing *.phd
with open('haystack-phdef/ph-def-2018-08-10/phIoT/lib/AirPoint.phd', 'r') as fp:
    lines = fp.readlines()

head = defaultdict(dict)
stack = [head]
node_name = None
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
        _, node_name, _, parent = splitted
        stack[-1][node_name] = defaultdict(dict)
    elif 'use' in splitted:
        use = stack[-1][node_name]['use']
        if isinstance(use, list):
            use.append(splitted[1])
        else:
            use = [splitted[1]]
        stack[-1][node_name]['use'] = use

    else:
        assert False

d = dict(stack[0])
with open('test.json', 'w') as fp:
    json.dump(d, fp, indent=2)
pdb.set_trace()

