"""
main.py
Orquesta la limpieza completa del CSV histórico de tickets.

Ejecucion (desde la raiz del proyecto):
    python3 -m src.main
    python3 -m src.main ruta/otro_archivo.csv
"""
import csv
import sys
from pathlib import Path

from src.clean import (
    normalize_date,
    normalize_category,
    remove_duplicates,
    validate_record,
    apply_defaults,
)

RUTA_ENTRADA_DEFECTO = "data/raw/tickets_historicos.csv"
RUTA_SALIDA_LIMPIOS = "data/processed/tickets_limpios.csv"
RUTA_SALIDA_DESCARTES = "data/processed/descartes.csv"
RUTA_SALIDA_RESUMEN = "data/processed/resumen_area_prioridad.csv"


def cargar_tickets(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def procesar_ticket(ticket):
    """
    Valida y normaliza un ticket ya deduplicado.
    Devuelve (es_valido, ticket_procesado_o_None, razones)
    """
    valido, razones = validate_record(ticket)
    if not valido:
        return False, None, razones

    ticket = apply_defaults(ticket)
    ticket["categoria"] = normalize_category(ticket.get("categoria"))

    fecha_creacion = normalize_date(ticket.get("fecha_creacion"))
    ticket["fecha_creacion"] = fecha_creacion.isoformat() if fecha_creacion else ""

    fecha_cierre = normalize_date(ticket.get("fecha_cierre"))
    ticket["fecha_cierre"] = fecha_cierre.isoformat() if fecha_cierre else ""

    return True, ticket, []


def generar_resumen(tickets_validos):
    """Cuenta tickets validos agrupados por (area, prioridad)."""
    resumen = {}
    for t in tickets_validos:
        clave = (t.get("area", ""), t.get("prioridad", ""))
        resumen[clave] = resumen.get(clave, 0) + 1
    return resumen


def guardar_csv(ruta, filas, columnas):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)


def main(ruta_entrada=RUTA_ENTRADA_DEFECTO):
    tickets_crudos = cargar_tickets(ruta_entrada)
    print(f"Leidos {len(tickets_crudos)} registros de {ruta_entrada}")

    sin_duplicados, cantidad_duplicados = remove_duplicates(tickets_crudos)
    print(f"Duplicados eliminados: {cantidad_duplicados}")

    validos, descartes = [], []
    for ticket in sin_duplicados:
        es_valido, ticket_procesado, razones = procesar_ticket(ticket)
        if es_valido:
            validos.append(ticket_procesado)
        else:
            fila = dict(ticket)
            fila["razon_descarte"] = "; ".join(razones)
            descartes.append(fila)

    print(f"Validos: {len(validos)}  |  Descartados: {len(descartes)}")

    columnas = list(tickets_crudos[0].keys()) if tickets_crudos else []
    guardar_csv(RUTA_SALIDA_LIMPIOS, validos, columnas)
    guardar_csv(RUTA_SALIDA_DESCARTES, descartes, columnas + ["razon_descarte"])

    resumen = generar_resumen(validos)
    filas_resumen = [
        {"area": area, "prioridad": prioridad, "total": total}
        for (area, prioridad), total in sorted(resumen.items())
    ]
    guardar_csv(RUTA_SALIDA_RESUMEN, filas_resumen, ["area", "prioridad", "total"])

    print(f"Guardado: {RUTA_SALIDA_LIMPIOS}")
    print(f"Guardado: {RUTA_SALIDA_DESCARTES}")
    print(f"Guardado: {RUTA_SALIDA_RESUMEN}")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_ENTRADA_DEFECTO
    main(ruta)