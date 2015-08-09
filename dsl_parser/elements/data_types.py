from dsl_parser import constants
from dsl_parser import exceptions

from dsl_parser.elements import properties
from dsl_parser.framework.elements import Element, Dict
from dsl_parser.utils import validate_type_fields


class DataType(Element):
    schema = {
        'properties': properties.Schema
    }

    def parse(self):
        return self.build_dict_result()

class DataTypes(Element):
    schema = Dict(type=DataType)
    provides = ['data_types']

    def parse(self):
        return self.initial_value or {}

    def calculate_provided(self):
        return {
            'data_types': self.value
        }

    def validate(self):
        datatypes = self.initial_value or {}
        for k, v in datatypes.iteritems():
            if k in constants.PRIMITIVE_TYPES:
                raise exceptions.DSLParsingFormatException(
                1,
                "Illegal type name '{0}' - it is primitive type".format(k))
            validate_type_fields(v, self.initial_value)


