"""
tests/test_legacy_module.py
Pruebas que exponen los tres defectos del modulo heredado (S1, S2, S3).
Se escriben ANTES de corregir: deben FALLAR con el codigo original,
y pasar despues de cada correccion.
"""
from datetime import date

from src.legacy_module import filtrar_por_periodo, resumir_por_area, contar_reaperturas


def test_s1_filtro_incluye_ambos_extremos_del_periodo():
    tickets = [
        {"fecha_creacion": "2025-03-01"},  # primer dia del periodo
        {"fecha_creacion": "2025-03-15"},  # dia intermedio
        {"fecha_creacion": "2025-03-31"},  # ultimo dia del periodo
    ]
    resultado = filtrar_por_periodo(tickets, date(2025, 3, 1), date(2025, 3, 31))
    assert len(resultado) == 3  # el docstring promete ambos extremos incluidos


def test_s2_resumen_no_arrastra_conteos_entre_llamadas():
    tickets = [{"area": "Calidad"}, {"area": "Calidad"}]
    resumir_por_area(tickets)             # primera corrida
    segundo = resumir_por_area(tickets)   # segunda corrida, mismos datos
    assert segundo == {"Calidad": 2}      # no debe heredar los de la primera


def test_s3_cuenta_reaperturas_aunque_el_ticket_ya_no_este_reabierto():
    tickets = [
        {"estado": "Cerrado", "reaperturas": "2"},    # fue reabierto, ya cerro
        {"estado": "REABIERTO", "reaperturas": "1"},  # mayusculas distintas
        {"estado": "Abierto", "reaperturas": "0"},    # nunca reabierto
    ]
    assert contar_reaperturas(tickets) == 2