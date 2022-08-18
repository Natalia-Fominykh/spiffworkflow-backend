"""Message_correlation_property."""
from flask_bpmn.models.db import db
from flask_bpmn.models.db import SpiffworkflowBaseDBModel
from sqlalchemy import ForeignKey

from spiffworkflow_backend.models.message_model import MessageModel


class MessageCorrelationPropertyModel(SpiffworkflowBaseDBModel):
    """MessageCorrelationPropertyModel."""

    __tablename__ = "message_correlation_property"
    __table_args__ = (
        db.UniqueConstraint(
            "message_model_id", "identifier", name="message_model_id_identifier_unique"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    message_model_id = db.Column(ForeignKey(MessageModel.id), nullable=False)
    identifier = db.Column(db.String(50), index=True)
    updated_at_in_seconds: int = db.Column(db.Integer)
    created_at_in_seconds: int = db.Column(db.Integer)
