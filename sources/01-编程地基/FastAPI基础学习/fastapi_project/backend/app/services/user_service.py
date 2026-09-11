import re
import random
from typing import Any

from sqlalchemy.orm import Session

from app.dao.user_dao import UserDao
from app.core.security import hash_password, verify_password, create_access_token
from app.core.email import gen_email_code, send_email
from app.config.redis_config import get_redis_client
from app.config.app_config import settings


class UserService:
    def __init__(self, db: Session, dao: UserDao):
        self.db = db
        self.dao = dao

    def send_email_code(self, email: str) -> dict[str, Any]:
        if not re.match(r".+@.+\..+", email):
            return {"code": 400, "msg": "无效的邮箱"}
        code = gen_email_code()
        redis_client = get_redis_client()
        redis_client.set(f"email:code:{email}", code.lower(), ex=300)
        # 开发环境：直接返回验证码
        # 生产环境：调用 send_email(email, code) 发送真实邮件
        return {"code": 200, "msg": "验证码已生成", "data": {"code": code}}

    def register(self, username: str, password: str, second_password: str, ecode: str) -> dict[str, Any]:
        if not re.match(r".+@.+\..+", username):
            return {"code": 400, "msg": "无效的邮箱"}
        if len(password) < 6:
            return {"code": 400, "msg": "密码不合法"}
        if password != second_password:
            return {"code": 400, "msg": "两次密码不一致"}
        redis_client = get_redis_client()
        stored_code = redis_client.get(f"email:code:{username}")
        if not stored_code or stored_code.lower() != ecode.lower():
            return {"code": 400, "msg": "邮箱验证码错误"}
        existing = self.dao.find_by_username(username)
        if existing:
            return {"code": 400, "msg": "用户名已经存在"}
        hashed = hash_password(password)
        nickname = username.split("@")[0]
        picture_num = random.randint(1, 539)
        picture = f"{picture_num}.jpg"
        user = self.dao.create_user(username, hashed, nickname, picture)
        user_dict = self.dao.model_to_dict(user)
        return {"code": 200, "msg": "注册成功", "data": user_dict}

    def login(self, username: str, password: str) -> dict[str, Any]:
        user_list = self.dao.find_by_username(username)
        if not user_list:
            return {"code": 400, "msg": "用户名或密码错误"}
        user = user_list[0]
        if not verify_password(password, user.password):
            return {"code": 400, "msg": "用户名或密码错误"}
        token = create_access_token({"sub": str(user.user_id)})
        user_dict = self.dao.model_to_dict(user)
        user_dict["token"] = token
        user_dict.pop("password", None)
        return {"code": 200, "msg": "登录成功", "data": user_dict}

    def get_user_info(self, user_id: int) -> dict[str, Any]:
        user = self.dao.find_by_userid(user_id)
        if not user:
            return {"code": 400, "msg": "用户不存在"}
        user_dict = self.dao.model_to_dict(user)
        user_dict.pop("password", None)
        return {"code": 200, "msg": "success", "data": user_dict}
