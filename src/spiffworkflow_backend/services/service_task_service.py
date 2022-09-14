"""ServiceTask_service."""
import json
import requests

from flask import current_app

from typing import Any
from typing import Generator
from typing import Iterable
from typing import TypedDict

from spiffworkflow_backend.services.reflection_service import ParameterDescription
from spiffworkflow_backend.services.reflection_service import ReflectionService
from spiffworkflow_backend.services.secret_service import SecretService


class Operator(TypedDict):
    """Describes an operator and its parameters."""

    id: str
    parameters: Iterable[ParameterDescription]


OperatorClass = Any
OperatorClassGenerator = Generator[tuple[str, OperatorClass], None, None]

class ServiceTaskDelegate:
    @staticmethod
    def callConnector(name: str, bpmn_params: Any):
        def normalizeValue(v: Any):
            value = v['value']
            # TODO replace with call to secret store
            secret_prefix = 'secret:'
            if value.startswith(secret_prefix):
                key = value.removeprefix(secret_prefix)
                value = SecretService.get_secret(key)
            return value

        params = { k: normalizeValue(v) for k, v in bpmn_params.items() }
        # TODO pull host/port from config
        proxied_response = requests.get('http://localhost:7004/v1/do/' + name, params)
        print('From: ' + name)
        print(proxied_response.text)

# TODO: delete lots of stuff here
class ServiceTaskService:
    """ServiceTaskService."""

    @staticmethod
    def _available_airflow_operator_classes() -> OperatorClassGenerator:
        """Yields name and class for all airflow operators available for use in service tasks."""
        # Example code to wire up all installed airflow hooks
        # try:
        #    import airflow.providers
        #    from airflow.hooks.base import BaseHook
        #
        #    yield from ReflectionService.classes_of_type_in_pkg(
        #        airflow.providers, type(BaseHook)
        #    )
        # except:
        #    pass
        yield from []

    @staticmethod
    def _parse_operator_params(
        operator_class: OperatorClass,
    ) -> Iterable[ParameterDescription]:
        """Parses the init of the given operator_class to build a list of OperatorParameters."""
        return ReflectionService.callable_params_desc(operator_class.__init__)

    @classmethod
    def available_operator_classes(cls) -> OperatorClassGenerator:
        """Yields name and class for all operators that are available for use."""
        # TODO maybe premature to have a place to aggregate other operator types?
        yield from cls._available_airflow_operator_classes()

    @classmethod
    def available_operators(cls) -> list[Operator]:
        """Returns a list of all operator names and parameters that are available for use."""

        try:
            # TODO pull url from config
            response = requests.get('http://localhost:7004/v1/commands')
        except Exception as e:
            print(e)
            return []

        if response.status_code != 200:
            return []

        parsed_response = json.loads(response.text)
        return parsed_response

    @classmethod
    def scripting_additions(cls) -> dict[str, OperatorClass]:
        """Returns a dictionary of operator names and classes."""
        #operator_classes = list(cls.available_operator_classes())
        #scripting_additions = {name: clz for name, clz in operator_classes}
        #return scripting_additions
        return { 'ServiceTaskDelegate': ServiceTaskDelegate }