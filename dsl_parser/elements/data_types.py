from dsl_parser import constants
from dsl_parser import exceptions
from dsl_parser import utils
from dsl_parser.elements import properties_utils
from dsl_parser.framework.elements import Element, Dict, Leaf, DictElement
from dsl_parser.framework.parser import parse
from dsl_parser.framework.requirements import Value


_DERIVED_FROM = 'derived_from'


class StringElement(Element):
    schema = Leaf(type=str)


class DataType(Element):
    schema = {
        'properties': properties_utils.UnsafeSchema,
        'description': StringElement,
        _DERIVED_FROM: StringElement,
        'version': StringElement
    }

    def parse(self):
        result = self.build_dict_result()
        if 'properties' not in result:
            result['properties'] = {}
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
    provides = ['data_types']

    def parse(self):
        datatypes = self.build_dict_result()

        class DataTypesInternal(DictElement):
            schema = {}
            requires = {}

        types_internal = {}
        for type_name, type_schema in datatypes.iteritems():
            if type_name in constants.PRIMITIVE_TYPES:
                raise exceptions.DSLParsingFormatException(
                    1,
                    "Illegal type name '{0}' - it is primitive "
                    "type".format(type_name))

            class DataTypeInternal(DataType):
                requires = {}
                _type_name = type_name

                def parse(self, **data_types):
                    schema = self.build_dict_result()
                    schema['properties'] = utils.parse_type_fields(
                        schema['properties'],
                        data_types)
                    parent_type = schema.get(_DERIVED_FROM)
                    if parent_type:
                        schema['properties'] = utils.merge_sub_dicts(
                            overriding_dict=schema,
                            overridden_dict=data_types[parent_type],
                            sub_dict_key='properties'
                        )
                    return schema

            types_internal[type_name] = DataTypeInternal
            DataTypesInternal.schema[type_name] = DataTypeInternal

        for type_name, type_schema in datatypes.iteritems():
            if type_schema.get(_DERIVED_FROM):
                err_msg = 'Type {0} derives from unknown type {1}'.format(
                    type_name,
                    type_schema[_DERIVED_FROM])
                _add_requirement_if_exists(type_name,
                                           type_schema['derived_from'],
                                           types_internal,
                                           err_msg)
            for prop_name, prop in type_schema['properties'].iteritems():
                if 'type' in prop and \
                                prop['type'] not in constants.PRIMITIVE_TYPES:
                    err_msg = 'Property {0} in type {1} ' \
                              'has unkown type {2}'.format(prop_name,
                                                           type_name,
                                                           prop['type'])
                    _add_requirement_if_exists(type_name,
                                               prop['type'],
                                               types_internal,
                                               err_msg)

        return parse(datatypes, DataTypesInternal)
