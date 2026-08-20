from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.deps.db import get_session
from app.services.tstat_ingest import run_ingestion

router = APIRouter(tags=["tstats"])


@router.get("/tstats")
def list_tstats() -> dict:
    # Django's TstatsViewSet.list() returns {} immediately -- the rest of
    # the method (below the return) is dead code. Ported verbatim.
    return {}


@router.post("/tstats")
def create_tstat(session: Session = Depends(get_session)) -> list[str] | None:
    return run_ingestion(session)
