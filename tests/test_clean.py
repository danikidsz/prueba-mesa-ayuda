"""
tests/test_clean.py
Pruebas de la normalización de fechas, con casos reales tomados del
CSV entregado y casos de borde inventados a propósito.
"""
from datetime import date
from src.clean import normalize_date, normalize_category, remove_duplicates


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


def test_categoria_ya_correcta():
    assert normalize_category("Hardware") == "Hardware"


def test_categoria_mayusculas():
    assert normalize_category("HARDWARE") == "Hardware"


def test_categoria_minusculas():
    assert normalize_category("compras") == "Compras"


def test_categoria_sin_tilde():
    assert normalize_category("Nomina") == "Nómina"


def test_categoria_fusionada_conectividad_a_red():
    assert normalize_category("Conectividad") == "Red"


def test_categoria_fusionada_gestion_accesos():
    assert normalize_category("Gestión de accesos") == "Accesos"


def test_categoria_ya_sin_clasificar():
    assert normalize_category("Sin clasificar") == "Sin clasificar"


def test_categoria_vacia_cae_en_sin_clasificar():
    assert normalize_category("") == "Sin clasificar"


def test_categoria_none_cae_en_sin_clasificar():
    assert normalize_category(None) == "Sin clasificar"


def test_categoria_desconocida_cae_en_sin_clasificar():
    assert normalize_category("algo que nunca habiamos visto") == "Sin clasificar"


def test_sin_duplicados_no_cambia_nada():
    tickets = [
        {"id": "TK-001", "estado": "Abierto"},
        {"id": "TK-002", "estado": "Cerrado"},
    ]
    resultado, duplicados = remove_duplicates(tickets)
    assert len(resultado) == 2
    assert duplicados == 0
 
 
def test_deduplica_manteniendo_el_ultimo_estado():
    tickets = [
        {"id": "TK-001", "estado": "Abierto"},
        {"id": "TK-001", "estado": "Cerrado"},  # misma id, aparece despues
    ]
    resultado, duplicados = remove_duplicates(tickets)
    assert len(resultado) == 1
    assert resultado[0]["estado"] == "Cerrado"
    assert duplicados == 1
 
 
def test_cuenta_varios_duplicados():
    tickets = [
        {"id": "TK-001", "estado": "Abierto"},
        {"id": "TK-001", "estado": "En proceso"},
        {"id": "TK-001", "estado": "Cerrado"},
    ]
    resultado, duplicados = remove_duplicates(tickets)
    assert len(resultado) == 1
    assert resultado[0]["estado"] == "Cerrado"
    assert duplicados == 2
 
 
def test_filas_sin_id_no_se_pierden():
    tickets = [
        {"id": "", "estado": "Abierto"},
        {"id": "", "estado": "Cerrado"},
    ]
    resultado, duplicados = remove_duplicates(tickets)
    # ninguna tiene id, así que ninguna se considera "duplicada" entre sí
    assert len(resultado) == 2
    assert duplicados == 0
 