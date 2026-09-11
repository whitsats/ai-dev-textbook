from pydantic import BaseModel, Field


class LoginReq(BaseModel):
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")
    vcode: str = Field(..., min_length=1, description="图形验证码")


class RegisterReq(BaseModel):
    username: str = Field(..., description="用户名（邮箱格式）")
    password: str = Field(..., min_length=6, description="密码")
    second_password: str = Field(..., description="确认密码")
    ecode: str = Field(..., min_length=1, description="邮箱验证码")


class SendEmailCodeReq(BaseModel):
    email: str = Field(..., description="邮箱地址")


class LogoutReq(BaseModel):
    pass
