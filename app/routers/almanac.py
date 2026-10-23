from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from astral import Observer
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.deps.db import get_session
from app.models.almanac import ALMANAC_METRIC_FIELDS, AlmanacDay
from app.schemas.almanac import AlmanacDatesResponse, AlmanacDayLogRequest, AlmanacDayLogResponse
from app.services.almanac import (
    UnsupportedImageError,
    compute_rise_set,
    observer_from_settings,
    render_compass_svg,
    rise_set_azimuths,
    sun_now,
)

router = APIRouter(tags=["almanac"])


@router.post("/almanac-days/{site}/log", response_model=AlmanacDayLogResponse)
def log_almanac_day(
    site: str,
    payload: AlmanacDayLogRequest,
    session: Session = Depends(get_session),
) -> AlmanacDayLogResponse:
    settings = get_settings()
    # Prefer the coordinates the logger actually used to fetch sunrise/
    # sunset from the API -- guarantees the azimuth matches the times it
    # was derived from, even if the backend's own settings later drift.
    observer = Observer(
        latitude=float(payload.latitude) if payload.latitude is not None else float(settings.latitude),
        longitude=float(payload.longitude) if payload.longitude is not None else float(settings.longitude),
        elevation=float(payload.elevation_m) if payload.elevation_m is not None else float(settings.elevation_m),
    )
    azimuths = rise_set_azimuths(
        observer,
        sunrise_at=payload.sunrise_at,
        sunset_at=payload.sunset_at,
        moonrise_at=payload.moonrise_at,
        moonset_at=payload.moonset_at,
    )

    existing = session.exec(select(AlmanacDay).where(AlmanacDay.site == site, AlmanacDay.day == payload.day)).first()

    candidate = payload.model_dump(exclude={"day", "raw"})
    candidate.update(azimuths)

    if existing is not None and all(getattr(existing, field) == candidate.get(field) for field in ALMANAC_METRIC_FIELDS):
        return AlmanacDayLogResponse(site=site, day=payload.day, created=False, **azimuths)

    if existing is None:
        existing = AlmanacDay(site=site, day=payload.day)

    for field in ALMANAC_METRIC_FIELDS:
        setattr(existing, field, candidate.get(field))
    existing.raw = payload.raw
    existing.fetched_at = datetime.now(UTC)

    session.add(existing)
    session.commit()
    return AlmanacDayLogResponse(site=site, day=payload.day, created=True, **azimuths)


@router.get("/almanac-days/{site}/dates", response_model=AlmanacDatesResponse)
def list_almanac_dates(
    site: str,
    start: date | None = None,
    end: date | None = None,
    session: Session = Depends(get_session),
) -> AlmanacDatesResponse:
    """What's already logged for `site` -- the astronomy app calls this
    first and only fetches/pushes the gaps, so a day already banked never
    costs another API credit."""
    statement = select(AlmanacDay.day).where(AlmanacDay.site == site)
    if start is not None:
        statement = statement.where(col(AlmanacDay.day) >= start)
    if end is not None:
        statement = statement.where(col(AlmanacDay.day) <= end)
    rows = session.exec(statement.order_by(col(AlmanacDay.day))).all()
    return AlmanacDatesResponse(dates=list(rows))


@router.get("/almanac-days/{site}/compass.svg")
def compass_svg(
    site: str,
    day: date | None = None,
    at: datetime | None = None,
    session: Session = Depends(get_session),
) -> Response:
    """The Grafana panel image. Renders for *any* date -- a stored
    AlmanacDay row only supplies the API-sourced rise/set times and their
    azimuths; failing that, both come straight from astral. `at`
    overrides "now" for deterministic testing/screenshots."""
    settings = get_settings()
    target_day = day or date.today()
    now = at or datetime.now(UTC)

    if not settings.house_image_path:
        raise HTTPException(status_code=500, detail="HOUSE_IMAGE_PATH is not configured")
    try:
        with open(settings.house_image_path, "rb") as image_file:
            image_bytes = image_file.read()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read house image: {exc}") from exc

    observer = observer_from_settings(settings)
    tzinfo = ZoneInfo(settings.timezone)

    row = session.exec(select(AlmanacDay).where(AlmanacDay.site == site, AlmanacDay.day == target_day)).first()
    if row is not None and row.sunrise_at is not None:
        sunrise_at, sunset_at = row.sunrise_at, row.sunset_at
        sunrise_azimuth_deg, sunset_azimuth_deg = row.sunrise_azimuth_deg, row.sunset_azimuth_deg
    else:
        rise_set = compute_rise_set(observer, target_day, tzinfo)
        sunrise_at, sunset_at = rise_set["sunrise_at"], rise_set["sunset_at"]
        azimuths = rise_set_azimuths(observer, sunrise_at=sunrise_at, sunset_at=sunset_at, moonrise_at=None, moonset_at=None)
        sunrise_azimuth_deg, sunset_azimuth_deg = azimuths["sunrise_azimuth_deg"], azimuths["sunset_azimuth_deg"]

    # A row's sunrise_at/sunset_at come back from Postgres in whatever
    # timezone the DB session defaults to -- not necessarily this site's
    # timezone -- so the display labels need an explicit conversion
    # rather than trusting whatever tzinfo the driver happened to attach.
    if sunrise_at is not None:
        sunrise_at = sunrise_at.astimezone(tzinfo)
    if sunset_at is not None:
        sunset_at = sunset_at.astimezone(tzinfo)

    is_today = now.astimezone(tzinfo).date() == target_day
    current_azimuth_deg = current_elevation_deg = None
    if is_today:
        current_azimuth_deg, current_elevation_deg = sun_now(observer, now)

    try:
        svg = render_compass_svg(
            image_bytes=image_bytes,
            day=target_day,
            is_today=is_today,
            sunrise_at=sunrise_at,
            sunset_at=sunset_at,
            sunrise_azimuth_deg=sunrise_azimuth_deg,
            sunset_azimuth_deg=sunset_azimuth_deg,
            current_azimuth_deg=current_azimuth_deg,
            current_elevation_deg=current_elevation_deg,
            north_offset_deg=settings.compass_north_offset_deg,
            center_x_pct=settings.compass_center_x_pct,
            center_y_pct=settings.compass_center_y_pct,
            radius_pct=settings.compass_radius_pct,
        )
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Response(content=svg, media_type="image/svg+xml")
