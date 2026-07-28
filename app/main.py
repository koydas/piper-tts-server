import io
import wave

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from piper import PiperVoice

MODEL_PATH = "/models/fr_FR-siwis-medium.onnx"

app = FastAPI()
voice = PiperVoice.load(MODEL_PATH, use_cuda=False)


class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
def tts(req: TTSRequest):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(req.text, wav_file)
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
