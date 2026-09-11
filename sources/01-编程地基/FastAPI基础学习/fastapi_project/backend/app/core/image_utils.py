import os
import time
from pathlib import Path

from PIL import Image

from app.config.app_config import settings


def ensure_upload_dir():
    upload_path = settings.upload_dir_abs
    upload_path.mkdir(parents=True, exist_ok=True)


def compress_image(source: str, dest: str, max_width: int = 1200):
    ensure_upload_dir()
    im = Image.open(source)

    # 统一输出 jpg：若原图带透明通道（RGBA/P 等），先转成 RGB
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")

    x, y = im.size

    # Pillow 10+ 移除了 Image.ANTIALIAS，改用 Resampling.LANCZOS
    try:
        resample = Image.Resampling.LANCZOS  # Pillow>=9
    except AttributeError:  # pragma: no cover
        resample = Image.LANCZOS  # Pillow<9

    if x > max_width:
        ys = int(y * max_width / x)
        xs = max_width
        temp = im.resize((xs, ys), resample)
        temp.save(dest, quality=80, optimize=True)
    else:
        im.save(dest, quality=80, optimize=True)


def save_upload_file(file_bytes: bytes, suffix: str) -> str:
    ensure_upload_dir()
    filename = f"{time.strftime('%Y%m%d_%H%M%S')}.{suffix}"
    filepath = settings.upload_dir_abs / filename
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return filename
