"""
Hero Image Upload Service

儲存路徑：  app/static/uploads/events/{event_id}/hero-{slot}.{ext}
公開 URL：   /static/uploads/events/{event_id}/hero-{slot}.{ext}
支援格式：  jpg jpeg png webp
最大大小：  16 MB
"""
import os
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_BYTES = 16 * 1024 * 1024  # 16 MB


def _ext(filename: str) -> str:
    return Path(filename).suffix.lstrip('.').lower()


def allowed_file(filename: str) -> bool:
    return _ext(filename) in ALLOWED_EXTENSIONS


def upload_dir(event_id: int) -> Path:
    base = Path(current_app.root_path) / 'static' / 'uploads' / 'events' / str(event_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_hero_image(file, event_id: int, slot: str) -> str:
    """
    slot: 'desktop' | 'tablet' | 'mobile'
    returns: public URL path e.g. '/static/uploads/events/1/hero-desktop.webp'
    raises: ValueError on validation failure
    """
    if not file or not file.filename:
        raise ValueError("未選擇檔案")

    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支援的格式：{ext}，請使用 jpg / png / webp")

    if slot not in ('desktop', 'tablet', 'mobile'):
        raise ValueError(f"無效的 slot：{slot}")

    # 讀取到記憶體先檢查大小
    content = file.read()
    if len(content) > MAX_BYTES:
        raise ValueError(f"檔案過大（{len(content)//1024//1024} MB），上限 16 MB")
    file.seek(0)

    filename = f"hero-{slot}.{ext}"
    dest = upload_dir(event_id) / filename

    # 覆蓋舊檔（同 slot 只保留最新一張）
    with open(dest, 'wb') as f:
        f.write(content)

    return f"/static/uploads/events/{event_id}/{filename}"


def delete_hero_image(event_id: int, slot: str) -> None:
    """刪除指定 slot 的圖片檔案（不拋例外）"""
    for ext in ALLOWED_EXTENSIONS:
        path = upload_dir(event_id) / f"hero-{slot}.{ext}"
        try:
            path.unlink()
        except FileNotFoundError:
            pass


# ── Logo ────────────────────────────────────────────────────────────────────

LOGO_ALLOWED_EXTENSIONS = {'png', 'svg', 'webp', 'jpg', 'jpeg'}
LOGO_MAX_BYTES = 4 * 1024 * 1024  # 4 MB


def save_logo_image(file, event_id: int) -> str:
    """
    儲存活動 Logo。
    路徑：app/static/uploads/events/{event_id}/logo.{ext}
    URL： /static/uploads/events/{event_id}/logo.{ext}
    """
    if not file or not file.filename:
        raise ValueError("未選擇檔案")
    ext = _ext(file.filename)
    if ext not in LOGO_ALLOWED_EXTENSIONS:
        raise ValueError(f"不支援的格式：{ext}，請使用 png / svg / webp / jpg")
    content = file.read()
    if len(content) > LOGO_MAX_BYTES:
        raise ValueError(f"檔案過大（{len(content)//1024} KB），Logo 上限 4 MB")
    file.seek(0)
    # 先刪舊 logo（任何副檔名）
    _delete_logo(event_id)
    filename = f"logo.{ext}"
    dest = upload_dir(event_id) / filename
    with open(dest, 'wb') as f:
        f.write(content)
    return f"/static/uploads/events/{event_id}/{filename}"


def delete_logo_image(event_id: int) -> None:
    _delete_logo(event_id)


def _delete_logo(event_id: int) -> None:
    for ext in LOGO_ALLOWED_EXTENSIONS:
        path = upload_dir(event_id) / f"logo.{ext}"
        try:
            path.unlink()
        except FileNotFoundError:
            pass
