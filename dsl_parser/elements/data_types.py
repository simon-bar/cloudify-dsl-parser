########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
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

from dsl_parser import constants
from dsl_parser import exceptions
from dsl_parser import utils
from dsl_parser.elements import properties_utils
from dsl_parser.framework.elements import (
    Element,
    Dict,
    DictElement,
    StringElement)
from dsl_parser.framework.parser import parse
from dsl_parser.framework.requirements import Value


_DERIVED_FROM = 'derived_from'
_TYPE = 'type'


class DataType(Element):
    schema = {
        constants.PROPERTIES: properties_utils.UnsafeSchema,
        'description': StringElement,
        _DERIVED_FROM: StringElement,
        'version': StringElement
    }

    def parse(self):
        result = self.build_dict_result()
        if constants.PROPERTIES not in result:
            result[constants.PROPERTIES] = {}
        return result


def _add_requirement_if_exists(current_type,
                               required_type,
                               types_classes,
                               unknown_type_err):
    if required_type not in types_classes:
        raise exceptions.DSLParsingElementMatchException(
            39,
            unknown_type_err)
    types_classes[current_type].requires[
        types_classes[required_type]] = [Value(required_type)]


class DataTypes(Element):
    schema = Dict(type=DataType)

    def parse(self):
        datatypes = self.build_dict_result()

        class DataTypesInternal(DictElement):
            schema = {}

        types_internal = {}
        for type_name, type_schema in datatypes.iteritems():
            if type_name in constants.PRIMITIVE_TYPES:
                raise exceptions.DSLParsingFormatException(
                    1,
                    "Illegal type name '{0}' - it is primitive "
                    "type".format(type_name))

            class DataTypeInternal(DataType):
                requires = {}

                def parse(self, **data_types):
                    schema = self.build_dict_result()
                    schema[constants.PROPERTIES] = utils.parse_type_fields(
                        schema[constants.PROPERTIES],
                        data_types)
                    parent_type = schema.get(_DERIVED_FROM)
                    if parent_type:
                        schema[constants.PROPERTIES] = utils.merge_sub_dicts(
                            overriding_dict=schema,
                            overridden_dict=data_types[parent_type],
                            sub_dict_key=constants.PROPERTIES
                        )
                    return schema

            types_internal[type_name] = DataTypeInternal
            DataTypesInternal.schema[type_name] = DataTypeInternal

        for type_name, type_schema in datatypes.iteritems():
            parent_type = type_schema.get(_DERIVED_FROM)
            if parent_type:
                err_msg = 'Type {0} derives from unknown type {1}'.format(
                    type_name,
                    parent_type)
                _add_requirement_if_exists(type_name,
                                           parent_type,
                                           types_internal,
                                           err_msg)
            for prop_name, prop in type_schema[
                    constants.PROPERTIES].iteritems():
                property_type = prop.get(_TYPE)
                if (property_type
                        and property_type not in constants.PRIMITIVE_TYPES):
                    err_msg = 'Property {0} in type {1} ' \
                              'has unknown type {2}'.format(prop_name,
                                                            type_name,
                                                            property_type)
                    _add_requirement_if_exists(type_name,
                                               property_type,
                                               types_internal,
                                               err_msg)

        return parse(datatypes, DataTypesInternal)
