"""Message_service."""
from typing import Optional

import flask
from flask import g
from flask_bpmn.models.db import db
from SpiffWorkflow.bpmn.specs.events.event_definitions import MessageEventDefinition  # type: ignore
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import select

from spiffworkflow_backend.models.message_correlation import MessageCorrelationModel
from spiffworkflow_backend.models.message_instance import MessageInstanceModel
from spiffworkflow_backend.models.message_triggerable_process_model import (
    MessageTriggerableProcessModel,
)
from spiffworkflow_backend.models.process_instance import ProcessInstanceModel
from spiffworkflow_backend.services.process_instance_processor import (
    ProcessInstanceProcessor,
)
from spiffworkflow_backend.services.process_instance_service import ProcessInstanceService


class MessageServiceWithAppContext:
    """Wrapper for Message Service.

    This wrappers is to facilitate running the MessageService from the scheduler
    since we need to specify the app context then.
    """

    def __init__(self, app: flask.app.Flask):
        """__init__."""
        self.app = app

    def process_message_instances_with_app_context(self) -> None:
        """Since this runs in a scheduler, we need to specify the app context as well."""
        with self.app.app_context():
            MessageService().process_message_instances()


class MessageServiceError(Exception):
    """MessageServiceError."""


class MessageService:
    """MessageService."""

    def process_message_instances(self) -> None:
        """Process_message_instances."""
        message_instances_send = MessageInstanceModel.query.filter_by(
            message_type="send", status="ready"
        ).all()
        message_instances_receive = MessageInstanceModel.query.filter_by(
            message_type="receive"
        ).all()
        for message_instance_send in message_instances_send:
            # check again in case another background process picked up the message
            # while the previous one was running
            if message_instance_send.status != "ready":
                continue

            message_instance_send.status = "running"
            db.session.add(message_instance_send)
            db.session.commit()

            message_instance_receive = None
            try:
                message_instance_receive = self.get_message_instance_receive(
                    message_instance_send, message_instances_receive
                )
                if message_instance_receive is None:

                    message_triggerable_process_model = (
                        MessageTriggerableProcessModel.query.filter_by(
                            message_model_id=message_instance_send.message_model_id
                        )
                    )
                    if message_triggerable_process_model:
                        process_instance = (
                            ProcessInstanceService.create_process_instance(
                                message_triggerable_process_model.process_model_identifier,
                                g.user,
                                process_group_identifier=message_triggerable_process_model.process_group_identifier,
                            )
                        )
                        processor = ProcessInstanceProcessor(process_instance)
                        processor.do_engine_steps()

                if message_instance_receive:
                    self.process_message_receive(
                        message_instance_send, message_instance_receive
                    )
                    message_instance_receive.status = "completed"
                    db.session.add(message_instance_receive)
                    message_instance_send.status = "completed"
                else:
                    # if we can't get a queued message then put it back in the queue
                    message_instance_send.status = "ready"

                db.session.add(message_instance_send)
                db.session.commit()
            except Exception as exception:
                message_instance_send.status = "failed"
                message_instance_send.failure_cause = str(exception)
                db.session.add(message_instance_send)

                if message_instance_receive:
                    message_instance_receive.status = "failed"
                    message_instance_receive.failure_cause = str(exception)
                    db.session.add(message_instance_receive)

                db.session.commit()
                raise exception

    def process_message_receive(
        self,
        message_instance_send: MessageInstanceModel,
        message_instance_receive: MessageInstanceModel,
    ) -> None:
        """Process_message_receive."""
        process_instance_send = self.get_process_instance_for_message_instance(
            message_instance_send
        )
        processor_send = ProcessInstanceProcessor(process_instance_send)
        spiff_task_send = processor_send.get_task_by_id(
            message_instance_send.bpmn_element_identifier
        )
        print(
            f"message_instance_send.bpmn_element_identifier: {message_instance_send.bpmn_element_identifier}"
        )
        if spiff_task_send is None:
            raise MessageServiceError(
                "Processor failed to obtain task.",
            )

        # message_event_send = MessageEventDefinition(
        #     spiff_task_send.id, payload=spiff_task_send.payload
        # )

        process_instance_receive = ProcessInstanceModel.query.filter_by(
            id=message_instance_receive.process_instance_id
        ).first()
        if process_instance_receive is None:
            raise MessageServiceError(
                (
                    f"Process instance cannot be found for queued message: {message_instance_receive.id}."
                    f"Tried with id {message_instance_receive.process_instance_id}",
                )
            )

        processor_receive = ProcessInstanceProcessor(process_instance_receive)
        import pdb

        pdb.set_trace()
        processor_receive.bpmn_process_instance.catch_bpmn_message(
            spiff_task_send.id, spiff_task_send.payload
        )

    def get_message_instance_receive(
        self,
        message_instance_send: MessageInstanceModel,
        message_instances_receive: list[MessageInstanceModel],
    ) -> Optional[MessageInstanceModel]:
        """Get_message_instance_receive."""
        message_correlations_send = MessageCorrelationModel.query.filter_by(
            message_instance_id=message_instance_send.id
        ).all()
        message_correlation_filter = []
        for message_correlation_send in message_correlations_send:
            message_correlation_filter.append(
                and_(
                    MessageCorrelationModel.name == message_correlation_send.name,
                    MessageCorrelationModel.value == message_correlation_send.value,
                )
            )

        for message_instance_receive in message_instances_receive:

            # sqlalchemy supports select / where statements like active record apparantly
            # https://docs.sqlalchemy.org/en/14/core/tutorial.html#conjunctions
            message_correlation_select = (
                select([db.func.count()])
                .select_from(MessageCorrelationModel)  # type: ignore
                .where(
                    and_(
                        MessageCorrelationModel.message_instance_id
                        == message_instance_receive.id,
                        or_(*message_correlation_filter),
                    )
                )
            )
            message_correlations_receive = db.session.execute(
                message_correlation_select
            )

            # since the query matches on name, value, and message_instance_receive.id, if the counts
            # message correlations found are the same, then this should be the relevant message
            if message_correlations_receive.scalar() == len(message_correlations_send):
                return message_instance_receive

        return None

    def get_process_instance_for_message_instance(
        self, message_instance: MessageInstanceModel
    ) -> ProcessInstanceModel:
        """Get_process_instance_for_message_instance."""
        process_instance = ProcessInstanceModel.query.filter_by(
            id=message_instance.process_instance_id
        ).first()
        if process_instance is None:
            raise MessageServiceError(
                f"Process instance cannot be found for message: {message_instance.id}."
                f"Tried with id {message_instance.process_instance_id}"
            )

        return process_instance
