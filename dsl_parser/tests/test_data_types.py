from dsl_parser.tests.abstract_test_parser import AbstractTestParser
from dsl_parser import exceptions
from dsl_parser.exceptions import DSLParsingFormatException, DSLParsingLogicException


class TestDataTypes(AbstractTestParser):
    def test_unkown_type(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first:
        type: unknown-type
      second: {}
"""
        self._assert_dsl_parsing_exception_error_code(
            yaml, 1, DSLParsingFormatException)

    def test_simple(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first: {}
      second: {}
"""
        self.parse_1_2(yaml)

    def test_definitions(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first: {}
      second: {}
  pair_of_pairs_type:
    properties:
      first:
        type: pair_type
      second:
        type: pair_type
"""
        self.parse_1_2(yaml)

    def test_infinite_list(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
    list_type:
        properties:
            head:
                type: int
            tail:
                type: list_type
                default:
                    head: 1
"""
        self._assert_dsl_parsing_exception_error_code(
            yaml, exceptions.ERROR_CODE_CYCLE, DSLParsingLogicException)

    def test_definitions_with_default_error(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first: {}
      second: {}
  pair_of_pairs_type:
    properties:
      first:
        type: pair_type
        default:
            first: 1
            second: 2
            third: 4
      second:
        type: pair_type
"""
        self._assert_dsl_parsing_exception_error_code(
            yaml, 106, DSLParsingLogicException)

    def test_unkown_type_in_datatype(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first:
        type: unknown-type
      second: {}
        """
        self._assert_dsl_parsing_exception_error_code(
            yaml, 1, DSLParsingFormatException)
