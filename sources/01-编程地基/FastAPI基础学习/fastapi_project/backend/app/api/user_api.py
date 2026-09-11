from fastapi import APIRouter, Depends, Response, Cookie, Request
from fastapi.responses import JSONResponse
from http.cookies import SimpleCookie

from app.dependencies.current_user import get_current_user
from app.dependencies.api_dp import UserServiceDep
from app.schemas.req.user import LoginReq, RegisterReq, SendEmailCodeReq
from app.core.vcode import ImageCode
from app.common.result import Result

router = APIRouter(prefix="/api/user", tags=["用户"])


@router.get("/vcode")
async def get_vcode(response: Response):
    vcode = ImageCode()
    code, image_bytes = vcode.get_code()

    cookie = SimpleCookie()
    cookie["vcode"] = code.lower()
    cookie["vcode"]["max-age"] = 300
    cookie["vcode"]["httponly"] = True
    cookie["vcode"]["samesite"] = "lax"
    cookie["vcode"]["path"] = "/"

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Set-Cookie": cookie["vcode"].OutputString()}
    )


@router.post("/ecode")
async def send_email_code(
    req: SendEmailCodeReq,
    service: UserServiceDep,
) -> Result:
    r = service.send_email_code(req.email)
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/reg")
async def register(
    req: RegisterReq,
    service: UserServiceDep,
) -> Result:
    r = service.register(
        req.username, req.password, req.second_password, req.ecode
    )
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/login")
async def login(
    request: Request,
    req: LoginReq,
    response: Response,
    service: UserServiceDep,
) -> Result:
    vcode = request.cookies.get("vcode")
    if not vcode or req.vcode.lower() != vcode.lower():
        return Result(code=400, msg="验证码错误")
    r = service.login(req.username, req.password)
    if r.get("code") == 200 and r.get("data"):
        response.set_cookie(
            "token",
            r["data"].get("token"),
            max_age=86400 * 7,
            httponly=True,
            samesite="lax",
        )
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/logout")
async def logout(response: Response) -> Result:
    response.delete_cookie("token")
    return Result.success(msg="注销成功")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)) -> Result:
    return Result.success(data=current_user)
