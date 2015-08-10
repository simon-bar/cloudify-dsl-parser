########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import copy
import contextlib
import urllib2

import yaml.parser

from dsl_parser import yaml_loader
from dsl_parser import functions
from dsl_parser import constants
from dsl_parser.exceptions import (DSLParsingLogicException,
                                   DSLParsingFormatException)


def merge_sub_dicts(overridden_dict, overriding_dict, sub_dict_key):
    overridden_sub_dict = overridden_dict.get(sub_dict_key, {})
    overriding_sub_dict = overriding_dict.get(sub_dict_key, {})
    return dict(overridden_sub_dict.items() + overriding_sub_dict.items())


def flatten_schema(schema):
    flattened_schema_props = {}
    for prop_key, prop in schema.iteritems():
        if 'default' in prop:
            flattened_schema_props[prop_key] = prop['default']
        else:
            flattened_schema_props[prop_key] = None
    return flattened_schema_props


def merge_schema_and_instance_properties(
        instance_properties,
        schema_properties,
        data_types,
        undefined_property_error_message,
        missing_property_error_message,
        node_name):
    flattened_schema_props = flatten_schema(schema_properties)

    # validate instance properties don't
    # contain properties that are not defined
    # in the schema.

    for key in instance_properties.iterkeys():
        if key not in flattened_schema_props:
            ex = DSLParsingLogicException(
                106,
                undefined_property_error_message.format(node_name, key))
            ex.property = key
            raise ex

    merged_properties = dict(flattened_schema_props.items() +
                             instance_properties.items())
    result = {}
    for key, value in merged_properties.iteritems():
        if value is None:
            ex = DSLParsingLogicException(
                107,
                missing_property_error_message.format(node_name, key))
            ex.property = key
            raise ex
        result[key] = _parse_value(
            value,
            schema_properties.get(key).get('type'),
            key,
            data_types,
            undefined_property_error_message=\
                undefined_property_error_message,
            missing_property_error_message=\
                missing_property_error_message,
            node_name=node_name)

    return result


def _parse_value(
        value,
        type_name,
        property_name,
        data_types,
        undefined_property_error_message,
        missing_property_error_message,
        node_name):
    if type_name is None:
        return value
    if functions.parse(value) != value:
        # intrinsic function - not validated at the moment
        return value
    if type_name == 'integer':
        if isinstance(value, (int, long)) and not isinstance(
                value, bool):
            return value
    elif type_name == 'float':
        if isinstance(value, (int, float, long)) and not isinstance(
                value, bool):
            return value
    elif type_name == 'boolean':
        if isinstance(value, bool):
            return value
    elif type_name == 'string':
        return value
    elif type_name in data_types:
        if isinstance(value, dict):
            data_schema = data_types[type_name]
            return merge_schema_and_instance_properties(
                value,
                data_schema,
                data_types=data_types,
                undefined_property_error_message=\
                    undefined_property_error_message,
                missing_property_error_message=\
                    missing_property_error_message,
                node_name=node_name)
    else:
        raise RuntimeError(
            "Unexpected type defined in property schema for property '{0}'"
            " - unknown type is '{1}'".format(property_name, type_name))

    raise DSLParsingLogicException(
        50, "Property type validation failed: Property '{0}' type "
            "is '{1}', yet it was assigned with the value '{2}'"
            .format(property_name, type_name, value))


def parse_type_fields(fields, data_types):
    result = {}
    for property_name, property_schema in fields.iteritems():
        type_name = property_schema.get('type')
        if type_name is not None and (type_name not in data_types and
                 type_name not in constants.PRIMITIVE_TYPES):
            raise DSLParsingFormatException(
                1,
                "Illegal type name '{0}'".format(type_name))
        val_clone = copy.deepcopy(property_schema)
        default_value = property_schema.get('default')
        if default_value:
            undefined_property_error = 'Undefined property in default' \
                                       ' value of type {}: {}'
            missing_property_error = 'Property is missing in default' \
                                     ' value of type {}: {}'
            default_value = _parse_value(
                default_value,
                type_name,
                property_name,
                data_types=data_types,
                undefined_property_error_message=undefined_property_error,
                missing_property_error_message=missing_property_error,
                node_name=type_name)
            val_clone['default'] = default_value
        result[property_name] = val_clone
    return result


def load_yaml(raw_yaml, error_message, filename=None):
    try:
        return yaml_loader.load(raw_yaml, filename)
    except yaml.parser.ParserError, ex:
        raise DSLParsingFormatException(-1, '{0}: Illegal yaml; {1}'
                                        .format(error_message, ex))


def url_exists(url):
    try:
        with contextlib.closing(urllib2.urlopen(url)):
            return True
    except urllib2.URLError:
        return False
