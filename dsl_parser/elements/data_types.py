from dsl_parser import constants
from dsl_parser import exceptions
from dsl_parser import utils
from dsl_parser.elements import properties_utils
from dsl_parser.framework.elements import Element, Dict
from dsl_parser.framework.parser import parse
from dsl_parser.framework.requirements import Value


class DataType(Element):
    schema = {
        'properties': properties_utils.UnsafeSchema
    }

    def parse(self):
        result = self.build_dict_result()
        if 'properties' not in result:
            result['properties'] = {}
        return result


class DataTypes(Element):
    schema = Dict(type=DataType)
    provides = ['data_types']

    def parse(self):
        datatypes = self.build_dict_result()

        class DataTypesInternal(Element):
            schema = {}
            requires = {}

        types_internal = {}
        for type_name, type_schema in datatypes.iteritems():
            if type_name in constants.PRIMITIVE_TYPES:
                raise exceptions.DSLParsingFormatException(
                    1,
                    "Illegal type name '{0}' - it is primitive "
                    "type".format(type_name))

            class DataTypeInternal(Element):
                schema = {
                    'properties': properties_utils.UnsafeSchema
                }
                requires = {}

                def parse(self, **data_types):
                    return {
                        'properties': utils.parse_type_fields(
                            self.build_dict_result()['properties'],
                            data_types)
                    }

            types_internal[type_name] = DataTypeInternal
            DataTypesInternal.schema[type_name] = DataTypeInternal

        for type_name, type_schema in datatypes.iteritems():
            for prop_name, prop in type_schema['properties'].iteritems():
                if 'type' in prop and prop['type'] in types_internal:
                    prop_type = prop['type']
                    types_internal[type_name].requires[
                        types_internal[prop_type]] = [Value(prop_type)]

        return parse(datatypes, DataTypesInternal)
