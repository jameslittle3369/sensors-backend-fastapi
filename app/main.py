from fastapi import FastAPI

from app.core.errors import ApiFieldError, api_field_error_handler
from app.routers import (
    aqsensors,
    cameras,
    login,
    register,
    stats,
    thermohygrometers,
    thermometers,
    tstats,
    users,
)

app = FastAPI(title="sensors-backend-fastapi")

app.add_exception_handler(ApiFieldError, api_field_error_handler)

# Mounted under /v1, matching Django's root-mount (no /api/ prefix), so
# existing mobile clients' hardcoded base URLs keep working unchanged.
app.include_router(login.router, prefix="/v1")
app.include_router(register.router, prefix="/v1")
app.include_router(users.router, prefix="/v1")
app.include_router(aqsensors.router, prefix="/v1")
app.include_router(cameras.router, prefix="/v1")
app.include_router(thermometers.router, prefix="/v1")
app.include_router(thermohygrometers.router, prefix="/v1")
app.include_router(tstats.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
