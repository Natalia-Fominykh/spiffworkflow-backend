"""User."""
import jwt
import marshmallow
from flask import current_app
from flask_bpmn.models.db import db
from flask_bpmn.models.db import SpiffworkflowBaseDBModel
from marshmallow import Schema
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates

from spiffworkflow_backend.models.group import GroupModel
from spiffworkflow_backend.models.user_group_assignment import UserGroupAssignmentModel
from spiffworkflow_backend.services.authentication_service import AuthenticationProviderTypes


class UserModel(SpiffworkflowBaseDBModel):
    """UserModel."""

    __tablename__ = "user"
    __table_args__ = (db.UniqueConstraint("service", "service_id", name="service_key"),)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    uid = db.Column(db.String(50), unique=True)
    service = db.Column(db.String(50), nullable=False, unique=False)
    service_id = db.Column(db.String(), nullable=False, unique=False)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50))
    user_group_assignments = relationship(UserGroupAssignmentModel, cascade="delete")
    groups = relationship(  # type: ignore
        GroupModel,
        viewonly=True,
        secondary="user_group_assignment",
        overlaps="user_group_assignments,users",
    )

    @validates('service')
    def validate_service(self, key, value):
        assert value in AuthenticationProviderTypes._member_names_
        return value

    def encode_auth_token(self) -> str:
        """Generate the Auth Token.

        :return: string
        """
        secret_key = current_app.config.get("SECRET_KEY")
        if secret_key is None:
            raise KeyError("we need current_app.config to have a SECRET_KEY")

        # hours = float(app.config['TOKEN_AUTH_TTL_HOURS'])
        payload = {
            # 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=hours, minutes=0, seconds=0),
            # 'iat': datetime.datetime.utcnow(),
            "sub": f"service:{self.service}::service_id:{self.service_id}",
            "token_type": "internal",
        }
        return jwt.encode(
            payload,
            secret_key,
            algorithm="HS256",
        )

    def is_admin(self) -> bool:
        """Is_admin."""
        return True

    # @classmethod
    # def from_open_id_user_info(cls, user_info: dict) -> Any:
    #     """From_open_id_user_info."""
    #     instance = cls()
    #     instance.service = "keycloak"
    #     instance.service_id = user_info["sub"]
    #     instance.name = user_info["preferred_username"]
    #     instance.username = user_info["sub"]
    #
    #     return instance


class UserModelSchema(Schema):
    """UserModelSchema."""

    class Meta:
        """Meta."""

        model = UserModel
        # load_instance = True
        # include_relationships = False
        # exclude = ("UserGroupAssignment",)

    id = marshmallow.fields.String(required=True)
    username = marshmallow.fields.String(required=True)


class AdminSessionModel(SpiffworkflowBaseDBModel):
    """AdminSessionModel."""

    __tablename__ = "admin_session"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(50), unique=True)
    admin_impersonate_uid = db.Column(db.String(50))
