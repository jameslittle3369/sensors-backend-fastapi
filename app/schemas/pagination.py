from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

# Mirrors DRF's PageNumberPagination response shape (PAGE_SIZE=30,
# page query param "page") so existing clients parsing {count, next,
# previous, results} keep working unchanged.
PAGE_SIZE = 30


class Page(BaseModel, Generic[T]):
    count: int
    next: str | None
    previous: str | None
    results: list[T]
