import struct
import zlib
from datetime import date, timezone

import pytest
from astral import Observer
from astral import sun as astral_sun
from sqlmodel import select
from xml.etree import ElementTree

from app.core.config import get_settings
from app.models.almanac import AlmanacDay
from app.services.almanac import rise_set_azimuths, sniff_image


def _make_png(width: int = 4, height: int = 3) -> bytes:
    """A tiny, genuinely valid PNG -- not a fixture file, so the test
    doesn't depend on a binary asset living in the repo."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + bytes([200, 150, 100]) * width for _ in range(height))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture
def house_image(tmp_path, monkeypatch):
    """Points the app at a real, tiny house image and a fixed location
    for the duration of one test, then restores the Settings cache so
    nothing leaks into the next test."""
    image_path = tmp_path / "house.png"
    image_path.write_bytes(_make_png(400, 300))

    monkeypatch.setenv("HOUSE_IMAGE_PATH", str(image_path))
    monkeypatch.setenv("LATITUDE", "40.7128")
    monkeypatch.setenv("LONGITUDE", "-74.0060")
    monkeypatch.setenv("ELEVATION_M", "10")
    monkeypatch.setenv("TIMEZONE", "America/New_York")
    get_settings.cache_clear()
    yield image_path
    get_settings.cache_clear()


# --- POST /almanac-days/{site}/log --------------------------------------


def _payload(day: str, sunrise: str, sunset: str, **extra) -> dict:
    body = {
        "day": day,
        "latitude": "40.7128",
        "longitude": "-74.0060",
        "elevation_m": "10",
        "timezone_name": "America/New_York",
        "sunrise_at": sunrise,
        "sunset_at": sunset,
        "sun_status": "-",
    }
    body.update(extra)
    return body


def test_log_creates_row_and_computes_azimuths(client, session):
    # March equinox: sunrise/sunset should land close to due east/west
    # everywhere outside the poles, independent of latitude.
    payload = _payload(
        "2026-03-20",
        "2026-03-20T06:58:00-04:00",
        "2026-03-20T19:08:00-04:00",
        event="march_equinox",
    )
    response = client.post("/v1/almanac-days/home/log", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert abs(float(body["sunrise_azimuth_deg"]) - 90) < 2
    assert abs(float(body["sunset_azimuth_deg"]) - 270) < 2

    row = session.exec(
        select(AlmanacDay).where(AlmanacDay.site == "home", AlmanacDay.day == date(2026, 3, 20))
    ).first()
    assert row is not None
    assert row.event == "march_equinox"
    assert row.sunrise_azimuth_deg is not None


def test_log_dedups_unchanged_day(client, session):
    payload = _payload("2026-06-21", "2026-06-21T05:25:00-04:00", "2026-06-21T20:31:00-04:00", event="june_solstice")
    first = client.post("/v1/almanac-days/home/log", json=payload)
    second = client.post("/v1/almanac-days/home/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False
    # On the June solstice, a northern-hemisphere sunrise is well north
    # of due east.
    assert float(first.json()["sunrise_azimuth_deg"]) < 90


def test_log_updates_in_place_when_values_change(client, session):
    base = _payload("2026-12-21", "2026-12-21T07:17:00-05:00", "2026-12-21T16:32:00-05:00", event="december_solstice")
    client.post("/v1/almanac-days/home/log", json=base)

    changed = dict(base, sunset_at="2026-12-21T16:35:00-05:00")
    response = client.post("/v1/almanac-days/home/log", json=changed)
    assert response.json()["created"] is True

    rows = session.exec(
        select(AlmanacDay).where(AlmanacDay.site == "home", AlmanacDay.day == date(2026, 12, 21))
    ).all()
    # Updated in place -- still exactly one row for this (site, day), not
    # a second log entry.
    assert len(rows) == 1
    # December solstice: sunrise well south of due east.
    assert float(response.json()["sunrise_azimuth_deg"]) > 90


# --- GET /almanac-days/{site}/dates --------------------------------------


def test_list_dates_filters_by_range(client):
    for day, sunrise, sunset in (
        ("2026-01-01", "2026-01-01T07:20:00-05:00", "2026-01-01T16:40:00-05:00"),
        ("2026-06-21", "2026-06-21T05:25:00-04:00", "2026-06-21T20:31:00-04:00"),
        ("2026-12-21", "2026-12-21T07:17:00-05:00", "2026-12-21T16:32:00-05:00"),
    ):
        client.post("/v1/almanac-days/home/log", json=_payload(day, sunrise, sunset))

    response = client.get("/v1/almanac-days/home/dates", params={"start": "2026-06-01", "end": "2026-12-31"})
    assert response.status_code == 200
    assert response.json()["dates"] == ["2026-06-21", "2026-12-21"]


# --- GET /almanac-days/{site}/compass.svg --------------------------------


def test_compass_svg_for_logged_day(client, house_image):
    payload = _payload("2026-03-20", "2026-03-20T06:58:00-04:00", "2026-03-20T19:08:00-04:00", event="march_equinox")
    client.post("/v1/almanac-days/home/log", json=payload)

    response = client.get(
        "/v1/almanac-days/home/compass.svg",
        params={"day": "2026-03-20", "at": "2026-03-20T12:00:00-04:00"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    root = ElementTree.fromstring(response.text)
    assert root.tag.endswith("svg")
    # Regression check: a sunrise_at read back from Postgres comes back
    # in whatever timezone the DB session defaults to, not necessarily
    # this site's America/New_York -- the label must show 06:58 (what was
    # actually posted), not that session-default clock time.
    assert "06:58" in response.text


def test_compass_svg_for_unlogged_day_still_renders(client, house_image):
    # No POST for this date at all -- the endpoint falls back to astral
    # directly, per the panel's "any date" design.
    response = client.get(
        "/v1/almanac-days/home/compass.svg",
        params={"day": "2031-07-04"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    root = ElementTree.fromstring(response.text)
    assert root.tag.endswith("svg")


# --- Service-level sanity (independent of the HTTP layer) ---------------


def test_rise_set_azimuths_equinox_is_due_east_and_west():
    observer = Observer(latitude=40.7128, longitude=-74.0060, elevation=10)
    day = date(2026, 3, 20)
    sunrise_at = astral_sun.sunrise(observer, day, tzinfo=timezone.utc)
    sunset_at = astral_sun.sunset(observer, day, tzinfo=timezone.utc)

    result = rise_set_azimuths(observer, sunrise_at=sunrise_at, sunset_at=sunset_at, moonrise_at=None, moonset_at=None)

    assert abs(float(result["sunrise_azimuth_deg"]) - 90) < 2
    assert abs(float(result["sunset_azimuth_deg"]) - 270) < 2
    assert result["moonrise_azimuth_deg"] is None
    assert result["moonset_azimuth_deg"] is None


def test_rise_set_azimuths_solstices_bracket_the_equinox():
    observer = Observer(latitude=40.7128, longitude=-74.0060, elevation=10)
    june_sunrise = astral_sun.sunrise(observer, date(2026, 6, 21), tzinfo=timezone.utc)
    december_sunrise = astral_sun.sunrise(observer, date(2026, 12, 21), tzinfo=timezone.utc)

    june = rise_set_azimuths(observer, sunrise_at=june_sunrise, sunset_at=None, moonrise_at=None, moonset_at=None)
    december = rise_set_azimuths(
        observer, sunrise_at=december_sunrise, sunset_at=None, moonrise_at=None, moonset_at=None
    )

    # Northern hemisphere: June sunrise is north of due east, December
    # sunrise is south of it.
    assert float(june["sunrise_azimuth_deg"]) < 90 < float(december["sunrise_azimuth_deg"])


def test_sniff_image_reads_png_dimensions():
    mime, width, height = sniff_image(_make_png(400, 300))
    assert mime == "image/png"
    assert (width, height) == (400, 300)


def test_sniff_image_rejects_unknown_format():
    from app.services.almanac import UnsupportedImageError

    with pytest.raises(UnsupportedImageError):
        sniff_image(b"not an image")
