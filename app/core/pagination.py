from fastapi import Request

from app.schemas.pagination import PAGE_SIZE, Page


def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return str(request.url.replace_query_params(**params))


def build_page(request: Request, items: list, total_count: int, page: int) -> Page:
    last_page = max(1, -(-total_count // PAGE_SIZE))  # ceil division
    next_url = _page_url(request, page + 1) if page < last_page else None
    previous_url = _page_url(request, page - 1) if page > 1 else None
    return Page(count=total_count, next=next_url, previous=previous_url, results=items)
