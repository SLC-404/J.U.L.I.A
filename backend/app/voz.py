"""
Asistente de voz de J.U.L.I.A. -- todo local (la voz de la Lic. y los datos
de los clientes no salen de la computadora). Funciona igual en Mac y en
Windows 11.

- Oido (voz -> texto): Whisper "small" via faster-whisper. Se le da una
  "pista" con los nombres y terminos del caso (cliente, causante, juzgado,
  "apersonamiento"...): sin pista escribia nombres propios mal (apellidos, "Tiandistenco");
  con pista, bien.
- Voz (texto -> voz): Chatterbox multilingue (la mas humana; la eligio
  Cesar, oct 2026). Clona el acento mexicano de `modelos_voz/voz_julia.wav`
  (si no existe, se arma con Piper; se puede cambiar por una grabacion de
  ~10 s de cualquier voz). Es lenta: en la Mac M5 tarda ~1.4x lo que dura el
  audio con GPU y ~2.3x en CPU; por eso el navegador pide frase por frase
  (empieza a hablar con la primera mientras se genera la siguiente).
  Piper (es_MX-claude-high) queda de respaldo: si Chatterbox no esta
  instalado o falla, habla Piper. VOZ_MOTOR=piper fuerza Piper.

Los modelos viven en backend/modelos_voz/ (no van a git). Si no estan, se
bajan solos la primera vez que se usan (necesita internet esa unica vez):
Whisper small ~460 MB, voz de Piper ~60 MB, Chatterbox ~3 GB.
"""

import io
import os
import re
import threading
import wave
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODELOS = BASE_DIR / "modelos_voz"
WHISPER_MODELO = os.getenv("WHISPER_MODELO", "small")
VOZ_PIPER = os.getenv("VOZ_PIPER", "es_MX-claude-high")
VOZ_MOTOR = os.getenv("VOZ_MOTOR", "chatterbox")  # "chatterbox" o "piper"
VOZ_REFERENCIA = MODELOS / "voz_julia.wav"

_lock_whisper = threading.Lock()
_lock_piper = threading.Lock()
_lock_chatterbox = threading.Lock()
_lock_carga_chatterbox = threading.Lock()
_whisper = None
_piper = None
_chatterbox = None
_chatterbox_error: str | None = None  # si fallo al cargar, no se reintenta en cada frase


def _certificados() -> None:
    # El Python de python.org en Mac no trae certificados raiz y las
    # descargas por HTTPS fallaban; certifi los trae.
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass


def _modelo_whisper():
    global _whisper
    if _whisper is None:
        _certificados()
        from faster_whisper import WhisperModel

        _whisper = WhisperModel(
            WHISPER_MODELO, device="cpu", compute_type="int8", download_root=str(MODELOS / "whisper")
        )
    return _whisper


def _voz_piper():
    global _piper
    if _piper is None:
        from piper import PiperVoice

        onnx = MODELOS / "piper" / f"{VOZ_PIPER}.onnx"
        if not onnx.exists():
            _certificados()
            import subprocess
            import sys

            (MODELOS / "piper").mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [sys.executable, "-m", "piper.download_voices", "--download-dir", str(MODELOS / "piper"), VOZ_PIPER],
                check=True,
            )
        _piper = PiperVoice.load(str(onnx))
    return _piper


def _dispositivo() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"  # GPU de la Mac
    return "cpu"  # la laptop de la Lic. (Windows, sin tarjeta de video)


def _modelo_chatterbox():
    """Chatterbox ya listo con la voz de J.U.L.I.A.; None si no se puede usar."""
    global _chatterbox, _chatterbox_error
    if _chatterbox is not None or _chatterbox_error is not None or VOZ_MOTOR != "chatterbox":
        return _chatterbox
    with _lock_carga_chatterbox:
        if _chatterbox is not None or _chatterbox_error is not None:
            return _chatterbox
        try:
            _certificados()
            from huggingface_hub import snapshot_download
            from chatterbox.mtl_tts import REPO_ID, ChatterboxMultilingualTTS

            carpeta = snapshot_download(
                repo_id=REPO_ID,
                cache_dir=str(MODELOS / "chatterbox"),
                allow_patterns=["ve.pt", "t3_mtl23ls_v2.safetensors", "s3gen.pt",
                                "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"],
            )
            modelo = ChatterboxMultilingualTTS.from_local(carpeta, _dispositivo())
            if not VOZ_REFERENCIA.exists():
                # Sin muestra, Chatterbox habla con acento gringo: se le da
                # la voz mexicana de Piper para que copie el acento.
                VOZ_REFERENCIA.write_bytes(_hablar_piper(
                    "Buenos días, licenciada. Soy Julia. Ya revisé el escrito del juicio sucesorio "
                    "y te leo los cambios que hice en los hechos y en el derecho, para que me digas si quedó bien."
                ))
            modelo.prepare_conditionals(str(VOZ_REFERENCIA))
            _chatterbox = modelo
        except Exception as e:  # sin Chatterbox se sigue con Piper
            _chatterbox_error = f"{type(e).__name__}: {e}"
            print(f"[voz] Chatterbox no disponible, se usa Piper: {_chatterbox_error}")
    return _chatterbox


def precargar() -> None:
    """Carga Whisper y Chatterbox en segundo plano (al entrar al modo voz),
    para que la primera frase no espere la carga."""
    def _cargar():
        try:
            _modelo_whisper()
        except Exception as e:
            print(f"[voz] no se pudo precargar Whisper: {e}")
        _modelo_chatterbox()

    threading.Thread(target=_cargar, daemon=True).start()


def estado() -> dict:
    return {
        "motor": "chatterbox" if _chatterbox is not None else ("piper" if _chatterbox_error or VOZ_MOTOR == "piper" else "chatterbox (sin cargar)"),
        "chatterbox_error": _chatterbox_error,
        "whisper_descargado": (MODELOS / "whisper").exists() and any((MODELOS / "whisper").iterdir()),
        "voz_descargada": (MODELOS / "piper" / f"{VOZ_PIPER}.onnx").exists(),
        "whisper_cargado": _whisper is not None,
        "voz_cargada": _piper is not None,
    }


# --- Voz -> texto ------------------------------------------------------------------

def _wav_a_numpy(datos: bytes, sr_destino: int = 16000) -> np.ndarray:
    """WAV (lo que manda el navegador) -> audio float32 mono a 16 kHz."""
    with wave.open(io.BytesIO(datos)) as w:
        sr, canales, ancho = w.getframerate(), w.getnchannels(), w.getsampwidth()
        crudo = w.readframes(w.getnframes())
    if ancho != 2:
        raise ValueError("se esperaba audio de 16 bits")
    x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0
    if canales > 1:
        x = x.reshape(-1, canales).mean(axis=1)
    if sr != sr_destino and len(x):
        t = np.arange(0, len(x) / sr, 1 / sr_destino)
        x = np.interp(t, np.arange(len(x)) / sr, x).astype(np.float32)
    return x


def transcribir(wav: bytes, pista: str = "") -> str:
    audio = _wav_a_numpy(wav)
    if len(audio) < 16000 * 0.3:  # menos de 0.3 s: ruido
        return ""
    with _lock_whisper:
        segmentos, _ = _modelo_whisper().transcribe(
            audio, language="es", initial_prompt=pista or None, vad_filter=True, beam_size=5
        )
        texto = " ".join(s.text.strip() for s in segmentos).strip()
    # Whisper a veces "alucina" frases tipicas de subtitulos con silencio.
    if re.fullmatch(r"(?i)\W*(gracias( por ver)?|subt[ií]tulos.*|amara\.org.*)\W*", texto):
        return ""
    return texto


# --- Texto -> voz ------------------------------------------------------------------

_LECTURA = [
    (r"\bLIC\.\s*", "licenciada "), (r"\bLICS\.\s*", "licenciados "), (r"\bC\.\s*JUEZ", "ciudadano juez"),
    (r"\bNo\.\s*", "número "), (r"\bart\.\s*", "artículo "), (r"(\d+)\s*/\s*(\d+)", r"\1 diagonal \2"),
    (r"\bP\s*R\s*E\s*S\s*E\s*N\s*T\s*E\b", "presente"), (r"\bH\s*E\s*C\s*H\s*O\s*S\b", "hechos"),
    (r"\bD\s*E\s*R\s*E\s*C\s*H\s*O\b", "derecho"), (r"(\d)\.-", r"\1."), (r"\bV\.\s*S\.", "versus"),
    (r"\[([^\]]+)\]", r"falta: \1"), (r"#", "número "), (r"\bEDO\.?\s*MEX\.?", "Estado de México"),
]


def preparar_para_leer(texto: str) -> str:
    """Que suene natural: 'LIC.' -> 'licenciada', '123/2026' -> '123 diagonal
    2026', 'H E C H O S' -> 'hechos', y las MAYUSCULAS en tipo oracion (Piper
    deletrea algunas palabras en mayusculas)."""
    for patron, cambio in _LECTURA:
        texto = re.sub(patron, cambio, texto)

    def suavizar(m: re.Match) -> str:
        w = m.group(0)
        return w.capitalize() if len(w) > 3 else w.lower()

    return re.sub(r"\b[A-ZÁÉÍÓÚÑ]{2,}\b", suavizar, texto)


def _numeros_en_letra(texto: str) -> str:
    """Chatterbox se traba con cifras: '6.142' -> 'seis punto ciento cuarenta
    y dos', '23' -> 'veintitres'. (Piper si las lee solo.)"""
    from num2words import num2words

    texto = re.sub(r"(\d),(\d{3})\b", r"\1\2", texto)  # 3,000 -> 3000
    texto = re.sub(r"\$\s*(\d+)(?:\.00)?", r"\1 pesos", texto)

    def letra(m: re.Match) -> str:
        return " punto ".join(num2words(int(p), lang="es") for p in m.group(0).split("."))

    return re.sub(r"\d+(?:\.\d+)*", letra, texto)


def _a_wav(pcm16: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm16.tobytes())
    return buf.getvalue()


def _hablar_piper(texto: str) -> bytes:
    buf = io.BytesIO()
    with _lock_piper:
        voz = _voz_piper()
        with wave.open(buf, "wb") as w:
            voz.synthesize_wav(texto, w)
    return buf.getvalue()


def _hablar_chatterbox(modelo, texto: str) -> bytes:
    texto = _numeros_en_letra(texto)
    with _lock_chatterbox:
        audio = modelo.generate(texto, language_id="es")
    pcm = (audio.squeeze().cpu().numpy().clip(-1, 1) * 32767).astype(np.int16)
    return _a_wav(pcm, modelo.sr)


def hablar(texto: str) -> bytes:
    """WAV con la voz de J.U.L.I.A. leyendo `texto` (una frase o un parrafo
    corto: el navegador manda los textos largos en pedazos)."""
    texto = preparar_para_leer(texto)
    modelo = _modelo_chatterbox()
    if modelo is not None:
        try:
            return _hablar_chatterbox(modelo, texto)
        except Exception as e:
            print(f"[voz] Chatterbox fallo en esta frase, se usa Piper: {e}")
    return _hablar_piper(texto)
