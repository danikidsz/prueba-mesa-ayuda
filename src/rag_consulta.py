"""
rag_consulta.py
Pasos 3, 4 y 5 del RAG: recuperar los fragmentos relevantes a una
pregunta y generar una respuesta fundamentada, o declarar que no hay
evidencia.

Comportamiento de abstencion (punto critico #6 del enunciado): el corpus
de politicas NO cubre todos los temas, y eso es intencional. Aqui se
aplican dos barreras:
  1. Umbral de similitud: si el mejor fragmento no supera UMBRAL_MINIMO,
     ni siquiera se llama al modelo -- se responde "no tengo evidencia".
  2. Instruccion explicita en el prompt: el modelo debe responder
     UNICAMENTE con los fragmentos entregados y declarar cuando no
     alcanzan.

Ejecucion:
    python3 -m src.rag_consulta "¿con cuanta anticipacion pido vacaciones?"
"""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.rag_ingesta import calcular_embedding

load_dotenv()

RUTA_INDICE = Path("data/processed/indice_politicas.json")
API_KEY = os.getenv("IA_PROVIDER_API_KEY", "")
MODELO = "gemini-3.6-flash"
URL_MODELO = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"
)

FRAGMENTOS_A_RECUPERAR = 3
UMBRAL_MINIMO = 0.60  # similitud por debajo de esto = sin evidencia suficiente

MENSAJE_SIN_EVIDENCIA = (
    "No tengo evidencia en las políticas disponibles para responder esa "
    "pregunta. Le sugiero consultar directamente con el área responsable."
)

_indice_cache = None


def cargar_indice():
    global _indice_cache
    if _indice_cache is None:
        if not RUTA_INDICE.exists():
            raise SystemExit(
                f"No existe {RUTA_INDICE}. Ejecute primero: python3 -m src.rag_ingesta"
            )
        with open(RUTA_INDICE, encoding="utf-8") as f:
            _indice_cache = json.load(f)
    return _indice_cache


def similitud_coseno(a, b):
    """Similitud coseno entre dos vectores, sin dependencias externas."""
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = sum(x * x for x in a) ** 0.5
    norma_b = sum(y * y for y in b) ** 0.5
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return producto / (norma_a * norma_b)


def recuperar(pregunta, k=FRAGMENTOS_A_RECUPERAR):
    """Devuelve los k fragmentos mas similares a la pregunta, con su puntaje."""
    indice = cargar_indice()
    vector_pregunta = calcular_embedding(pregunta)

    puntuados = [
        (similitud_coseno(vector_pregunta, f["embedding"]), f) for f in indice
    ]
    puntuados.sort(key=lambda par: par[0], reverse=True)
    return puntuados[:k]


def responder(pregunta):
    """
    Responde la pregunta con base en las politicas, o declara que no
    tiene evidencia.

    Devuelve un diccionario con la respuesta, las fuentes citadas, si
    hubo abstencion y la similitud del mejor fragmento (para observar
    el comportamiento del umbral).
    """
    recuperados = recuperar(pregunta)
    if not recuperados:
        return {
            "respuesta": MENSAJE_SIN_EVIDENCIA,
            "fuentes": [],
            "abstuvo": True,
            "similitud_maxima": 0.0,
        }

    mejor_similitud = recuperados[0][0]

    # Barrera 1: sin evidencia suficientemente cercana, no se llama al modelo
    if mejor_similitud < UMBRAL_MINIMO:
        return {
            "respuesta": MENSAJE_SIN_EVIDENCIA,
            "fuentes": [],
            "abstuvo": True,
            "similitud_maxima": round(mejor_similitud, 3),
        }

    contexto = "\n\n---\n\n".join(
        f"[{f['documento']} — sección {f['seccion']}]\n{f['texto_limpio']}"
        for _, f in recuperados
    )

    # Barrera 2: instruccion explicita de no inventar
    prompt = (
        "Eres un asistente de la mesa de ayuda de La Fortuna S.A. Responde "
        "la pregunta del colaborador UNICAMENTE con la información de los "
        "fragmentos de política entregados abajo.\n\n"
        "Reglas estrictas:\n"
        "- Si los fragmentos no contienen la respuesta, responde exactamente: "
        f"\"{MENSAJE_SIN_EVIDENCIA}\"\n"
        "- No uses conocimiento externo ni supongas datos que no estén escritos.\n"
        "- Cita el documento y la sección de donde tomaste cada dato.\n"
        "- Sé breve y concreto.\n\n"
        f"FRAGMENTOS:\n{contexto}\n\n"
        f"PREGUNTA: {pregunta}\n\nRESPUESTA:"
    )

    r = requests.post(
        URL_MODELO,
        json={"contents": [{"parts": [{"text": prompt}]}]},
        headers={"x-goog-api-key": API_KEY},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Error {r.status_code} del proveedor: {r.text[:200]}")

    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    abstuvo = MENSAJE_SIN_EVIDENCIA[:40].lower() in texto.lower()

    return {
        "respuesta": texto,
        "fuentes": [
            {
                "documento": f["documento"],
                "seccion": f["seccion"],
                "similitud": round(s, 3),
            }
            for s, f in recuperados
        ]
        if not abstuvo
        else [],
        "abstuvo": abstuvo,
        "similitud_maxima": round(mejor_similitud, 3),
    }


if __name__ == "__main__":
    pregunta = (
        " ".join(sys.argv[1:])
        or "¿Con cuánta anticipación debo solicitar mis vacaciones?"
    )
    resultado = responder(pregunta)

    print(f"\nPREGUNTA: {pregunta}\n")
    print(f"RESPUESTA:\n{resultado['respuesta']}\n")
    if resultado["fuentes"]:
        print("FUENTES:")
        for f in resultado["fuentes"]:
            print(f"  - {f['documento']} · {f['seccion']} (similitud {f['similitud']})")
    print(f"\nabstuvo: {resultado['abstuvo']} · similitud máxima: {resultado['similitud_maxima']}")