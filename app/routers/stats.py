from collections import defaultdict
from datetime import UTC, datetime, timedelta

from dateutil.rrule import MINUTELY, rrule
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.deps.db import get_session
from app.models.tstat import Thermometer, TstatLog
from app.schemas.stats import StatsResponse

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def stats(type: str = "year", session: Session = Depends(get_session)) -> StatsResponse:
    # Django's StatsView.get() computes this "default" range unconditionally
    # first, and only the elif chain below overrides it -- there's no
    # branch for type == "year" at all, so "year" (and anything else
    # unrecognized) silently behaves exactly like "last24". Ported as-is.
    end = datetime.now(UTC)
    start = end - timedelta(hours=24)
    dates = list(rrule(freq=MINUTELY, dtstart=start, until=end))

    if type == "last24":
        end = datetime.now(UTC)
        start = end - timedelta(hours=24)
        dates = list(rrule(freq=MINUTELY, dtstart=start, until=end))
    elif type == "today":
        end = datetime.now(UTC)
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
        dates = list(rrule(freq=MINUTELY, dtstart=start, until=end))
    elif type == "yesterday":
        end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        dates = list(rrule(freq=MINUTELY, dtstart=start, until=end))

    labels = [str(d) for d in dates]
    totals: list = []
    thermometers: dict[str, list] = {}

    tstat_logs = session.exec(
        select(TstatLog).where(TstatLog.created_at >= start, TstatLog.created_at <= end)
    ).all()

    # BUG PORTED AS-IS (see plan doc / code review): Django's original
    # write loop does `format_stats[stat['romid']][stat['created_at']]`
    # on a model instance, which raises TypeError on every call with any
    # matching data -- that's a load-bearing crash, not a rare edge case,
    # so the minimal faithful fix here is attribute access instead of
    # subscript (`stat.romid_id`/`stat.created_at`), matching the
    # commented-out line in the original source that shows this was the
    # intended code. The SECOND bug is deliberately NOT fixed: the read
    # loop below indexes with a literal integer 0, never the real date,
    # so every value returned is always 0 regardless of actual sensor
    # data. Do not "fix" that as a drive-by -- it's out of scope here.
    format_stats: dict = defaultdict(lambda: defaultdict(int))
    for stat in tstat_logs:
        format_stats[stat.romid_id][stat.created_at] = stat.primary_value

    for thermometer in session.exec(select(Thermometer)).all():
        thermometers[thermometer.romid] = []
        for _date in dates:
            # Django's model instances are hashable by default (pk-based
            # __hash__), so `format_stats[thermometer]` was a valid (if
            # buggy) dict lookup there. SQLModel table objects are NOT
            # hashable by default -- using `thermometer` itself as a key
            # raises TypeError, a porting artifact rather than a bug to
            # preserve. `id(thermometer)` keeps the same observable
            # behavior (a key that never matches anything written above,
            # so this always falls through to the defaultdict(int)
            # default of 0) without crashing.
            thermometers[thermometer.romid].append(format_stats[id(thermometer)][0])

    return StatsResponse(labels=labels, totals=totals, thermometers=thermometers)
