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


# --- Moon: timezone handling, phase, and the overlay ---------------------


def test_moon_position_is_the_same_for_local_and_utc_times():
    # astral.moon reads a datetime's wall clock as UTC regardless of its
    # tzinfo; moon_now/rise_set_azimuths must convert first, or a Chicago
    # time is evaluated six hours early.
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services.almanac import moon_now

    observer = Observer(latitude=29.5714, longitude=-98.8519, elevation=427)
    local = datetime(2026, 11, 7, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    assert moon_now(observer, local) == moon_now(observer, local.astimezone(timezone.utc))


def test_moonrise_azimuth_is_where_the_moon_actually_is_at_moonrise():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from astral import moon as astral_moon

    from app.services.almanac import compute_moon_rise_set

    observer = Observer(latitude=29.5714, longitude=-98.8519, elevation=427)
    tz = ZoneInfo("America/Chicago")
    moonrise_at = compute_moon_rise_set(observer, date(2026, 11, 7), tz)["moonrise_at"]
    assert moonrise_at is not None

    result = rise_set_azimuths(observer, sunrise_at=None, sunset_at=None, moonrise_at=moonrise_at, moonset_at=None)

    # At moonrise the moon is on the horizon -- only true when evaluated at
    # the right instant -- and that azimuth is what gets reported.
    utc_moonrise = moonrise_at.astimezone(timezone.utc)
    assert abs(astral_moon.elevation(observer, utc_moonrise)) < 1
    assert abs(float(result["moonrise_azimuth_deg"]) - astral_moon.azimuth(observer, utc_moonrise)) < 0.01


def test_moon_illumination_and_phase_names():
    from app.services.almanac import moon_illumination, moon_phase_name

    full_fraction, _ = moon_illumination(date(2026, 11, 24))  # full moon 2026-11-24
    new_fraction, _ = moon_illumination(date(2026, 11, 9))  # new moon 2026-11-09
    assert full_fraction > 0.95
    assert new_fraction < 0.05
    _, waxing = moon_illumination(date(2026, 11, 16))
    assert waxing
    assert moon_phase_name(0.62, True) == "Waxing Gibbous"
    assert moon_phase_name(0.2, False) == "Waning Crescent"
    assert moon_phase_name(0.5, True) == "First Quarter"
    assert moon_phase_name(0.995, False) == "Full Moon"


def _render(**overrides):
    from datetime import datetime
    from decimal import Decimal
    from zoneinfo import ZoneInfo

    from app.services.almanac import render_compass_svg

    tz = ZoneInfo("America/Chicago")
    kwargs = dict(
        image_bytes=_make_png(1120, 689),
        day=date(2026, 11, 6),
        is_today=True,
        sunrise_at=datetime(2026, 11, 6, 6, 52, tzinfo=tz),
        sunset_at=datetime(2026, 11, 6, 17, 38, tzinfo=tz),
        sunrise_azimuth_deg=Decimal("108.5"),
        sunset_azimuth_deg=Decimal("251.5"),
        current_azimuth_deg=Decimal("205"),
        current_elevation_deg=Decimal("32"),
        radius_pct=0.385,
        now_local=datetime(2026, 11, 6, 13, 2, 31, tzinfo=tz),
        moonrise_at=datetime(2026, 11, 6, 13, 41, tzinfo=tz),
        moonset_at=datetime(2026, 11, 7, 1, 52, tzinfo=tz),
        moonrise_azimuth_deg=Decimal("92"),
        moonset_azimuth_deg=Decimal("268"),
        moon_azimuth_deg=Decimal("86"),
        moon_elevation_deg=Decimal("-8"),
        moon_fraction=0.62,
        moon_waxing=True,
    )
    kwargs.update(overrides)
    return render_compass_svg(**kwargs)


def test_compass_svg_readout_and_moon_overlay():
    svg = _render()
    ElementTree.fromstring(svg)  # well-formed
    text = svg.replace(" ", " ")
    assert "2026-11-06 13:02:31" in text  # date + time with seconds on a "today" render
    assert "Len 10h 46m" in text
    assert "Waxing Gibbous 62%" in text
    assert "Moonrise 13:41" in text and "Moonset 01:52" in text
    assert "rotate(" in svg  # the moon disc is drawn
    assert 'opacity="0.75"' in svg  # ...see-through, since it's below the horizon


def test_compass_svg_not_today_shows_no_bodies_or_time():
    svg = _render(is_today=False)
    text = svg.replace(" ", " ")
    assert "13:02:31" not in text
    assert "Sun: Len 10h 46m" in text
    assert "Moon: Waxing Gibbous 62%" in text
    assert "rotate(" not in svg


def test_clashing_rise_set_labels_get_moved_with_a_leader_line():
    from decimal import Decimal

    # Sun labels alone fit in their default spots -- no leader lines.
    sun_only = _render(moonrise_azimuth_deg=None, moonset_azimuth_deg=None)
    assert sun_only.count('r="2.5"') == 0  # leader-line dots
    # A moonrise 2° from sunrise can't share that spot, so it moves.
    clashing = _render(moonrise_azimuth_deg=Decimal("106.5"), moonset_azimuth_deg=None)
    assert clashing.count('r="2.5"') == 1
    assert "Moonrise 13:41" in clashing.replace("\u00a0", " ")


def test_sun_and_moon_labels_dodge_each_other():
    import re
    from decimal import Decimal

    # Sun and moon at the same bearing and almost the same height (a new
    # moon): both az/el labels would default to the same spot.
    svg = _render(
        current_azimuth_deg=Decimal("170"),
        current_elevation_deg=Decimal("40"),
        moon_azimuth_deg=Decimal("170"),
        moon_elevation_deg=Decimal("39"),
        moonrise_azimuth_deg=None,
        moonset_azimuth_deg=None,
    )
    sun_x, sun_y = (float(v) for v in re.search(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*><tspan[^>]*>170\.0° \+40\.0°', svg).groups())
    moon_x, moon_y = (float(v) for v in re.search(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*><tspan[^>]*>170\.0° \+39\.0°', svg).groups())
    # Not on top of each other: separated by at least a line height
    # vertically, or by a label width horizontally.
    assert abs(sun_y - moon_y) >= 0.08 * 265 or abs(sun_x - moon_x) > 50
