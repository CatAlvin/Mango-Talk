from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.deps import get_db
from app.models import User, Upload
from app.services.uploads import ensure_access, metadata, safe_path

router = APIRouter(prefix="/uploads", tags=["uploads"])
IMAGES = {".png": ("PNG", "image/png"), ".jpg": ("JPEG", "image/jpeg"), ".jpeg": ("JPEG", "image/jpeg"), ".webp": ("WEBP", "image/webp"), ".gif": ("GIF", "image/gif")}
FILES = {".txt", ".md", ".csv", ".json", ".pdf", ".zip", ".7z", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".mp3", ".mp4", ".wav"}


@router.post("", status_code=201)
def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = Path((file.filename or "").replace("\\", "/")).name
    if not name or len(name) > 255 or any(ord(c) < 32 for c in name):
        raise HTTPException(400, "文件名无效")
    extension = Path(name).suffix.lower()
    if extension not in FILES and extension not in IMAGES:
        raise HTTPException(400, "不支持这种文件格式")
    upload_id = uuid4().hex
    root = Path(settings.UPLOAD_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    stored_name = upload_id + extension
    target = root / stored_name
    size = 0
    try:
        with target.open("xb") as handle:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(400, "文件不能超过 50 MB")
                handle.write(chunk)
        if size == 0:
            raise HTTPException(400, "文件内容为空")
        mime = "application/octet-stream"
        kind = "file"
        if extension in IMAGES:
            try:
                with Image.open(target) as picture:
                    if picture.format != IMAGES[extension][0] or picture.width * picture.height > 40_000_000:
                        raise ValueError()
                    picture.verify()
            except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
                raise HTTPException(400, "图片无法读取，请选择有效的图片")
            kind, mime = "image", IMAGES[extension][1]
        upload = Upload(id=upload_id, owner_id=current_user.id, attachment_type=kind, original_name=name, stored_name=stored_name, storage_path=stored_name, mime_type=mime, file_size=size)
        db.add(upload)
        db.commit()
        db.refresh(upload)
        return {"message": "上传成功", "data": metadata(upload, current_user.id)}
    except Exception:
        db.rollback()
        target.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/{upload_id}/access")
def get_access(upload_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "文件不存在")
    ensure_access(db, upload, current_user.id)
    return {"data": metadata(upload, current_user.id)}


@router.get("/{upload_id}/download")
def download(upload_id: str, access_token: str = Query(default=""), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"require_exp": True})
        if payload.get("typ") != "attachment" or payload.get("upload_id") != upload_id:
            raise ValueError()
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "文件链接已过期，请重新打开")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(403, "你没有访问该文件的权限")
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "文件不存在")
    ensure_access(db, upload, user_id)
    inline = upload.attachment_type == "image" and upload.mime_type in {mime for _, mime in IMAGES.values()}
    return FileResponse(safe_path(upload.storage_path), media_type=upload.mime_type if inline else "application/octet-stream", filename=upload.original_name, content_disposition_type="inline" if inline else "attachment", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store", "Content-Security-Policy": "sandbox"})
