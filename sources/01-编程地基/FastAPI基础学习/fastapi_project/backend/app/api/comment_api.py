import os
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.current_user import get_current_user
from app.dependencies.api_dp import CommentServiceDep
from app.schemas.req.comment import CommentAddReq, CommentReplyReq
from app.core.image_utils import compress_image, ensure_upload_dir
from app.config.app_config import settings
from app.common.result import Result

router = APIRouter(prefix="/api/comment", tags=["评论"])


@router.api_route("/ueditor", methods=["GET", "POST"])
async def ueditor_action(request: Request, db: Session = Depends(get_db)) -> dict:
    action = request.query_params.get("action", "")
    if request.method == "GET" and action == "config":
        return settings.comment_ueditor_config
    if action == "image":
        form = await request.form()
        file = form.get("file")
        if not file:
            return JSONResponse({"state": "ERROR", "url": ""})
        ensure_upload_dir()
        suffix = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        newname = f"{time.strftime('%Y%m%d_%H%M%S')}.{suffix}"
        upload_path = os.path.join("resource/upload", newname)
        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)
        compress_image(upload_path, upload_path, 1200)
        return {
            "state": "SUCCESS",
            "url": f"/upload/{newname}",
            "title": file.filename,
            "original": file.filename,
        }
    return {"state": "ERROR"}


@router.post("/add")
async def add_comment(
    service: CommentServiceDep,
    req: CommentAddReq,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> Result:
    ipaddr = request.client.host if request.client else "0.0.0.0"
    r = service.add_comment(
        user_id=current_user["user_id"],
        article_id=req.article_id,
        content=req.content,
        ipaddr=ipaddr,
    )
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/reply")
async def reply_comment(
    service: CommentServiceDep,
    req: CommentReplyReq,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> Result:
    ipaddr = request.client.host if request.client else "0.0.0.0"
    r = service.add_reply(
        user_id=current_user["user_id"],
        article_id=req.article_id,
        content=req.content,
        ipaddr=ipaddr,
        reply_id=req.reply_id,
        base_reply_id=req.base_reply_id,
    )
    # 帮助定位：返回本次解析到的 user_id
    if r.get("code") == 200:
        data = r.get("data") or {}
        data["debug_user_id"] = current_user.get("user_id")
        r["data"] = data
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))
