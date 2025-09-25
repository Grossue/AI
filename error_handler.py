
from fastapi import FastAPI, Request, status
from make_response import make_json_response
from fastapi.exceptions import HTTPException

class UnprocessableEntityException(HTTPException):
    def __init__(self, detail: str = "입력값을 처리할 수 없습니다."):
        super().__init__(status_code=422, detail=detail)

def register_exception_handlers(app: FastAPI) -> None:
    """전역 예외 핸들러들을 FastAPI 인스턴스에 등록한다.

    사용 예시::

        from fastapi import FastAPI
        from error_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    @app.exception_handler(UnprocessableEntityException)
    async def unprocessable_entity_exception_handler(request: Request, exc: UnprocessableEntityException):
        return make_json_response(
            message=str(exc.detail),
            status=422
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
      return make_json_response(
          message="AI 서버 에러 (예상치 못한 에러 발생)",
          status=500
  )
