import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import time

import cerberus

import schema

OSM_PATH = "toronto_map.osm"

NODES_PATH = "csv/nodes.csv"
NODE_TAGS_PATH = "csv/nodes_tags.csv"
WAYS_PATH = "csv/ways.csv"
WAY_NODES_PATH = "csv/ways_nodes.csv"
WAY_TAGS_PATH = "csv/ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

def convert_fields(base_dict):
    """
    Returns dictionary with the same keys and converted values

    <base_dict> : basic {key:value} dict containing only keys that are present in field_map

    """

    field_map={'id':'int', 'lat':'float', 'lon':'float', 'user':'str',
            'uid':'int', 'version':'int', 'changeset':'int', 'timestamp':'str',
            'key':'str','value':'str','type':'str','node_id':'int','position':'int'}
    converted={}
    for k,v in base_dict.items():
        if field_map[k]=='str':
            converted[k]=str(v)
        elif field_map[k]=='int':
            converted[k]=int(v)
        elif field_map[k]=='float':
            converted[k]=float(v)
        # if isinstance(v, str)
    return converted

def parse_tags(id,tags,problem_chars=PROBLEMCHARS):
    """
    Returns a list of tag dicts with the keys: id,key,value,type
    Searches for problematic characters in the tag key. If present, tag is not returned.

    <id> integer id of the node/way
    <tags> list of tags
    <problem_chars> regular expression with problem characters to search for
    """
    tags_list=[]

    for tag in tags:
        tag_type=tag.attrib.get('k','regular')
        m = problem_chars.search(tag_type)
        if m: ##if there are problem tags..
            continue
        else:
            split_tag=tag_type.split(':')
            if len(split_tag)==1:
                tag_type='regular'
                key=tag.attrib.get('k',None)
            else:
                tag_type=split_tag[0]
                key=':'.join(split_tag[1:])

            tag_dict=convert_fields({'id':id,'key':key,'value':tag.attrib.get('v',None),'type':tag_type})
            tags_list.append(tag_dict)

    return tags_list

def parse_way_nodes(id,nodes):
    """
    Returns a list of node dicts with the keys [id,node_id,position]
    <id> integer id of the way
    <nodes> list of nodes
    """
    nodes_list=[]

    for i,nd in enumerate(nodes): ##i represents the nodes order
        base_dict={'id':id,'node_id':nd.attrib.get('ref',None),'position':i}
        nodes_list.append(convert_fields(base_dict))

    return nodes_list

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    if element.tag == 'node':
        base_dict={k:element.attrib.get(k,None) for k in node_attr_fields}
        node_attribs=convert_fields(base_dict)
        tags=parse_tags(int(element.attrib.get('id',None)),element.findall('./tag'))
        return {'node': node_attribs, 'node_tags': tags}

    elif element.tag == 'way':
        base_dict={k:element.attrib.get(k,None) for k in way_attr_fields}
        way_attribs=convert_fields(base_dict)
        tags=parse_tags(element.attrib.get('id',None),element.findall('./tag'))
        way_nodes=parse_way_nodes(element.attrib.get('id',None),element.findall('./nd'))
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.items())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        # super(UnicodeDictWriter, self).writerow({
        #     k: (v.encode('utf-8') if isinstance(v, str) else v) for k, v in row.items()
        # })
        super(UnicodeDictWriter, self).writerow({k: v for k, v in row.items()})
    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        # nodes_writer.writeheader()
        # node_tags_writer.writeheader()
        # ways_writer.writeheader()
        # way_nodes_writer.writeheader()
        # way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=False)
