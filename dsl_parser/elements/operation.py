########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

from dsl_parser import (constants,
                        exceptions,
                        utils)
from dsl_parser.elements import (properties,
                                 misc)
from dsl_parser.framework.elements import (DictElement,
                                           Element,
                                           Leaf,
                                           Dict)


class OperationImplementation(Element):

    schema = Leaf(type=str)

    def parse(self):
        return self.initial_value if self.initial_value is not None else ''


class OperationExecutor(Element):

    schema = Leaf(type=str)

    def validate(self):
        if self.initial_value is None:
            return
        value = self.initial_value
        valid_executors = [constants.CENTRAL_DEPLOYMENT_AGENT,
                           constants.HOST_AGENT]
        if value not in valid_executors:
            full_operation_name = '{0}.{1}'.format(
                self.ancestor(Interface).name,
                self.ancestor(Operation).name)
            raise exceptions.DSLParsingLogicException(
                28, "Operation '{0}' has an illegal executor value '{1}'. "
                    "valid values are [{2}]"
                    .format(full_operation_name,
                            value,
                            ','.join(valid_executors)))


class NodeTemplateOperationInputs(Element):

    schema = Leaf(type=dict)

    def parse(self):
        return self.initial_value if self.initial_value is not None else {}


class OperationMaxRetries(Element):

    schema = Leaf(type=int)
    requires = {
        misc.ToscaDefinitionsVersion: ['version']
    }

    def validate(self, version):
        value = self.initial_value
        if value is None:
            return
        if version < (1, 1):
            raise exceptions.DSLParsingLogicException(
                81,
                'operation max_retries '
                'is only supported in dsl versions greater or equal to'
                'cloudify_dsl_1_1')
        if value < -1:
            raise ValueError("'{0}' value must be either -1 to specify "
                             "unlimited retries or a non negative number but "
                             "got {1}."
                             .format(self.name, value))


class OperationRetryInterval(Element):

    schema = Leaf(type=(int, float, long))
    requires = {
        misc.ToscaDefinitionsVersion: ['version']
    }

    def validate(self, version):
        value = self.initial_value
        if value is None:
            return
        if version < (1, 1):
            raise exceptions.DSLParsingLogicException(
                81,
                'operation retry_interval '
                'is only supported in dsl versions greater or equal to'
                'cloudify_dsl_1_1')
        if value is not None and value < 0:
            raise ValueError("'{0}' value must be a non negative number but "
                             "got {1}.".format(self.name, value))


class Operation(Element):

    def parse(self):
        if isinstance(self.initial_value, basestring):
            return {
                'implementation': self.initial_value,
                'executor': None,
                'inputs': {},
                'max_retries': None,
                'retry_interval': None
            }
        else:
            return self.build_dict_result()


class NodeTypeOperation(Operation):

    schema = [
        Leaf(type=str),
        {
            'implementation': OperationImplementation,
            'inputs': properties.Schema,
            'executor': OperationExecutor,
            'max_retries': OperationMaxRetries,
            'retry_interval': OperationRetryInterval,
        }
    ]


class NodeTemplateOperation(Operation):

    schema = [
        Leaf(type=str),
        {
            'implementation': OperationImplementation,
            'inputs': NodeTemplateOperationInputs,
            'executor': OperationExecutor,
            'max_retries': OperationMaxRetries,
            'retry_interval': OperationRetryInterval,
        }
    ]


class Interface(DictElement):
    pass


class NodeTemplateInterface(Interface):

    schema = Dict(type=NodeTemplateOperation)


class NodeTemplateInterfaces(DictElement):

    schema = Dict(type=NodeTemplateInterface)


class NodeTypeInterface(Interface):

    schema = Dict(type=NodeTypeOperation)


class NodeTypeInterfaces(DictElement):

    schema = Dict(type=NodeTypeInterface)


def process_interface_operations(
        interface,
        plugins,
        error_code,
        partial_error_message,
        resource_base):
    return [process_operation(plugins=plugins,
                              operation_name=operation_name,
                              operation_content=operation_content,
                              error_code=error_code,
                              partial_error_message=partial_error_message,
                              resource_base=resource_base)
            for operation_name, operation_content in interface.items()]


def process_operation(
        plugins,
        operation_name,
        operation_content,
        error_code,
        partial_error_message,
        resource_base,
        is_workflows=False):
    payload_field_name = 'parameters' if is_workflows else 'inputs'
    mapping_field_name = 'mapping' if is_workflows else 'implementation'
    operation_mapping = operation_content[mapping_field_name]
    operation_payload = operation_content[payload_field_name]

    # only for node operations
    operation_executor = operation_content.get('executor', None)
    operation_max_retries = operation_content.get('max_retries', None)
    operation_retry_interval = operation_content.get('retry_interval', None)

    if not operation_mapping:
        if is_workflows:
            raise RuntimeError('Illegal state. workflow mapping should always'
                               'be defined (enforced by schema validation)')
        else:
            return _operation(
                name=operation_name,
                plugin_name='',
                operation_mapping='',
                operation_inputs={},
                executor=None,
                max_retries=None,
                retry_interval=None)

    candidate_plugins = [p for p in plugins.keys()
                         if operation_mapping.startswith('{0}.'.format(p))]
    if candidate_plugins:
        if len(candidate_plugins) > 1:
            raise exceptions.DSLParsingLogicException(
                91, 'Ambiguous operation mapping. [operation={0}, '
                    'plugins={1}]'.format(operation_name, candidate_plugins))
        plugin_name = candidate_plugins[0]
        mapping = operation_mapping[len(plugin_name) + 1:]
        if is_workflows:
            return _workflow_operation(
                plugin_name=plugin_name,
                workflow_mapping=mapping,
                workflow_parameters=operation_payload)
        else:
            if not operation_executor:
                operation_executor = plugins[plugin_name]['executor']
            return _operation(
                name=operation_name,
                plugin_name=plugin_name,
                operation_mapping=mapping,
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval)
    elif resource_base and _resource_exists(resource_base, operation_mapping):
        operation_payload = copy.deepcopy(operation_payload or {})
        if constants.SCRIPT_PATH_PROPERTY in operation_payload:
            message = "Cannot define '{0}' property in '{1}' for {2} '{3}'" \
                .format(constants.SCRIPT_PATH_PROPERTY,
                        operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise exceptions.DSLParsingLogicException(60, message)
        script_path = operation_mapping
        if is_workflows:
            operation_mapping = constants.SCRIPT_PLUGIN_EXECUTE_WORKFLOW_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: {
                    'default': script_path,
                    'description': 'Workflow script executed by the script'
                                   ' plugin'
                }
            })
        else:
            operation_mapping = constants.SCRIPT_PLUGIN_RUN_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: script_path
            })
        if constants.SCRIPT_PLUGIN_NAME not in plugins:
            message = "Script plugin is not defined but it is required for" \
                      " mapping '{0}' of {1} '{2}'" \
                .format(operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise exceptions.DSLParsingLogicException(61, message)

        if is_workflows:
            return _workflow_operation(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                workflow_mapping=operation_mapping,
                workflow_parameters=operation_payload)
        else:
            if not operation_executor:
                operation_executor = plugins[constants.SCRIPT_PLUGIN_NAME][
                    'executor']
            return _operation(
                name=operation_name,
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                operation_mapping=operation_mapping,
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval)
    else:
        # This is an error for validation done somewhere down the
        # current stack trace
        base_error_message = (
            "Could not extract plugin from {2} "
            "mapping '{0}', which is declared for {2} '{1}'. "
            .format(operation_mapping,
                    operation_name,
                    'workflow' if is_workflows else 'operation'))
        error_message = base_error_message + partial_error_message
        raise exceptions.DSLParsingLogicException(error_code, error_message)


def _resource_exists(resource_base, resource_name):
    return utils.url_exists('{0}/{1}'.format(resource_base, resource_name))


def _operation(name,
               plugin_name,
               operation_mapping,
               operation_inputs,
               executor,
               max_retries,
               retry_interval):
    return {
        'name': name,
        'plugin': plugin_name,
        'operation': operation_mapping,
        'executor': executor,
        'inputs': operation_inputs,
        'has_intrinsic_functions': False,
        'max_retries': max_retries,
        'retry_interval': retry_interval
    }


def _workflow_operation(plugin_name,
                        workflow_mapping,
                        workflow_parameters):
    return {
        'plugin': plugin_name,
        'operation': workflow_mapping,
        'parameters': workflow_parameters
    }
