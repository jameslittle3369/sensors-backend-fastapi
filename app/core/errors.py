from fastapi import Request
from fastapi.responses import JSONResponse

# DRF renders validation errors as {field: [messages]} at the top level of
# the response body (not nested under "detail"). Existing mobile clients
# may parse that exact shape, so ApiFieldError reproduces it instead of
# using FastAPI's default {"detail": ...} error body.

NON_FIELD_ERRORS_KEY = "non_field_errors"


class ApiFieldError(Exception):
    def __init__(self, errors: dict[str, list[str]], status_code: int = 400) -> None:
        self.errors = errors
        self.status_code = status_code
        super().__init__(errors)

    @classmethod
    def field(cls, field: str, message: str, status_code: int = 400) -> "ApiFieldError":
        return cls({field: [message]}, status_code=status_code)

    @classmethod
    def non_field(cls, message: str, status_code: int = 400) -> "ApiFieldError":
        return cls({NON_FIELD_ERRORS_KEY: [message]}, status_code=status_code)


async def api_field_error_handler(request: Request, exc: ApiFieldError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.errors)
