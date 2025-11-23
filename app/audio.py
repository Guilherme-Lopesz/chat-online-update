
# app/audio.py
from fastapi import APIRouter, UploadFile, File, Form
from sqlalchemy.orm import Session
import wave, os
from .db import SessionLocal, Media
from .main import ws_broadcast_text  # chamaremos a função de broadcast

router = APIRouter(prefix="/audio", tags=["audio"])

def transcribe_audio_wav(path: str) -> str:
    # Tenta Vosk; fallback SpeechRecognition (PocketSphinx/Google)
    try:
        from vosk import Model, KaldiRecognizer
        import json
        mpath = os.environ.get("VOSK_MODEL_PATH", "")
        if not mpath or not os.path.isdir(mpath):
            raise RuntimeError("VOSK_MODEL_PATH ausente")
        wf = wave.open(path, "rb")
        rec = KaldiRecognizer(Model(mpath), wf.getframerate()); rec.SetWords(True)
        parts=[]
        while True:
            data=wf.readframes(4000)
            if len(data)==0: break
            if rec.AcceptWaveform(data):
                res=json.loads(rec.Result()); parts.append(res.get("text",""))
        final=json.loads(rec.FinalResult()); parts.append(final.get("text",""))
        wf.close()
        txt=" ".join(t.strip() for t in parts).strip()
        return txt or "(sem áudio reconhecível)"
    except Exception as e:
        try:
            import speech_recognition as sr
            r=sr.Recognizer()
            with sr.AudioFile(path) as source:
                audio=r.record(source)
            try: return r.recognize_sphinx(audio)
            except Exception:
                return r.recognize_google(audio)
        except Exception as e2:
            return f"Falha na transcrição: {e2}"

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), username: str = Form("Anon"), room: str = Form("group:main")):
    # Aceita .wav (recomendado). Para outros formatos, o cliente pode converter.
    tmp = f"/tmp/{file.filename}"
    data = await file.read()
    with open(tmp,"wb") as f: f.write(data)
    text = transcribe_audio_wav(tmp)
    # Salva como media (áudio) para ter URL também
    db: Session = SessionLocal()
    try:
        m = Media(filename=file.filename, mimetype="audio/wav", size=len(data), data=data, created_by=username, kind="audio")
        db.add(m); db.commit(); db.refresh(m)
        # Broadcast no WS (grupo ou DM)
        await ws_broadcast_text(room, f"[Transcrição] <{username}> '{file.filename}': {text}")
        return {"text": text, "media_id": m.id, "url": f"/media/{m.id}"}
    finally:
        db.close()
        try: os.remove(tmp)
        except Exception: pass
