"""
Upload Service — Cloudflare R2 backend

環境變數（必填）：
  R2_ACCOUNT_ID       Cloudflare Account ID
  R2_ACCESS_KEY_ID    R2 API Token Access Key
  R2_SECRET_ACCESS_KEY R2 API Token Secret Key
  R2_BUCKET_NAME      Bucket 名稱
  R2_PUBLIC_URL       Public bucket URL，例如 https://pub-xxxx.r2.dev

若環境變數未設定，fallback 到本地 static/uploads（僅供本機開發）。
"""
import os
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_BYTES = 16 * 1024 * 1024  # 16 MB

LOGO_ALLOWED_EXTENSIONS = {'png', 'svg', 'webp', 'jpg', 'jpeg'}
LOGO_MAX_BYTES = 4 * 1024 * 1024  # 4 MB


def _ext(filename: str) -> str:
    return Path(filename).suffix.lstrip('.').lower()


def allowed_file(filename: str) -> bool:
    return _ext(filename) in ALLOWED_EXTENSIONS


# ── R2 client ───────────────────────────────────────────────────────────────

def _r2_client():
    """回傳 boto3 S3 client（指向 R2），若未設定環境變數則回傳 None。"""
    account_id  = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key  = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key  = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    if not (account_id and access_key and secret_key):
        return None
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def _r2_bucket() -> str:
    return os.getenv("R2_BUCKET_NAME", "").strip()


def _r2_public_url() -> str:
    return os.getenv("R2_PUBLIC_URL", "").rstrip("/")


def _use_r2() -> bool:
    return bool(_r2_client() and _r2_bucket() and _r2_public_url())


# ── Local fallback（開發用） ─────────────────────────────────────────────────

def _upload_dir(event_id: int) -> Path:
    base = Path(current_app.root_path) / 'static' / 'uploads' / 'events' / str(event_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── 核心：儲存圖片 ───────────────────────────────────────────────────────────

def save_hero_image(file, event_id: int, slot: str, prefix: str = "hero") -> str:
    """
    slot:   'desktop' | 'tablet' | 'mobile'
    prefix: 'hero' 或 'landing'
    returns: public URL
    """
    if not file or not file.filename:
        raise ValueError("未選擇檔案")

    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支援的格式：{ext}，請使用 jpg / png / webp")

    if slot not in ('desktop', 'tablet', 'mobile'):
        raise ValueError(f"無效的 slot：{slot}")

    content = file.read()
    if len(content) > MAX_BYTES:
        raise ValueError(f"檔案過大（{len(content)//1024//1024} MB），上限 16 MB")

    filename = f"{prefix}-{slot}.{ext}"
    key = f"events/{event_id}/{filename}"

    if _use_r2():
        client = _r2_client()
        content_type = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'webp': 'image/webp',
        }.get(ext, 'application/octet-stream')

        # 先刪舊檔（同 slot 不同副檔名）
        _delete_r2_slot(event_id, slot, prefix)

        client.put_object(
            Bucket=_r2_bucket(),
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return f"{_r2_public_url()}/{key}"
    else:
        logger.warning("R2 未設定，fallback 到本地儲存")
        delete_hero_image(event_id, slot, prefix=prefix)
        dest = _upload_dir(event_id) / filename
        with open(dest, 'wb') as f:
            f.write(content)
        return f"/static/uploads/events/{event_id}/{filename}"


def delete_hero_image(event_id: int, slot: str, prefix: str = "hero") -> None:
    """刪除指定 slot 圖片（R2 或本地）"""
    if _use_r2():
        _delete_r2_slot(event_id, slot, prefix)
    else:
        for ext in ALLOWED_EXTENSIONS:
            path = _upload_dir(event_id) / f"{prefix}-{slot}.{ext}"
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _delete_r2_slot(event_id: int, slot: str, prefix: str) -> None:
    client = _r2_client()
    if not client:
        return
    for ext in ALLOWED_EXTENSIONS:
        key = f"events/{event_id}/{prefix}-{slot}.{ext}"
        try:
            client.delete_object(Bucket=_r2_bucket(), Key=key)
        except Exception:
            pass


# ── Logo ────────────────────────────────────────────────────────────────────

def save_logo_image(file, event_id: int) -> str:
    if not file or not file.filename:
        raise ValueError("未選擇檔案")
    ext = _ext(file.filename)
    if ext not in LOGO_ALLOWED_EXTENSIONS:
        raise ValueError(f"不支援的格式：{ext}，請使用 png / svg / webp / jpg")

    content = file.read()
    if len(content) > LOGO_MAX_BYTES:
        raise ValueError(f"檔案過大（{len(content)//1024} KB），Logo 上限 4 MB")

    filename = f"logo.{ext}"
    key = f"events/{event_id}/{filename}"

    if _use_r2():
        content_type = {
            'png': 'image/png', 'svg': 'image/svg+xml',
            'webp': 'image/webp', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        }.get(ext, 'application/octet-stream')
        _delete_r2_logo(event_id)
        _r2_client().put_object(
            Bucket=_r2_bucket(),
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return f"{_r2_public_url()}/{key}"
    else:
        logger.warning("R2 未設定，fallback 到本地儲存")
        _delete_local_logo(event_id)
        dest = _upload_dir(event_id) / filename
        with open(dest, 'wb') as f:
            f.write(content)
        return f"/static/uploads/events/{event_id}/{filename}"


def delete_logo_image(event_id: int) -> None:
    if _use_r2():
        _delete_r2_logo(event_id)
    else:
        _delete_local_logo(event_id)


def _delete_r2_logo(event_id: int) -> None:
    client = _r2_client()
    if not client:
        return
    for ext in LOGO_ALLOWED_EXTENSIONS:
        try:
            client.delete_object(Bucket=_r2_bucket(), Key=f"events/{event_id}/logo.{ext}")
        except Exception:
            pass


def _delete_local_logo(event_id: int) -> None:
    for ext in LOGO_ALLOWED_EXTENSIONS:
        path = _upload_dir(event_id) / f"logo.{ext}"
        try:
            path.unlink()
        except FileNotFoundError:
            pass
