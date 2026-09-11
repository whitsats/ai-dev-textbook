from typing import Any

from pydantic import BaseModel, ConfigDict


class Result(BaseModel):
    """统一响应封装"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int
    msg: str
    data: Any = None

    @staticmethod
    def success(data: Any = None, msg: str = "success") -> "Result":
        return Result(code=200, msg=msg, data=data)

    @staticmethod
    def error(msg: str = "error") -> "Result":
        return Result(code=500, msg=msg)

    @staticmethod
    def other(msg: str = "bad request") -> "Result":
        return Result(code=400, msg=msg)

    @staticmethod
    def unauthorized(msg: str = "unauthorized") -> "Result":
        return Result(code=401, msg=msg)

    @staticmethod
    def forbidden(msg: str = "forbidden") -> "Result":
        return Result(code=403, msg=msg)

    @staticmethod
    def not_found(msg: str = "not found") -> "Result":
        return Result(code=404, msg=msg)
