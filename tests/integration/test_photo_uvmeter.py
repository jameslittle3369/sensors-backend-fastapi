from sqlmodel import select

from app.models.photo_uvmeter import PhotoUvmeter, PhotoUvmeterLog


def test_log_creates_photo_uvmeter_and_log_when_new(client, session):
    response = client.post(
        "/v1/photo-uvmeters/119/log",
        json={"name": "Atlas 119", "lumens": 5000, "uv_index": 3},
    )
    assert response.status_code == 200
    assert response.json() == {"external_id": "119", "created": True}

    device = session.get(PhotoUvmeter, "119")
    assert device is not None
    assert device.current_lumens == 5000
    assert device.current_uv_index == 3

    logs = session.exec(
        select(PhotoUvmeterLog).where(PhotoUvmeterLog.photo_uvmeter_id == "119")
    ).all()
    assert len(logs) == 1


def test_log_dedups_unchanged_reading(client, session):
    session.add(PhotoUvmeter(external_id="zone-2", name="Test"))
    session.commit()

    payload = {"name": "Test", "lumens": 100, "uv_index": 0}
    first = client.post("/v1/photo-uvmeters/zone-2/log", json=payload)
    second = client.post("/v1/photo-uvmeters/zone-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(
        select(PhotoUvmeterLog).where(PhotoUvmeterLog.photo_uvmeter_id == "zone-2")
    ).all()
    assert len(logs) == 1


def test_log_inserts_when_value_changes(client, session):
    session.add(PhotoUvmeter(external_id="zone-3", name="Test"))
    session.commit()

    client.post(
        "/v1/photo-uvmeters/zone-3/log",
        json={"name": "Test", "lumens": 100, "uv_index": 0},
    )
    client.post(
        "/v1/photo-uvmeters/zone-3/log",
        json={"name": "Test", "lumens": 200, "uv_index": 0},
    )

    logs = session.exec(
        select(PhotoUvmeterLog).where(PhotoUvmeterLog.photo_uvmeter_id == "zone-3")
    ).all()
    assert len(logs) == 2
