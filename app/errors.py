from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        error: str,
        code: str | None = None,
        quota: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error)
        self.status = status
        self.error = error
        self.code = code
        self.quota = quota

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error}
        if self.code:
            body["code"] = self.code
        if self.quota is not None:
            body["quota"] = self.quota
        return body


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.to_body())
