from tests.factories import make_user


def test_can_register(client):
    response = client.post(
        "/v1/register",
        json={"email": "new@example.com", "password": "password123", "first_name": "New"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["first_name"] == "New"
    assert body["is_email_verified"] is False


def test_duplicate_email(client, session):
    make_user(session, email="taken@example.com")
    response = client.post(
        "/v1/register", json={"email": "taken@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json() == {"email": ["That email is already in use.  Choose another."]}
