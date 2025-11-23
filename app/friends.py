
# app/friends.py
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from .db import SessionLocal, Friend, Invite

router = APIRouter(prefix="/friends", tags=["friends"])

@router.get("")
def list_friends(username: str):
    db: Session = SessionLocal()
    try:
        lst = db.query(Friend).filter(Friend.owner==username).all()
        return {"friends": [f.friend for f in lst]}
    finally:
        db.close()

@router.post("/invite")
def invite_friend(owner: str, target: str):
    if owner==target: raise HTTPException(400,"Não convide a si mesmo")
    db: Session = SessionLocal()
    try:
        # salva um "token" de convite de amizade (simples)
        import secrets
        tok = secrets.token_urlsafe(12)
        inv = Invite(token=f"FRIEND:{owner}:{target}:{tok}")
        db.add(inv); db.commit()
        return {"invite": inv.token}
    finally:
        db.close()

@router.post("/accept")
def accept_friend(token: str):
    db: Session = SessionLocal()
    try:
        inv = db.query(Invite).filter(Invite.token==token).first()
        if not inv: raise HTTPException(404,"Convite inválido")
        _, owner, target, _ = inv.token.split(":")
        # cria relação bilateral
        if not db.query(Friend).filter(Friend.owner==owner, Friend.friend==target).first():
            db.add(Friend(owner=owner, friend=target))
        if not db.query(Friend).filter(Friend.owner==target, Friend.friend==owner).first():
            db.add(Friend(owner=target, friend=owner))
        db.delete(inv); db.commit()
        return {"ok": True}
    finally:
        db.close()
