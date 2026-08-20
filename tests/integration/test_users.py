from app.services.confirm_email import generate_confirm_email_token
from tests.factories import auth_headers, make_user


def test_object_keys_for_own_user(client, session):
    user = make_user(session, email="me@example.com")
    headers = auth_headers(session, user)
    response = client.get(f"/v1/users/{user.id}", headers=headers)
    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "email",
        "is_email_verified",
        "first_name",
        "last_name",
        "avatar",
    }


def test_object_keys_for_other_user(client, session):
    user = make_user(session, email="them@example.com")
    response = client.get(f"/v1/users/{user.id}")
    assert response.status_code == 200
    assert set(response.json().keys()) == {"id", "first_name", "last_name", "avatar"}


def test_guest_can_list(client, session):
    make_user(session, email="a@example.com")
    response = client.get("/v1/users")
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_me_requires_auth(client):
    response = client.get("/v1/users/me")
    assert response.status_code == 401


def test_me_returns_self_shape(client, session):
    user = make_user(session, email="me@example.com")
    headers = auth_headers(session, user)
    response = client.get("/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_update_requires_auth(client, session):
    user = make_user(session, email="target@example.com")
    response = client.patch(f"/v1/users/{user.id}", json={"first_name": "New"})
    assert response.status_code == 401


def test_update_forbidden_for_other_user(client, session):
    user = make_user(session, email="target@example.com")
    other = make_user(session, email="other@example.com")
    headers = auth_headers(session, other)
    response = client.patch(f"/v1/users/{user.id}", json={"first_name": "New"}, headers=headers)
    assert response.status_code == 403


def test_update_self(client, session):
    user = make_user(session, email="me@example.com")
    headers = auth_headers(session, user)
    response = client.patch(f"/v1/users/{user.id}", json={"first_name": "New"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "New"


def test_change_password_requires_auth(client):
    response = client.post(
        "/v1/users/change-password", json={"current_password": "a", "new_password": "b"}
    )
    assert response.status_code == 401


def test_change_password_mismatch(client, session):
    user = make_user(session, email="me@example.com", password="password123")
    headers = auth_headers(session, user)
    response = client.post(
        "/v1/users/change-password",
        json={"current_password": "wrong", "new_password": "newpass123"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json() == {"current_password": ["That is not your current password."]}


def test_change_password_success(client, session):
    user = make_user(session, email="me@example.com", password="password123")
    headers = auth_headers(session, user)
    response = client.post(
        "/v1/users/change-password",
        json={"current_password": "password123", "new_password": "newpass123"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "success"}


def test_confirm_email_valid_token(client, session):
    user = make_user(session, email="me@example.com")
    token = generate_confirm_email_token(user)
    response = client.post(f"/v1/users/{user.id}/confirm-email", json={"token": token})
    assert response.status_code == 200
    session.refresh(user)
    assert user.is_email_verified is True


def test_confirm_email_invalid_token(client, session):
    user = make_user(session, email="me@example.com")
    response = client.post(f"/v1/users/{user.id}/confirm-email", json={"token": "garbage"})
    assert response.status_code == 400
    assert response.json() == {"token": ["Invalid token"]}


def test_confirm_email_nonexistent_user_is_400_not_404(client):
    response = client.post("/v1/users/999999/confirm-email", json={"token": "garbage"})
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Invalid token"]}
