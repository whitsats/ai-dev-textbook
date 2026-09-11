import os
from pathlib import Path
from typing import Dict

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):

    env: str = "test"

    db_url: str = "mysql+pymysql://root:123456@localhost:3306/shuiwenzhang"
    db_echo: bool = True

    page_count: int = 10

    # 文章头图：数据库里存相对路径，例如 "article/header/xxx.jpg"
    # 对外访问时由后端拼成：/images/{article_image}
    article_header_image_path: str = "/images/"
    user_header_image_path: str = "/images/headers/"

    # 上传目录（相对“项目根目录 fastapi_project”）
    upload_dir: str = "resource/images/article/header"

    @property
    def project_root(self) -> Path:
        # backend/app/config/app_config.py -> backend/app/config -> backend/app -> backend -> fastapi_project
        return Path(__file__).resolve().parents[3]

    @property
    def upload_dir_abs(self) -> Path:
        return self.project_root / self.upload_dir

    email_name: str = ""
    email_passwd: str = ""

    redis_host: str = "localhost"
    redis_port: int = 9379
    redis_password: str = "123456"
    redis_db: int = 2
    redis_decode_responses: bool = True

    jwt_secret_key: str = "fastapi-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24

    label_types: Dict[str, dict] = {
        "recommend": {"name": "全部", "selected": "selected"},
        "auto_test": {"name": "自动化测试", "selected": "no-selected"},
        "python": {"name": "Python", "selected": "no-selected"},
        "java": {"name": "Java", "selected": "no-selected"},
        "function_test": {"name": "功能测试", "selected": "no-selected"},
        "perf_test": {"name": "性能测试", "selected": "no-selected"},
        "funny": {"name": "幽默段子", "selected": "no-selected"},
    }

    article_types: Dict[str, dict] = {
        "recommend": {"name": "请选择", "selected": "selected"},
        "首发": {"name": "首发", "selected": "no-selected"},
        "原创": {"name": "原创", "selected": "no-selected"},
        "其它": {"name": "其它", "selected": "no-selected"},
    }

    article_tags: list = [
        "Html5", "Angular", "JS", "CSS3", "Sass/Less",
        "JAVA", "Python", "Go", "C++", "C#",
        "MySQL", "Oracle", "MongoDB",
        "Android", "Unity 3", "DCocos2d-x",
    ]

    ueditor_config: dict = {
        "initialContent": '<p>我是初始化内容，设不设置都可以</p>',
        "initialFrameWidth": 700,
        "focus": True,
        "imageActionName": "image",
        "imageFieldName": "file",
        "imageMaxSize": 10485760,
        "imageAllowFiles": [".jpg", ".png", ".jpeg"],
        "imageCompressEnable": True,
        "imageCompressBorder": 5000,
        "imageInsertAlign": "none",
        "imageUrlPrefix": "",
        "scrawlActionName": "crawl",
        "scrawlFieldName": "file",
        "scrawlMaxSize": 10485760,
        "scrawlUrlPrefix": "",
        "scrawlInsertAlign": "none",
        "snapscreenActionName": "snap",
        "snapscreenUrlPrefix": "",
        "snapscreenInsertAlign": "none",
        "catcherLocalDomain": ["127.0.0.1", "localhost"],
        "catcherActionName": "catch",
        "catcherFieldName": "source",
        "catcherUrlPrefix": "",
        "catcherMaxSize": 10485760,
        "catcherAllowFiles": [".jpg", ".png", ".jpeg"],
        "videoActionName": "video",
        "videoFieldName": "file",
        "videoUrlPrefix": "",
        "videoMaxSize": 104857600,
        "videoAllowFiles": [".mp4"],
        "fileActionName": "file",
        "fileFieldName": "file",
        "fileUrlPrefix": "",
        "fileMaxSize": 104857600,
        "fileAllowFiles": [".zip", ".pdf", ".doc"],
        "imageManagerActionName": "listImage",
        "imageManagerListSize": 20,
        "imageManagerUrlPrefix": "",
        "imageManagerInsertAlign": "none",
        "imageManagerAllowFiles": [".jpg", ".png", ".jpeg"],
        "fileManagerActionName": "listFile",
        "fileManagerUrlPrefix": "",
        "fileManagerListSize": 20,
        "fileManagerAllowFiles": [".zip", ".pdf", ".doc"],
        "formulaConfig": {
            "imageUrlTemplate": "https://latex.codecogs.com/svg.image?{}"
        },
    }

    comment_ueditor_config: dict = {
        "initialContent": '<p>请在此发表您的评论</p>',
        "initialFrameWidth": 670,
        "focus": True,
        "imageActionName": "image",
        "imageFieldName": "file",
        "imageMaxSize": 10485760,
        "imageAllowFiles": [".jpg", ".png", ".jpeg"],
        "imageCompressEnable": True,
        "imageCompressBorder": 5000,
        "imageInsertAlign": "none",
        "imageUrlPrefix": "",
        "scrawlActionName": "crawl",
        "scrawlFieldName": "file",
        "scrawlMaxSize": 10485760,
        "scrawlUrlPrefix": "",
        "scrawlInsertAlign": "none",
        "snapscreenActionName": "snap",
        "snapscreenUrlPrefix": "",
        "snapscreenInsertAlign": "none",
        "catcherLocalDomain": ["127.0.0.1", "localhost"],
        "catcherActionName": "catch",
        "catcherFieldName": "source",
        "catcherUrlPrefix": "",
        "catcherMaxSize": 10485760,
        "catcherAllowFiles": [".jpg", ".png", ".jpeg"],
        "videoActionName": "video",
        "videoFieldName": "file",
        "videoUrlPrefix": "",
        "videoMaxSize": 104857600,
        "videoAllowFiles": [".mp4"],
        "fileActionName": "file",
        "fileFieldName": "file",
        "fileUrlPrefix": "",
        "fileMaxSize": 104857600,
        "fileAllowFiles": [".zip", ".pdf", ".doc"],
        "imageManagerActionName": "listImage",
        "imageManagerListSize": 20,
        "imageManagerUrlPrefix": "",
        "imageManagerInsertAlign": "none",
        "imageManagerAllowFiles": [".jpg", ".png", ".jpeg"],
        "fileManagerActionName": "listFile",
        "fileManagerUrlPrefix": "",
        "fileManagerListSize": 20,
        "fileManagerAllowFiles": [".zip", ".pdf", ".doc"],
        "formulaConfig": {
            "imageUrlTemplate": "https://latex.codecogs.com/svg.image?{}"
        },
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AppConfig()
