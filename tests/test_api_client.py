"""
tests/test_api_client.py
Pruebas del cliente API SIN llamar al servicio real: se simulan las
respuestas con unittest.mock para poder probar los reintentos de forma
rapida y deterministica (el mock real falla al azar, las pruebas no
pueden depender del azar).
"""
from unittest.mock import Mock, patch

import pytest

from src.api_client import _request, ApiError, INTENTOS_MAXIMOS


def _respuesta(status, json_data=None, headers=None):
    r = Mock()
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.headers = headers or {}
    r.text = ""
    return r


def test_exito_al_primer_intento():
    with patch("src.api_client.requests.request") as m:
        m.return_value = _respuesta(200, {"estado": "operativo"})
        resultado = _request("GET", "/health")
    assert resultado == {"estado": "operativo"}
    assert m.call_count == 1


def test_reintenta_tras_error_500_y_luego_exito():
    with patch("src.api_client.requests.request") as m, patch("src.api_client.time.sleep"):
        m.side_effect = [
            _respuesta(500),
            _respuesta(200, {"ok": True}),
        ]
        resultado = _request("GET", "/solicitudes")
    assert resultado == {"ok": True}
    assert m.call_count == 2


def test_respeta_retry_after_en_429():
    with patch("src.api_client.requests.request") as m, patch("src.api_client.time.sleep") as s:
        m.side_effect = [
            _respuesta(429, headers={"Retry-After": "3"}),
            _respuesta(200, {"ok": True}),
        ]
        resultado = _request("GET", "/solicitudes")
    assert resultado == {"ok": True}
    s.assert_any_call(3)  # espero exactamente lo que pidio el servicio


def test_agota_reintentos_y_lanza_error_comprensible():
    with patch("src.api_client.requests.request") as m, patch("src.api_client.time.sleep"):
        m.return_value = _respuesta(500)
        with pytest.raises(ApiError) as excinfo:
            _request("GET", "/solicitudes")
    assert m.call_count == INTENTOS_MAXIMOS
    assert "intentos" in str(excinfo.value)


def test_error_401_no_se_reintenta():
    with patch("src.api_client.requests.request") as m:
        m.return_value = _respuesta(401)
        with pytest.raises(ApiError) as excinfo:
            _request("GET", "/solicitudes")
    assert m.call_count == 1  # reintentar con el mismo token malo no sirve
    assert "Token" in str(excinfo.value)