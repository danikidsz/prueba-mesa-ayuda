"""
clasificador.py
Modulo IA desacoplado (Etapa 2): clasifica texto libre de una solicitud
en categoria y prioridad.

Arquitectura (punto critico #4 del enunciado -- desacoplar el proveedor):
- La logica de negocio (clasificar_solicitud) NUNCA llama al proveedor
  directamente: recibe cualquier objeto con un metodo .clasificar(texto).
- ProveedorGemini es solo UNA implementacion. Cambiar de proveedor
  (OpenAI, Anthropic, un modelo local) = escribir otra clase con el
  mismo metodo, sin tocar la logica de negocio.
- Si el proveedor falla (sin clave, timeout, error), se cae a un modo
  degradado por reglas de palabras clave: el sistema sigue respondiendo,
  y marca el origen para que se sepa que no fue la IA.

Configuracion (.env):
    IA_PROVIDER_API_KEY   -- clave del proveedor (Gemini)
"""
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

CATEGORIAS_VALIDAS = [
    "Hardware", "Software", "Red", "Accesos", "Incidente",
    "Viáticos", "Vacaciones", "Nómina", "Reportes", "Compras",
    "Sin clasificar",
]
PRIORIDADES_VALIDAS = ["Baja", "Media", "Alta", "Critica"]


class ProveedorIAError(Exception):
    """El proveedor de IA no pudo responder (sin clave, timeout, error)."""


class ProveedorGemini:
    """Implementacion del proveedor usando la API REST de Gemini."""

    URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None, modelo="gemini-3.6-flash", timeout=30, intentos=2):
        self.api_key = api_key if api_key is not None else os.getenv("IA_PROVIDER_API_KEY", "")
        self.modelo = modelo
        self.timeout = timeout
        self.intentos = intentos

    def clasificar(self, texto):    
        if not self.api_key:
            raise ProveedorIAError("No hay clave configurada (IA_PROVIDER_API_KEY).")

        prompt = (
            "Clasifica esta solicitud de mesa de ayuda corporativa.\n"
            f"Solicitud: \"{texto}\"\n\n"
            f"Categorias posibles: {', '.join(CATEGORIAS_VALIDAS)}\n"
            f"Prioridades posibles: {', '.join(PRIORIDADES_VALIDAS)}\n\n"
            "Responde UNICAMENTE un JSON con las claves categoria y "
            "prioridad. Sin explicacion, sin markdown."
        )
        cuerpo = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        url = f"{self.URL_BASE}/{self.modelo}:generateContent"

        ultimo_error = None
        for intento in range(1, self.intentos + 1):
            try:
                r = requests.post(
                    url,
                    json=cuerpo,
                    headers={"x-goog-api-key": self.api_key},
                    timeout=self.timeout,
                )
            except requests.exceptions.Timeout:
                ultimo_error = f"timeout tras {self.timeout}s (intento {intento})"
            except requests.exceptions.ConnectionError:
                ultimo_error = f"sin conexion (intento {intento})"
            else:
                if r.status_code == 200:
                    try:
                        texto_modelo = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        return json.loads(texto_modelo)
                    except (KeyError, IndexError, json.JSONDecodeError) as e:
                        raise ProveedorIAError(f"Respuesta del modelo no interpretable: {e}")
                if r.status_code in (429,) or r.status_code >= 500:
                    ultimo_error = f"{r.status_code} del proveedor (intento {intento})"
                else:
                    raise ProveedorIAError(f"Error {r.status_code} del proveedor: {r.text[:200]}")
            time.sleep(intento)  # espera creciente entre reintentos

        raise ProveedorIAError(f"Proveedor no disponible tras {self.intentos} intentos ({ultimo_error}).")


class ClasificadorPorReglas:
    """
    Modo degradado: clasificacion por palabras clave, sin IA.
    Menos preciso, pero disponible siempre y con costo cero.
    """

    REGLAS_CATEGORIA = {
        "Hardware": ["computador", "portatil", "pantalla", "teclado", "mouse", "impresora", "equipo", "monitor"],
        "Software": ["programa", "aplicacion", "licencia", "instalar", "office", "sistema"],
        "Red": ["internet", "red", "wifi", "conexion", "vpn", "lento"],
        "Accesos": ["acceso", "contrasena", "clave", "usuario", "bloqueado", "carpeta", "permiso"],
        "Vacaciones": ["vacaciones", "descanso"],
        "Nómina": ["nomina", "pago", "salario", "sueldo"],
        "Viáticos": ["viatico", "viaje", "hospedaje", "anticipo"],
        "Compras": ["compra", "proveedor", "orden"],
        "Reportes": ["reporte", "informe"],
    }
    PALABRAS_URGENTES = ["urgente", "caido", "no funciona", "no puedo trabajar", "toda el area", "critico"]

    def clasificar(self, texto):
        texto_bajo = (texto or "").lower()

        categoria = "Sin clasificar"
        for cat, palabras in self.REGLAS_CATEGORIA.items():
            if any(p in texto_bajo for p in palabras):
                categoria = cat
                break

        prioridad = "Alta" if any(p in texto_bajo for p in self.PALABRAS_URGENTES) else "Media"
        return {"categoria": categoria, "prioridad": prioridad}


def clasificar_solicitud(texto, proveedor=None):
    """
    Logica de negocio de clasificacion.

    Usa el proveedor recibido (o Gemini por defecto). Si el proveedor
    falla por cualquier motivo, cae al modo degradado por reglas.
    El resultado siempre indica su origen ("ia" o "reglas_degradado")
    y las etiquetas se validan contra las listas maestras: si el modelo
    devuelve algo fuera de catalogo, se normaliza en lugar de aceptarse.
    """
    if proveedor is None:
        proveedor = ProveedorGemini()

    try:
        resultado = proveedor.clasificar(texto)
        categoria = resultado.get("categoria", "Sin clasificar")
        prioridad = resultado.get("prioridad", "Media")
        if categoria not in CATEGORIAS_VALIDAS:
            categoria = "Sin clasificar"
        if prioridad not in PRIORIDADES_VALIDAS:
            prioridad = "Media"
        return {"categoria": categoria, "prioridad": prioridad, "origen": "ia"}
    except ProveedorIAError:
        respaldo = ClasificadorPorReglas().clasificar(texto)
        return {**respaldo, "origen": "reglas_degradado"}