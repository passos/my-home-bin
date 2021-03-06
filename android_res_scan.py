#!/usr/bin/env python
# -*- coding: utf-8 -*-  

import sys
import os
import os.path
from optparse import OptionParser
import json
import lxml.etree

ANDROID_XML_NAMESPACE='{http://schemas.android.com/apk/res/android}'

def to_json(dicts, properties=None):
    return json.dumps(dicts, ensure_ascii=False)

def from_json(json_str, properties=None):
    return json.loads(json_str)

def pretty_json(dicts, properties=None):
    return json.dumps(dicts, ensure_ascii=False, sort_keys=True, indent=4)



# class for scan/parse/compress Android resource files
class AndroidResources:

    def __init__(self, root):
        self.root = root
        self.maps = {'dimens': {}, 'colors': {}, 'strings': {}, 'attrs': {}, 'vals': {}, 'files': {}}

    def get_res_map(self):
        return self.maps

    # parse all xml files under root dir
    def parse(self):
        self.__find(self.__parse_xml)

        # sort the result
        for dicts in [self.maps['strings'], self.maps['colors'], self.maps['dimens']]:
            for k, v in dicts.items():
                dicts[k].sort()

    # find for all files with ext name under root_dir and apply callback method for
    # each of them
    def __find(self, callback):
        for dirpath, dirname, files in os.walk(self.root, followlinks=True):
            for filename in files:
                basename, extname = os.path.splitext(filename)
                if (extname == '.xml'):
                    fullname = os.sep.join((dirpath, filename))
                    callback(fullname)

    # parse an Android xml file, extract interested data
    def __parse_xml(self, fullname):
        with open(fullname, 'r') as fh:
            xml = fh.read()
        dom = lxml.etree.fromstring(xml)

        filename = fullname.split('/res/')[-1]
        self.maps['files'][filename] = self.__process(filename, dom)

    def __process(self, filename, elem):
        # handle the element like <string name="xxx'>value</string>
        # this is where the real value be placed
        if elem.tag == 'string':
            self.__save_element_content(filename, elem, self.maps['strings'])
            return
        elif elem.tag == 'color':
            self.__save_element_content(filename, elem, self.maps['colors'])
            return
        elif elem.tag == 'dimen':
            self.__save_element_content(filename, elem, self.maps['dimens'])
            return

        # handle the element like 
        # <View android:layout_width="xxx" android:layout_height="xxx" />
        # the value could be real value or variable
        node = {}
        for attr_name, attr_value in elem.attrib.items():
            # only handle attribute like android:xxx 
            if not attr_name.startswith(ANDROID_XML_NAMESPACE):
                continue
            attr_name = attr_name.replace(ANDROID_XML_NAMESPACE, '').strip()
            attr_value = attr_value.strip()

            # only take care the variable style value
            if attr_value.startswith('@'):
                node[attr_name] = attr_value
                self.__save_element_attribute(attr_name, attr_value)

        # visit all element for collecting wanted attribute name and value
        for e in elem:
            child_node = self.__process(filename, e)
            if (child_node is not None and len(child_node) > 0):
                child_node['_element'] = e.tag
                if '_items' not in node:
                    node['_items'] = []
                node['_items'].append(child_node)

        return node

    def __save_element_content(self, filename, elem, dicts):
        if 'name' not in elem.attrib:
            return

        # skip SherlockActionBar attributes
        name = elem.attrib['name'].strip()
        if name.startswith('abs__'):
            return

        # polish value
        value = elem.text.strip() if elem.text is not None else ''
        value = value.replace('dp', 'dip')
        #value = value.encode('utf-8')

        if value not in dicts:
            dicts[value] = []

        item = {'name': name, 'value': value, 'file': filename}
        dicts[value].append(item)

    def __save_element_attribute(self, name, value):
        if name not in self.maps['attrs']:
            self.maps['attrs'][name] = []
        self.maps['attrs'][name].append(value)

        if value not in self.maps['vals']:
            self.maps['vals'][value] = []
        self.maps['vals'][value].append(name)


############################################################
# 
############################################################

def validate(res):
    pass


def dump_variable_map(res):
    for filename, struct in res.maps['files'].items():
        if '_items' in struct:
            __dump_variable_map(filename, struct['_items'])


def __dump_variable_map(prefix, items):
    for item in items:
        # dump element attributes
        for k, v in item.items():
            if k.startswith("_"):
                continue
            print ':'.join((prefix, item['_element'], k)), '=', v

        # dump child elements
        if '_items' in v:
            __dump_variable_map(':'.join(prefix, item['_element']), v['_items'])
    


############################################################
#  main entry
############################################################
if __name__=="__main__":
    usage = "usage: %prog [options] DIR"
    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--dump", dest="dump_type", metavar="string|color|dimen|map",
            help="scan and dump result")
    parser.add_option("-v", "--validate", dest="validate", action="store_true", 
            default=False, help="validate values variables")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        sys.exit(0)

    if options.dump_type and options.dump_type not in ['string', 'color', 'dimen', 'map', 'map-raw', 'attr', 'value']:
        parser.print_help()
        sys.exit(0)

    root_dir = os.path.abspath(args[0])
    for sub_dir in ['values', 'layout', 'color', 'drawable']:
        if not os.path.exists(os.sep.join((root_dir, sub_dir))):
            sys.stderr.write("ERROR: %s is not an Android resource directory\n\n" % root_dir)
            parser.print_help()
            sys.exit(0)

    android_res = AndroidResources(root_dir)
    android_res.parse()

    if options.dump_type:
        if options.dump_type == 'string':
            print pretty_json(android_res.maps['strings'])
        elif (options.dump_type == 'color'):
            print pretty_json(android_res.maps['colors'])
        elif (options.dump_type == 'dimen'):
            print pretty_json(android_res.maps['dimens'])
        elif (options.dump_type == 'attr'):
            print pretty_json(android_res.maps['attrs'])
        elif (options.dump_type == 'value'):
            print pretty_json(android_res.maps['vals'])
        elif (options.dump_type == 'map_raw'):
            print pretty_json(android_res.maps['files'])
        elif (options.dump_type == 'map'):
            dump_variable_map(android_res)

    elif options.validate:
        validate(android_res)

