"""Test User Blueprint."""

import json
from spiff_workflow_webapp.models.user import UserModel
from spiff_workflow_webapp.models.group import GroupModel


def test_user_can_be_created_and_deleted(client):
    username = "joe"
    response = client.get(f"/user/{username}")
    assert response.status_code == 201
    user = UserModel.query.filter_by(username=username).first()
    assert user.username == username

    response = client.delete(f"/user/{username}")
    assert response.status_code == 204
    user = UserModel.query.filter_by(username=username).first()
    assert user is None


def test_delete_returns_an_error_if_user_is_not_found(client):
    username = "joe"
    response = client.delete(f"/user/{username}")
    assert response.status_code == 400


def test_create_returns_an_error_if_user_exists(client):
    username = "joe"
    response = client.get(f"/user/{username}")
    assert response.status_code == 201
    user = UserModel.query.filter_by(username=username).first()
    assert user.username == username

    response = client.get(f"/user/{username}")
    assert response.status_code == 409

    response = client.delete(f"/user/{username}")
    assert response.status_code == 204
    user = UserModel.query.filter_by(username=username).first()
    assert user is None


def test_group_can_be_created_and_deleted(client):
    group_name = "administrators"
    response = client.get(f"/group/{group_name}")
    assert response.status_code == 201
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group.name == group_name

    response = client.delete(f"/group/{group_name}")
    assert response.status_code == 204
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group is None


def test_delete_returns_an_error_if_group_is_not_found(client):
    group_name = "administrators"
    response = client.delete(f"/group/{group_name}")
    assert response.status_code == 400


def test_create_returns_an_error_if_group_exists(client):
    group_name = "administrators"
    response = client.get(f"/group/{group_name}")
    assert response.status_code == 201
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group.name == group_name

    response = client.get(f"/group/{group_name}")
    assert response.status_code == 409

    response = client.delete(f"/group/{group_name}")
    assert response.status_code == 204
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group is None


def test_user_can_be_assigned_to_a_group(client):
    user = create_user(client, "joe")
    group = create_group(client, "administrators")
    response = client.post("/assign_user_to_group", content_type='application/json', data=json.dumps({"user_id": user.id, "group_id": group.id}))
    assert response.status_code == 201
    user = UserModel.query.filter_by(id=user.id).first()
    assert len(user.user_group_assignments) == 1
    assert user.user_group_assignments[0].group_id == group.id
    delete_user(client, user.username)
    delete_group(client, group.name)


def create_user(client, username):
    response = client.get(f"/user/{username}")
    assert response.status_code == 201
    user = UserModel.query.filter_by(username=username).first()
    assert user.username == username
    return user


def delete_user(client, username):
    response = client.delete(f"/user/{username}")
    assert response.status_code == 204
    user = UserModel.query.filter_by(username=username).first()
    assert user is None


def create_group(client, group_name):
    response = client.get(f"/group/{group_name}")
    assert response.status_code == 201
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group.name == group_name
    return group


def delete_group(client, group_name):
    response = client.delete(f"/group/{group_name}")
    assert response.status_code == 204
    group = GroupModel.query.filter_by(name=group_name).first()
    assert group is None
