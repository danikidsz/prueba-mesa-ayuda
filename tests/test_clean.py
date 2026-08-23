"""
tests/test_clean.py
Pruebas de la normalización de fechas, con casos reales tomados del
CSV entregado y casos de borde inventados a propósito.
"""
from datetime import date
from src.clean import normalize_date


def test_formato_iso():
    assert normalize_date("2025-03-08") == date(2025, 3, 8)


def test_formato_dia_mes_espanol_abreviado():
    assert normalize_date("20-Ene-2026") == date(2026, 1, 20)


def test_formato_dia_mes_anio_con_slash():
    assert normalize_date("03/06/2025") == date(2025, 6, 3)


def test_cadena_vacia_devuelve_none():
    assert normalize_date("") is None


def test_valor_none_devuelve_none():
    assert normalize_date(None) is None


def test_fecha_invalida_devuelve_none():
    # 31/13/2024: mes 13 no existe
    assert normalize_date("31/13/2024") is None


def test_texto_no_reconocido_devuelve_none():
    assert normalize_date("no es una fecha") is None
