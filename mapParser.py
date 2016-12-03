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
STREET_TYPE_RE = re.compile(r'\b\S+\.?$', re.IGNORECASE)

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

EXPECTED_STREETS = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons","Crescent","Close","East","West","North","South","Way","Terrace"]

STREET_NAME_MAP = { "St": "Street",
                    "St.": "Street",
                    "Blvd": "Boulevard",
                    "Ave": "Avenue",
                    "Ave.": "Avenue",
                    "Rd": "Road",
                    "STREET": "Street",
                    "avenue": "Avenue",
                    "street": "Street",
                    "E": "East",
                    "W": "West"
                    }

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

def is_postal_code(tag_dict):
    return (tag_dict['key'] == 'postcode')

def is_street_name(tag_dict):
    return (tag_dict['key'] == 'street')

def clean_postal(postal_code):
    char_type = {1:0,2:1,3:0,4:1,5:0,6:1} ##1 if integer, 0 if alphabetical

    postal_code = "".join(postal_code.split()) ##remove all spaces
    postal_code = postal_code.upper() ##convert to upper case

    if len(postal_code)==6:
        pass
    else:
        return

    for i,s in enumerate(postal_code):
        check = (1 if s.isdigit() else 0)
        if check == char_type[i+1]:
            continue
        else:
            return
    return postal_code

def clean_street(street_name,expected=EXPECTED_STREETS,street_type_re=STREET_TYPE_RE):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            return update_street_name(street_name)
        else:
            return street_name

    return street_name

def update_street_name(street_name,street_name_mapping=STREET_NAME_MAP):
    street_words = street_name.split()

    updated_street_words=[]
    for w in street_words:
        try:
            w = street_name_mapping[w]
        except:
            pass
        updated_street_words.append(w)

    return " ".join(updated_street_words)


def clean_tag_dict(tag_dict):
    if is_postal_code(tag_dict):
        postal_code=clean_postal(tag_dict['value'])
        if postal_code:
            tag_dict['value']= postal_code ##update postal code in tag_dict
        else:
            return False
    if is_street_name(tag_dict):
        street_name=clean_street(tag_dict['value'])
        if street_name:
            tag_dict['value'] = street_name ##update street name in tag_dict
        else:
            return False
    return tag_dict

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
            cleaned_tag_dict=clean_tag_dict(tag_dict)
            if cleaned_tag_dict:
                tags_list.append(tag_dict)
            else: ##if the tag_dict has a bad postal code or street name, don't add it
                continue

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
