from dsl_parser.tests.abstract_test_parser import AbstractTestParser
from dsl_parser import exceptions
from dsl_parser.exceptions import (
    DSLParsingElementMatchException,
    DSLParsingLogicException
)
from dsl_parser.tasks import prepare_deployment_plan


class TestDataTypes(AbstractTestParser):

    def test_unknown_type(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first:
        type: unknown-type
      second: {}
"""
        self._assert_dsl_parsing_exception_error_code(
            yaml, 39, DSLParsingElementMatchException)

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
                type: integer
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

    def test_unknown_type_in_datatype(self):
        yaml = self.MINIMAL_BLUEPRINT + """
data_types:
  pair_type:
    properties:
      first:
        type: unknown-type
      second: {}
        """
        self._assert_dsl_parsing_exception_error_code(
            yaml, 39, DSLParsingElementMatchException)

    def test_nested_validation(self):
        yaml = """
node_templates:
  n_template:
    type: n_type
    properties:
      n_pair:
        second:
          first: 4
          second: invalid_type_value
node_types:
  n_type:
    properties:
      n_pair:
        type: pair_of_pairs_type
data_types:
  pair_type:
    properties:
      first: {}
      second:
        type: integer
  pair_of_pairs_type:
    properties:
      first:
        type: pair_type
        default:
            first: 1
            second: 2
      second:
        type: pair_type
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 50)

    def test_nested_defaults(self):
        yaml = """
node_types:
    vm_type:
        properties:
            agent:
                type: agent
            agent_name:
                type: string
node_templates:
    vm:
        type: vm_type
        properties:
            agent: {}
            agent_name: { get_property: [SELF, agent, connection, username] }
data_types:
    agent_connection:
        properties:
            username:
                type: string
                default: ubuntu
            key:
                type: string
                default: ~/.ssh/id_rsa

    agent:
        properties:
            connection:
                type: agent_connection
                default: {}
            basedir:
                type: string
                default: /home/
"""
        parsed = prepare_deployment_plan(self.parse(yaml))
        vm = self.get_node_by_name(parsed, 'vm')
        self.assertEqual('ubuntu', vm['properties']['agent_name'])

    def test_nested_validation(self):
        yaml = """
node_templates:
  n_template:
    type: n_type
    properties:
      n_pair:
        second:
          first: 4
          second: invalid_type_value
node_types:
  n_type:
    properties:
      n_pair:
        type: pair_of_pairs_type
data_types:
  pair_type:
    properties:
      first: {}
      second:
        type: integer
  pair_of_pairs_type:
    properties:
      first:
        type: pair_type
        default:
            first: 1
            second: 2
      second:
        type: pair_type
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 50)

    def test_derives(self):
        yaml = """
node_types:
    vm_type:
        properties:
            agent:
                type: agent
            agent_name:
                type: string
            agent_key:
                type: string
node_templates:
    vm:
        type: vm_type
        properties:
            agent:
                connection:
                    key: /home/ubuntu/id_rsa
            agent_name: { get_property: [SELF, agent, connection, username] }
            agent_key: { get_property: [SELF, agent, connection, key] }
data_types:
    agent_connection:
        properties:
            username:
                type: string
                default: ubuntu
            key:
                type: string
                default: ~/.ssh/id_rsa
    agent:
        derived_from: agent_installer
        properties:
            basedir:
                type: string
                default: /home/
    agent_installer:
        properties:
            connection:
                type: agent_connection
                default: {}
"""
        parsed = prepare_deployment_plan(self.parse(yaml))
        vm = self.get_node_by_name(parsed, 'vm')
        self.assertEqual('ubuntu', vm['properties']['agent_name'])
        self.assertEqual('/home/ubuntu/id_rsa', vm['properties']['agent_key'])
