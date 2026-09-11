from typing import Optional

from pydantic import BaseModel


class UserLoginRes(BaseModel):
    user_id: int
    username: str
    nickname: str
    picture: str


class UserRegisterRes(BaseModel):
    user_id: int
    username: str
    nickname: str
