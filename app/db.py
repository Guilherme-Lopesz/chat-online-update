
# app/db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = DeclarativeBase()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Friend(Base):
    __tablename__ = "friends"
    id = Column(Integer, primary_key=True)
    owner = Column(String(32), index=True, nullable=False)
    friend = Column(String(32), index=True, nullable=False)

class Invite(Base):
    __tablename__ = "invites"
    id = Column(Integer, primary_key=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True)
    filename = Column(String(256))
    mimetype = Column(String(64))
    size = Column(Integer)
    data = Column(LargeBinary)      # BLOB
    created_by = Column(String(32), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    kind = Column(String(16))       # "image" | "video" | "audio" | "file"

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    author = Column(String(32), index=True)
    room = Column(String(64), index=True)   # "group:<name>" ou "dm:<u1>:<u2>"
    content = Column(Text)                  # opcional: armazenar texto
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
