import random
import smtplib
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config.app_config import settings


def gen_email_code(length: int = 6) -> str:
    chars = random.sample(string.ascii_letters + string.digits, length)
    return "".join(chars)


def send_email(to_email: str, code: str):
    email_name = settings.email_name
    passwd = settings.email_passwd
    content = f"""
    注册验证码是:<h1 style='color:red'>{code}</h1>
    """
    msg = MIMEMultipart()
    msg["Subject"] = "注册验证码"
    msg["From"] = email_name
    msg["To"] = to_email
    msg.attach(MIMEText(content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as s:
        s.login(email_name, passwd)
        s.sendmail(email_name, to_email, msg.as_string())
