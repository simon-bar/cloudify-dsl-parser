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
import copy

from dsl_parser import constants
from dsl_parser import elements
from dsl_parser import exceptions
from dsl_parser import utils
from dsl_parser.elements import types
from dsl_parser.framework.elements import (
    Element,
    Dict,
    DictElement,
    Leaf,
    StringElement)
from dsl_parser.framework.requirements import (
    Value,
    Requirement,
    sibling_predicate)


class SchemaPropertyDescription(Element):

    schema = Leaf(type=str)


class SchemaPropertyType(Element):

    schema = Leaf(type=str)

    # requires will be modified later.
    requires = {}
    provides = ['component_types']

    def validate(self, data_type, component_types):
        if self.initial_value and self.initial_value not in \
                constants.USER_PRIMITIVE_TYPES and not data_type:
            raise exceptions.DSLParsingLogicException(
                exceptions.ERROR_UNKNOWN_TYPE,
                "Illegal type name '{0}'".format(self.initial_value))

    def calculate_provided(self, data_type, component_types):
        component_types = component_types or {}
        if self.value and self.value not in constants.USER_PRIMITIVE_TYPES:
            component_types = copy.copy(component_types)
            component_types[self.value] = data_type
        return {'component_types': component_types}


class SchemaPropertyDefault(Element):
    schema = Leaf(type=elements.PRIMITIVE_TYPES)
    requires = {
        SchemaPropertyType: [
            Value('type_name', required=False, predicate=sibling_predicate),
            Requirement('component_types',
                        required=False,
                        predicate=sibling_predicate)
        ]
    }

    def parse(self, type_name, component_types):
        if self.initial_value is None:
            return
        component_types = component_types or {}
        prop_name = self.ancestor(SchemaProperty).name
        undefined_property_error = 'Undefined property {1} in default' \
                                   ' value of type {0}'
        missing_property_error = 'Property {1} is missing in default' \
                                 ' value of type {0}'
        current_type = self.ancestor(Schema).parent().name
        print str(self.initial_value)
        return utils.parse_value(
            self.initial_value,
            type_name,
            prop_name,
            component_types,
            undefined_property_error_message=undefined_property_error,
            missing_property_error_message=missing_property_error,
            node_name=current_type,
            path=[]
        )


class SchemaProperty(Element):

    schema = {
        'default': SchemaPropertyDefault,
        'description': SchemaPropertyDescription,
        'type': SchemaPropertyType,
    }

    def parse(self):
        result = self.build_dict_result()
        return dict((k, v) for k, v in result.iteritems() if v is not None)


class Schema(DictElement):

    schema = Dict(type=SchemaProperty)


class DataType(types.Type):

    schema = {
        constants.PROPERTIES: Schema,
        'description': StringElement,
        constants.DERIVED_FROM: types.DerivedFrom,
        'version': StringElement
    }

    requires = {
        'self': [
            Requirement('component_types',
                        multiple_results=True,
                        required=False,
                        predicate=lambda source, target:
                            target.name in source.direct_component_types),
            Value('super_type',
                  predicate=types.derived_from_predicate,
                  required=False)
        ]
    }

    provides = ['component_types']

    def __init__(self, *args, **kwargs):
        super(DataType, self).__init__(*args, **kwargs)
        self._direct_component_types = None
        self.component_types = {}

    def parse(self, super_type, component_types):
        for component in component_types:
            self.component_types.update(component)
        result = self.build_dict_result()
        if constants.PROPERTIES not in result:
            result[constants.PROPERTIES] = {}
        if super_type:
            result[constants.PROPERTIES] = utils.merge_sub_dicts(
                overridden_dict=super_type,
                overriding_dict=result,
                sub_dict_key=constants.PROPERTIES
            )
        self.component_types[self.name] = result
        return result

    def calculate_provided(self, **kwargs):
        return {'component_types': self.component_types}

    @property
    def direct_component_types(self):
        if self._direct_component_types is None:
            direct_component_types = set()
            parent_type = self.initial_value.get(constants.DERIVED_FROM)
            if parent_type:
                direct_component_types.add(parent_type)
            for desc in self.descendants(SchemaPropertyType):
                direct_component_types.add(desc.initial_value)
            self._direct_component_types = direct_component_types
        return self._direct_component_types


class DataTypes(types.Types):
    schema = Dict(type=DataType)


# source: element describing data_type name
# target: data_type
def _has_type(source, target):
    return source.initial_value == target.name


SchemaPropertyType.requires[DataType] = [
    Value('data_type', predicate=_has_type, required=False),
    Requirement('component_types', predicate=_has_type, required=False)
]
