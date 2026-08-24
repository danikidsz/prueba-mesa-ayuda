"""
api_client.py
Cliente para el Servicio de Solicitudes Corporativas (mock).

El servicio falla a proposito: ~12% de errores 500, ~5% de 429 con
cabecera Retry-After, y latencia variable de 0.1 a 2.5 segundos.
Este cliente esta diseñado asumiendo esos fallos: timeout explicito,
reintentos con espera creciente, y errores finales comprensibles.

Configuracion por variables de entorno (.env):
    MOCK_API_BASE_URL  (por defecto http://localhost:8080)
    MOCK_API_TOKEN     (token Bearer del servicio)
"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8080")
TOKEN = os.getenv("MOCK_API_TOKEN", "")

TIMEOUT_SEGUNDOS = 5
INTENTOS_MAXIMOS = 3
ESPERA_BASE = 1  # segundos; la espera crece con cada intento


class ApiError(Exception):
    """Error final del cliente, con mensaje entendible para el usuario."""


def _headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def _request(metodo, ruta, **kwargs):
    """
    Hace la peticion con reintentos.

    Reintenta ante: timeout, error 500+ del proveedor, y 429 (respetando
    la cabecera Retry-After si viene). No reintenta ante errores que no
    se resuelven reintentando: 401 (token malo) o 404 (no existe).
    """
    url = f"{BASE_URL}{ruta}"
    ultimo_error = None

    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            respuesta = requests.request(
                metodo, url, headers=_headers(), timeout=TIMEOUT_SEGUNDOS, **kwargs
            )
        except requests.exceptions.Timeout:
            ultimo_error = f"timeout tras {TIMEOUT_SEGUNDOS}s (intento {intento})"
        except requests.exceptions.ConnectionError:
            raise ApiError(
                "No se pudo conectar al servicio. "
                "¿Esta corriendo el mock en " + BASE_URL + "?"
            )
        else:
            if respuesta.status_code in (200, 201):
                return respuesta.json()

            if respuesta.status_code == 429:
                espera = int(respuesta.headers.get("Retry-After", ESPERA_BASE * intento))
                ultimo_error = f"429 limite de tasa (intento {intento})"
                time.sleep(espera)
                continue

            if respuesta.status_code >= 500:
                ultimo_error = f"{respuesta.status_code} error del proveedor (intento {intento})"
            elif respuesta.status_code == 401:
                raise ApiError("Token ausente o invalido: revisa MOCK_API_TOKEN en tu .env")
            elif respuesta.status_code == 404:
                raise ApiError(f"Recurso no encontrado: {ruta}")
            else:
                raise ApiError(
                    f"Respuesta inesperada {respuesta.status_code}: {respuesta.text[:200]}"
                )

        time.sleep(ESPERA_BASE * intento)  # espera creciente entre reintentos

    raise ApiError(
        f"El servicio no respondio correctamente tras {INTENTOS_MAXIMOS} intentos "
        f"(ultimo error: {ultimo_error})."
    )


def verificar_salud():
    """GET /health -- estado del servicio."""
    return _request("GET", "/health")


def listar_solicitudes(area=None, estado=None, limite=50):
    """GET /solicitudes -- lista solicitudes, con filtros opcionales."""
    params = {"limite": limite}
    if area:
        params["area"] = area
    if estado:
        params["estado"] = estado
    return _request("GET", "/solicitudes", params=params)


def crear_solicitud(asunto, area, solicitante, descripcion="", canal="api"):
    """POST /solicitudes -- crea una solicitud nueva."""
    cuerpo = {
        "asunto": asunto,
        "area": area,
        "solicitante": solicitante,
        "descripcion": descripcion,
        "canal": canal,
    }
    return _request("POST", "/solicitudes", json=cuerpo)


if __name__ == "__main__":
    # Demostracion rapida: salud, crear una solicitud, listarlas.
    print("Salud del servicio:", verificar_salud())

    creada = crear_solicitud(
        asunto="Prueba de conexion desde el cliente",
        area="Aplicaciones",
        solicitante="daniel@lafortuna.com.co",
        descripcion="Solicitud de prueba creada por api_client.py",
    )
    print("Solicitud creada:", creada["id"], "-", creada["estado"])

    solicitudes = listar_solicitudes(limite=10)
    print(f"Solicitudes listadas: {len(solicitudes)}")