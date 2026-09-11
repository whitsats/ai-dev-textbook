import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.dependencies.current_user import get_current_user, get_current_user_optional
from app.dependencies.api_dp import ArticleServiceDep
from app.schemas.req.article import ArticleSaveReq, DraftedDetailReq
from app.core.image_utils import compress_image, ensure_upload_dir
from app.config.app_config import settings
from app.common.result import Result

router = APIRouter(prefix="/api/article", tags=["文章"])


@router.get("/detail")
async def get_article_detail(
    service: ArticleServiceDep,
    article_id: int = Query(..., description="文章ID"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> Result:
    r = service.get_detail(article_id, current_user)
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.get("/new-page")
async def get_new_page(
    service: ArticleServiceDep,
    current_user: dict = Depends(get_current_user),
) -> Result:
    r = service.get_new_page_data(current_user["user_id"])
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/drafted")
async def get_drafted_detail(
    service: ArticleServiceDep,
    req: DraftedDetailReq,
    current_user: dict = Depends(get_current_user),
) -> Result:
    r = service.get_drafted_detail(req.id)
    return Result(code=r["code"], msg=r["msg"], data=r.get("data"))


@router.post("/save")
async def save_article(
    service: ArticleServiceDep,
    req: ArticleSaveReq,
    current_user: dict = Depends(get_current_user),
) -> Result:
    try:
        r = service.save_article(
            user_id=current_user["user_id"],
            article_id=req.article_id,
            title=req.title,
            article_content=req.article_content,
            drafted=req.drafted,
            label_name=req.label_name,
            article_tag=req.article_tag,
            article_type=req.article_type,
            article_image=req.article_image,
        )
        return Result(code=r["code"], msg=r["msg"], data=r.get("data"))
    except PermissionError as e:
        return Result(code=403, msg=str(e))


@router.post("/upload")
async def upload_header_image(
    service: ArticleServiceDep,
    article_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> Result:
    ensure_upload_dir()

    # 统一存 jpg
    newname = f"article-header-{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    upload_path = str(settings.upload_dir_abs / newname)

    contents = await file.read()
    with open(upload_path, "wb") as f:
        f.write(contents)

    compress_image(upload_path, upload_path, 1200)

    # 数据库存相对路径
    rel_path = f"article/header/{newname}"
    try:
        r = service.upload_header_image(article_id, rel_path, current_user["user_id"])
    except PermissionError as e:
        return Result(code=403, msg=str(e))

    # upload_header_image 返回的是 {state,url,...}，不是 {code,msg,data}
    if isinstance(r, dict) and r.get("state") == "SUCCESS":
        return Result(code=200, msg="success", data=r)
    return Result(
        code=400,
        msg=(r.get("msg") if isinstance(r, dict) else "上传头图失败"),
        data=r if isinstance(r, dict) else None,
    )

