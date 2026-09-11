class AppException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(msg)


class AuthException(AppException):
    def __init__(self, msg: str = "认证失败"):
        super().__init__(401, msg)


class ParamException(AppException):
    def __init__(self, msg: str = "参数错误"):
        super().__init__(400, msg)


class NotFoundException(AppException):
    def __init__(self, msg: str = "资源未找到"):
        super().__init__(404, msg)


class BusinessException(AppException):
    def __init__(self, code: int, msg: str):
        super().__init__(code, msg)
