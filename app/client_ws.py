
# app/client_ws.py
import asyncio, websockets, json, base64
from cryptog2 import generate_key, derive_key_from_password, encrypt_message

async def run(uri, mode="public", value=None, username="Guilherme", room="group:main"):
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"auth": mode, "value": value or "", "room": room}))
        first = json.loads(await ws.recv())
        if first["type"]=="SALT":
            salt = base64.urlsafe_b64decode(first["value"])
            key = derive_key_from_password(value, salt)
            token = encrypt_message(username, key)
            await ws.send(base64.b64encode(token).decode("utf-8"))
        elif first["type"]=="KEY":
            # público/convite: para simplicidade, envia username em claro
            await ws.send(username)

        print("Conectado.")
        async def reader():
            try:
                while True:
                    print(await ws.recv())
            except Exception: pass
        asyncio.create_task(reader())

        while True:
            msg = input()
            if msg=="/quit": break
            await ws.send(msg)

if __name__=="__main__":
    asyncio.run(run("ws://localhost:8000/ws"))
