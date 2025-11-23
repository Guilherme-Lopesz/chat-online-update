
# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Session
import json, os, base64, secrets
from .db import init_db, SessionLocal, Invite, Friend, User, Message
from .cryptog2 import generate_key, derive_key_from_password, encrypt_message, decrypt_message
from .media import router as media_router
from .audio import router as audio_router
from .friends import router as friends_router

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(media_router)
app.include_router(audio_router)
app.include_router(friends_router)
init_db()

# ===== Estado de conexões =====
connections = {}   # ws -> {"username": str, "room": str, "mode":"group"/"dm", "dm_peer": str|None, "key": bytes}
users_ws = {}      # username -> ws
PUBLIC_KEY = generate_key()
PRIVATE_SALT = os.urandom(16)  # por sala privada (demo)

# ===== Helpers =====
async def ws_send(ws: WebSocket, payload: dict):
    await ws.send_text(json.dumps(payload, ensure_ascii=False))

async def ws_broadcast_text(room: str, text: str, skip_ws: WebSocket | None = None):
    for ws, info in list(connections.items()):
        if info.get("room")==room and ws is not skip_ws:
            try: await ws.send_text(text)
            except Exception:
                try: await ws.close()
                except: pass
                connections.pop(ws, None)

def save_message(author: str, room: str, text: str):
    db: Session = SessionLocal()
    try:
        db.add(Message(author=author, room=room, content=text))
        db.commit()
    finally:
        db.close()

def is_friend(a: str, b: str) -> bool:
    db: Session = SessionLocal()
    try:
        return db.query(Friend).filter(Friend.owner==a, Friend.friend==b).first() is not None
    finally:
        db.close()

# ===== WebSocket =====
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    key_in_use = PUBLIC_KEY  # default público
    room = "group:main"
    username = "Anon"

    try:
        # 1) Handshake inicial: cliente envia {"auth":"public|password|invite", "value": "...", "room": "..."}
        init_raw = await ws.receive_text()
        init = json.loads(init_raw)
        auth = init.get("auth","public")
        room = init.get("room", room)

        if auth == "password":
            # privado: devolve SALT e deriva a key depois
            salt_b64 = base64.urlsafe_b64encode(PRIVATE_SALT).decode("utf-8")
            await ws_send(ws, {"type":"SALT", "value": salt_b64})
            # agora receber username cifrado com fernet(PBKDF2)
            enc_user_b64 = await ws.receive_text()
            enc_user = base64.b64decode(enc_user_b64)
            key_in_use = derive_key_from_password(init.get("value","senha"), PRIVATE_SALT)
            username = decrypt_message(enc_user, key_in_use, as_text=True).strip() or "Anon"
        elif auth == "invite":
            # token: valida e entrega KEY pública
            db: Session = SessionLocal()
            ok = False
            try:
                token = init.get("value","")
                i = db.query(Invite).filter(Invite.token==token).first()
                if i:
                    db.delete(i); db.commit(); ok = True
            finally:
                db.close()
            if not ok:
                await ws_send(ws, {"type":"FAIL", "reason":"invite inválido"}); await ws.close(); return
            await ws_send(ws, {"type":"KEY", "value": PUBLIC_KEY.decode("utf-8")})
            # cliente envia username cifrado com PUBLIC_KEY (opcional) ou em texto
            user_raw = await ws.receive_text()
            username = user_raw.strip() or "Anon"
        else:
            # público: entrega KEY (didático) e recebe username
            await ws_send(ws, {"type":"KEY", "value": PUBLIC_KEY.decode("utf-8")})
            user_raw = await ws.receive_text()
            username = user_raw.strip() or "Anon"

        # registrar user
        connections[ws] = {"username": username, "room": room, "mode":"group", "dm_peer": None, "key": key_in_use}
        users_ws[username] = ws

        await ws_broadcast_text(room, f"● <{username}> entrou no chat", skip_ws=ws)
        save_message(username, room, "[join]")

        # 2) Loop de mensagens (comandos simples)
        while True:
            data = await ws.receive_text()
            msg = data.strip()

            # MODE DM
            if msg.startswith("/dm "):
                peer = msg.split(" ",1)[1].strip()
                if not is_friend(username, peer):
                    await ws.send_text(f"[Sistema] '{peer}' não é seu amigo. Use /friends e /friend invite/accept.")
                    continue
                connections[ws]["mode"]="dm"; connections[ws]["dm_peer"]=peer
                await ws.send_text(f"[Sistema] DM com {peer} ativado."); continue

            if msg.strip()=="/dm off":
                connections[ws]["mode"]="group"; connections[ws]["dm_peer"]=None
                await ws.send_text("[Sistema] Saiu do modo DM; voltou ao grupo."); continue

            # FRIENDS básicos (atalhos HTTP existem em /friends)
            if msg.strip()=="/friends":
                db: Session = SessionLocal()
                try:
                    fl = db.query(Friend).filter(Friend.owner==username).all()
                    await ws.send_text("[Sistema] Amigos: " + ", ".join([f.friend for f in fl]) if fl else "(nenhum)")
                finally:
                    db.close()
                continue

            # MEDIA/ÁUDIO (clientes devem chamar HTTP /media/upload e /audio/transcribe e aí WS anuncia)
            if msg.startswith("/say "):
                text = msg.split(" ",1)[1]
                info = connections.get(ws, {})
                if info.get("mode")=="dm" and info.get("dm_peer"):
                    peer = info["dm_peer"]; wpeer = users_ws.get(peer)
                    if wpeer:
                        await wpeer.send_text(f"[DM de {username}] {text}")
                        await ws.send_text(f"[DM para {peer}] {text}")
                        save_message(username, f"dm:{username}:{peer}", text)
                    else:
                        await ws.send_text(f"[Sistema] '{peer}' está offline.")
                else:
                    await ws_broadcast_text(room, f"<{username}> {text}", skip_ws=ws)
                    save_message(username, room, text)
                continue

            # MENSAGENS SIMPLES
            await ws_broadcast_text(room, f"<{username}> {msg}", skip_ws=ws)
            save_message(username, room, msg)

    except WebSocketDisconnect:
        pass
    finally:
        info = connections.pop(ws, None)
        if info:
            users_ws.pop(info["username"], None)
            await ws_broadcast_text(info["room"], f"<{info['username']}> saiu do chat")
