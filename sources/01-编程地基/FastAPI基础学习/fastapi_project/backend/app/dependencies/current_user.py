from typing import Optional

from fastapi import Depends, HTTPException, Header

from app.core.security import decode_access_token
from app.config.db_config import SessionLocal
from app.dao.user_dao import UserDao


def get_current_user(
    authorization: Optional[str] = Header(None),
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token 格式错误")
    token = parts[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token 已过期或无效")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 解析失败")
    db = SessionLocal()
    try:
        user_dao = UserDao(db)
        user = user_dao.find_by_userid(int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")

        u = user_dao.model_to_dict(user)
        # 只返回前端需要的字段，避免泄露敏感信息
        return {
            "user_id": u.get("user_id"),
            "username": u.get("username"),
            "nickname": u.get("nickname"),
            "picture": u.get("picture"),
            "job": u.get("job"),
        }
    finally:
        db.close()


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> Optional[dict]:
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None
