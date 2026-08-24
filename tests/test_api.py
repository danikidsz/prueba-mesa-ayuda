"""
tests/test_api.py
Pruebas de la API propia usando el cliente de pruebas de FastAPI
(no necesita servidor corriendo).
"""
from fastapi.testclient import TestClient

from src.api import app, ALMACEN

client = TestClient(app)


def setup_function():
    """Limpia el almacen antes de cada prueba, para que sean independientes."""
    ALMACEN.clear()


def _solicitud_valida():
    return {
        "asunto": "Computador no enciende",
        "descripcion": "Desde esta manana no responde",
        "area": "Contabilidad",
        "solicitante": "usuario1@lafortuna.com.co",
    }


def test_crear_solicitud_devuelve_201_con_id_y_estado():
    respuesta = client.post("/solicitudes", json=_solicitud_valida())
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"].startswith("SOL-")
    assert cuerpo["estado"] == "Abierto"
    assert cuerpo["fecha_creacion"]


def test_crear_sin_asunto_devuelve_422():
    datos = _solicitud_valida()
    del datos["asunto"]
    respuesta = client.post("/solicitudes", json=datos)
    assert respuesta.status_code == 422


def test_obtener_solicitud_existente():
    creada = client.post("/solicitudes", json=_solicitud_valida()).json()
    respuesta = client.get(f"/solicitudes/{creada['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creada["id"]


def test_obtener_inexistente_devuelve_404_con_forma_uniforme():
    respuesta = client.get("/solicitudes/SOL-NOEXISTE")
    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == 404
    assert "mensaje" in cuerpo["error"]


def test_listar_filtra_por_area_sin_distinguir_mayusculas():
    client.post("/solicitudes", json=_solicitud_valida())
    otra = _solicitud_valida()
    otra["area"] = "Comercial"
    client.post("/solicitudes", json=otra)

    respuesta = client.get("/solicitudes", params={"area": "contabilidad"})
    assert respuesta.status_code == 200
    resultados = respuesta.json()
    assert len(resultados) == 1
    assert resultados[0]["area"] == "Contabilidad"


def test_listar_filtra_por_estado():
    client.post("/solicitudes", json=_solicitud_valida())
    respuesta = client.get("/solicitudes", params={"estado": "abierto"})
    assert len(respuesta.json()) == 1
    respuesta = client.get("/solicitudes", params={"estado": "cerrado"})
    assert len(respuesta.json()) == 0