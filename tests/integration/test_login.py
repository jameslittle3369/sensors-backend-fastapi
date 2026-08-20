from tests.factories import make_user


def test_can_login(client, session):
    make_user(session, email="user@example.com", password="password123")
    response = client.post("/v1/login", json={"email": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    assert set(response.json().keys()) == {"token"}


def test_when_email_doesnt_exist(client):
    response = client.post("/v1/login", json={"email": "nobody@example.com", "password": "x"})
    assert response.status_code == 400
    assert response.json() == {"email": ["Email does not exist."]}


def test_when_password_doesnt_match(client, session):
    make_user(session, email="user@example.com", password="password123")
    response = client.post("/v1/login", json={"email": "user@example.com", "password": "wrong"})
    assert response.status_code == 400
    assert response.json() == {"password": ["Incorrect password."]}
