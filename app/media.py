
# app/media.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
import mimetypes
from .db import SessionLocal, Media

router = APIRouter(prefix="/media", tags=["media"])

IMAGE_EXTS = {".png",".jpg",".jpeg",".gif",".bmp",".webp"}
VIDEO_EXTS = {".mp4",".mov",".mkv",".webm",".avi"}

@router.post("/upload")
async def upload_media(file: UploadFile = File(...), username: str = Form("Anon")):
    ext = "." + file.filename.rsplit(".",1)[-1].lower() if "." in file.filename else ""
    mt = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    kind = "image" if ext in IMAGE_EXTS else ("video" if ext in VIDEO_EXTS else "file")
    data = await file.read()
    db: Session = SessionLocal()
    try:
        m = Media(filename=file.filename, mimetype=mt, size=len(data), data=data, created_by=username, kind=kind)
        db.add(m); db.commit(); db.refresh(m)
        # retorna URL pública do backend
        return {"id": m.id, "url": f"/media/{m.id}", "kind": kind, "name": file.filename, "size": m.size}
    finally:
        db.close()

@router.get("/{media_id}")
def get_media(media_id: int):
    db: Session = SessionLocal()
    try:
        m = db.query(Media).get(media_id)
        if not m: raise HTTPException(404, "Media não encontrada")
        return Response(content=m.data, media_type=m.mimetype)
    finally:
        db.close()
