
# app/db.py
import os
from datetime import datetime

from sqlalchemy import create_engine, String, Integer, LargeBinary, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Friend(Base):
    __tablename__ = "friends"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    friend: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str | None] = mapped_column(String(256))
    mimetype: Mapped[str | None] = mapped_column(String(64))
    size: Mapped[int | None] = mapped_column(Integer)
    data: Mapped[bytes | None] = mapped_column(LargeBinary)  # BLOB
    created_by: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    kind: Mapped[str | None] = mapped_column(String(16))  # "image" | "video" | "audio" | "file"

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[str | None] = mapped_column(String(32), index=True)
    room: Mapped[str | None] = mapped_column(String(64), index=True)  # "group:<name>" ou "dm:<u1>:<u2>"
    content: Mapped[str | None] = mapped_column(Text)  # opcional: armazenar texto
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
