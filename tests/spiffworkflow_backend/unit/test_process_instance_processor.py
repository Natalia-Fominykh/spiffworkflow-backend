"""Test_process_instance_processor."""
import pytest
from flask.app import Flask
from tests.spiffworkflow_backend.helpers.base_test import BaseTest
from tests.spiffworkflow_backend.helpers.test_data import load_test_spec

from spiffworkflow_backend.models.group import GroupModel
from spiffworkflow_backend.models.process_instance import ProcessInstanceStatus
from spiffworkflow_backend.services.authorization_service import AuthorizationService
from spiffworkflow_backend.services.authorization_service import (
    UserDoesNotHaveAccessToTaskError,
)
from spiffworkflow_backend.services.process_instance_processor import (
    ProcessInstanceProcessor,
)
from spiffworkflow_backend.services.process_instance_service import (
    ProcessInstanceService,
)


class TestProcessInstanceProcessor(BaseTest):
    """TestProcessInstanceProcessor."""

    # it's not totally obvious we want to keep this test/file
    def test_script_engine_takes_data_and_returns_expected_results(
        self,
        app: Flask,
        with_db_and_bpmn_file_cleanup: None,
    ) -> None:
        """Test_script_engine_takes_data_and_returns_expected_results."""
        script_engine = ProcessInstanceProcessor._script_engine

        result = script_engine._evaluate("a", {"a": 1})
        assert result == 1

    def test_script_engine_can_use_custom_scripts(
        self,
        app: Flask,
        with_db_and_bpmn_file_cleanup: None,
    ) -> None:
        """Test_script_engine_takes_data_and_returns_expected_results."""
        script_engine = ProcessInstanceProcessor._script_engine
        result = script_engine._evaluate("fact_service(type='norris')", {})
        assert (
            result
            == "Chuck Norris doesn’t read books. He stares them down until he gets the information he wants."
        )

    def test_sets_permission_correctly_on_active_task(
        self,
        app: Flask,
        with_db_and_bpmn_file_cleanup: None,
    ) -> None:
        """Test_sets_permission_correctly_on_active_task."""
        initiator_user = self.find_or_create_user("initiator_user")
        finance_user = self.find_or_create_user("testuser2")
        assert initiator_user.principal is not None
        assert finance_user.principal is not None
        AuthorizationService.import_permissions_from_yaml_file()

        finance_group = GroupModel.query.filter_by(identifier="Finance Team").first()
        assert finance_group is not None

        process_model = load_test_spec(
            process_model_id="model_with_lanes", bpmn_file_name="lanes.bpmn"
        )
        process_instance = self.create_process_instance_from_process_model(
            process_model=process_model, user=initiator_user
        )
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)

        assert len(process_instance.active_tasks) == 1
        active_task = process_instance.active_tasks[0]
        assert active_task.lane_assignment_id is None
        assert len(active_task.potential_owners) == 1
        assert active_task.potential_owners[0] == initiator_user

        spiff_task = processor.__class__.get_task_by_bpmn_identifier(
            active_task.task_name, processor.bpmn_process_instance
        )
        with pytest.raises(UserDoesNotHaveAccessToTaskError):
            ProcessInstanceService.complete_form_task(
                processor, spiff_task, {}, finance_user
            )
        ProcessInstanceService.complete_form_task(
            processor, spiff_task, {}, initiator_user
        )

        assert len(process_instance.active_tasks) == 1
        active_task = process_instance.active_tasks[0]
        assert active_task.lane_assignment_id == finance_group.id
        assert len(active_task.potential_owners) == 1
        assert active_task.potential_owners[0] == finance_user

        spiff_task = processor.__class__.get_task_by_bpmn_identifier(
            active_task.task_name, processor.bpmn_process_instance
        )
        with pytest.raises(UserDoesNotHaveAccessToTaskError):
            ProcessInstanceService.complete_form_task(
                processor, spiff_task, {}, initiator_user
            )

        ProcessInstanceService.complete_form_task(
            processor, spiff_task, {}, finance_user
        )
        assert len(process_instance.active_tasks) == 1
        active_task = process_instance.active_tasks[0]
        assert active_task.lane_assignment_id is None
        assert len(active_task.potential_owners) == 1
        assert active_task.potential_owners[0] == initiator_user

        spiff_task = processor.__class__.get_task_by_bpmn_identifier(
            active_task.task_name, processor.bpmn_process_instance
        )
        ProcessInstanceService.complete_form_task(
            processor, spiff_task, {}, initiator_user
        )

        assert process_instance.status == ProcessInstanceStatus.complete.value
