from fastapi.responses import JSONResponse
from typing import Any, Optional

def make_json_response(
    data: Optional[Any] = None,
    message: str = "",
    status: int = 200
) -> JSONResponse:
    return JSONResponse(
        content={
            "data": data,
            "message": message
        },
        status_code=status
    )

