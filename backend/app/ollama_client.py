"""
Capa delgada sobre Ollama. Es la UNICA parte del codigo que sabe que el
modelo de IA es Ollama -- si algun dia cambias de proveedor, solo tocas
este archivo.
"""

import os

import ollama

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
# qwen3.5:9b: en las pruebas con escritos reales del despacho siguio el
# formato de la Lic. Juana; llama3.1:8b se negaba a redactar escritos
# legales cuando le pasabamos un escrito de ejemplo.
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# Cuanto texto puede "leer" el modelo a la vez (en tokens). El default de
# Ollama es chico y cortaba en silencio el principio del contexto (las
# instrucciones, los escritos de ejemplo). 16k cabe bien en una Mac de 16 GB
# con llama3.1:8b.
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

# Mas bajo = mas apegado al modelo y a los datos, menos "creativo". Con el
# default (0.8) a veces escribia frases sin sentido en escritos largos.
TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))

_client = ollama.Client(host=OLLAMA_HOST)


def chat(messages: list[dict], temperatura: float | None = None) -> str:
    """
    messages: lista de {"role": "system"|"user"|"assistant", "content": str}
    Regresa el texto completo de la respuesta (sin streaming por ahora).
    """
    extra = {}
    if MODEL_NAME.startswith("qwen"):
        # Qwen "piensa en voz alta" antes de responder; eso duplica el tiempo
        # y no aporta para redactar. Se apaga.
        extra["think"] = False
    response = _client.chat(
        model=MODEL_NAME, messages=messages, options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE if temperatura is None else temperatura}, **extra
    )
    return response["message"]["content"]
