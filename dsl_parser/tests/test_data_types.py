from dsl_parser.tests.abstract_test_parser import AbstractTestParser
from dsl_parser.exceptions import DSLParsingFormatException

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

    def test_definitions(self):
        yaml = self.MINIMAL_BLUEPRINT +  """
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