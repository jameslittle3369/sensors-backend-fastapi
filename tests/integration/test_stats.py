from app.models.tstat import Thermometer, TstatLog


def test_stats_does_not_crash_and_values_are_always_zero(client, session):
    # Ported bug: the read loop in /v1/stats indexes format_stats with a
    # literal integer 0, never the real date, so every value is always
    # the defaultdict(int) default of 0 -- even though real TstatLog
    # data exists in range. Pinned here so it isn't silently "fixed" by
    # a future refactor without a deliberate decision.
    session.add(Thermometer(romid="28FF001", pretty_name="Living Room"))
    session.add(TstatLog(romid_id="28FF001", primary_value="20.0000"))
    session.commit()

    response = client.get("/v1/stats", params={"type": "last24"})
    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == []
    assert all(v == 0 for v in body["thermometers"]["28FF001"])
