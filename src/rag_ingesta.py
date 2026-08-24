"""
rag_ingesta.py
Paso 1 y 2 del RAG: leer los PDFs de politicas, partirlos en fragmentos
y calcular sus embeddings.

Decision de fragmentacion declarada: las politicas vienen con secciones
numeradas ("1. Objeto", "2. Autorizacion", ...). Se fragmenta por seccion
en lugar de por cantidad fija de caracteres, porque cada seccion es una
unidad de sentido completa -- eso permite citar "POL-ADM-04 seccion 3" en
la respuesta, que es lo que pide el enunciado, y evita cortar una tabla de
montos por la mitad.

Ejecucion:
    python3 -m src.rag_ingesta
"""
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

RUTA_POLITICAS = Path("docs/politicas")
RUTA_INDICE = Path("data/processed/indice_politicas.json")

API_KEY = os.getenv("IA_PROVIDER_API_KEY", "")
MODELO_EMBEDDING = "gemini-embedding-001"
URL_EMBEDDING = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO_EMBEDDING}:embedContent"
)


def extraer_texto(ruta_pdf):
    """Extrae todo el texto de un PDF, pagina por pagina."""
    lector = PdfReader(str(ruta_pdf))
    return "\n".join(pagina.extract_text() or "" for pagina in lector.pages)


def fragmentar_por_seccion(texto, documento):
    """
    Parte el texto en fragmentos, uno por seccion numerada de primer nivel.

    Busca lineas que empiecen con "N." (1., 2., 3. ...). Todo lo que va
    antes de la seccion 1 se guarda como encabezado del documento
    (titulo, codigo, version), que sirve como contexto.
    """
    fragmentos = []
    # separa en los numerales de primer nivel: "1. Objeto", "2. Autorizacion"
    partes = re.split(r"\n(?=\d+\.\s+[A-ZÁÉÍÓÚÑ])", texto)

    encabezado = partes[0].strip()[:300] if partes else ""

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"^(\d+)\.\s+([^\n]+)", parte)
        if not m:
            continue  # el encabezado inicial, ya capturado aparte
        numero, titulo = m.group(1), m.group(2).strip()
        fragmentos.append(
            {
                "documento": documento,
                "seccion": f"{numero}. {titulo}",
                "texto": f"{encabezado}\n\n{parte}",
                "texto_limpio": parte,
            }
        )
    return fragmentos


def calcular_embedding(texto, intentos=3, timeout=30):
    """Calcula el embedding de un texto con la API de Gemini."""
    if not API_KEY:
        raise RuntimeError("Falta IA_PROVIDER_API_KEY en el .env")

    cuerpo = {
        "model": f"models/{MODELO_EMBEDDING}",
        "content": {"parts": [{"text": texto}]},
    }
    for intento in range(1, intentos + 1):
        try:
            r = requests.post(
                URL_EMBEDDING,
                json=cuerpo,
                headers={"x-goog-api-key": API_KEY},
                timeout=timeout,
            )
        except requests.exceptions.RequestException as e:
            if intento == intentos:
                raise RuntimeError(f"Error de red al calcular embedding: {e}")
        else:
            if r.status_code == 200:
                return r.json()["embedding"]["values"]
            if r.status_code == 429 or r.status_code >= 500:
                if intento == intentos:
                    raise RuntimeError(f"Proveedor no disponible: {r.status_code}")
            else:
                raise RuntimeError(f"Error {r.status_code}: {r.text[:200]}")
        time.sleep(intento * 2)


def construir_indice():
    pdfs = sorted(RUTA_POLITICAS.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No se encontraron PDFs en {RUTA_POLITICAS}")

    todos = []
    for pdf in pdfs:
        texto = extraer_texto(pdf)
        fragmentos = fragmentar_por_seccion(texto, pdf.stem)
        print(f"{pdf.name}: {len(fragmentos)} secciones")
        todos.extend(fragmentos)

    print(f"\nTotal de fragmentos: {len(todos)}")
    print("Calculando embeddings (puede tardar un par de minutos)...")

    for i, fragmento in enumerate(todos, 1):
        fragmento["embedding"] = calcular_embedding(fragmento["texto_limpio"])
        print(f"  [{i}/{len(todos)}] {fragmento['documento']} — {fragmento['seccion'][:50]}")
        time.sleep(0.3)  # cortesia con el limite de tasa del proveedor

    RUTA_INDICE.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA_INDICE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False)

    print(f"\nIndice guardado en {RUTA_INDICE}")


if __name__ == "__main__":
    construir_indice()