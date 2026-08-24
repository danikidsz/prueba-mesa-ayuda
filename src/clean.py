"""
clean.py
Funciones de limpieza y normalización para tickets_historicos.csv

Supuesto declarado: las fechas con separador '/' siguen el formato
DD/MM/YYYY (estándar colombiano), no MM/DD/YYYY como en EE.UU.
"""
from datetime import datetime

MESES_ES = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}


def normalize_date(raw):
    """
    Normaliza una fecha en cualquiera de los 3 formatos detectados en el
    CSV real:
      - ISO:         2025-03-08
      - DD-Mes-YYYY: 20-Ene-2026   (mes abreviado en español)
      - DD/MM/YYYY:  03/06/2025

    Devuelve un objeto date, o None si el valor está vacío o no se puede
    reconocer con ninguno de los 3 formatos. No lanza excepción: un dato
    corrupto no debe tumbar el resto del proceso, solo queda como
    descartado para que main.py lo registre.
    """
    if raw is None:
        return None

    valor = str(raw).strip()
    if not valor:
        return None

    # Caso 1 y 2: separador '-' (puede ser ISO o DD-Mes-YYYY)
    if "-" in valor:
        partes = valor.split("-")
        if len(partes) == 3:
            dia, medio, anio = partes
            mes_abrev = medio.lower()[:3]

            # DD-Mes-YYYY con mes en español abreviado (ej. 20-Ene-2026)
            if mes_abrev in MESES_ES:
                valor_iso = f"{anio}-{MESES_ES[mes_abrev]}-{dia.zfill(2)}"
                try:
                    return datetime.strptime(valor_iso, "%Y-%m-%d").date()
                except ValueError:
                    return None

            # Si no es un mes reconocible, asumimos ISO puro: YYYY-MM-DD
            try:
                return datetime.strptime(valor, "%Y-%m-%d").date()
            except ValueError:
                return None

        return None

    # Caso 3: separador '/', formato DD/MM/YYYY
    if "/" in valor:
        try:
            return datetime.strptime(valor, "%d/%m/%Y").date()
        except ValueError:
            return None

    # Ningún formato reconocido
    return None


CATEGORIAS = {
    "hardware": "Hardware",
    "software": "Software",
    "red": "Red",
    "conectividad": "Red",
    "accesos": "Accesos",
    "gestion de accesos": "Accesos",
    "gestión de accesos": "Accesos",
    "incidente": "Incidente",
    "viaticos": "Viáticos",
    "viáticos": "Viáticos",
    "vacaciones": "Vacaciones",
    "nomina": "Nómina",
    "nómina": "Nómina",
    "reportes": "Reportes",
    "compras": "Compras",
    "sin clasificar": "Sin clasificar",
}


def normalize_category(raw):
    """
    Normaliza una categoría a la lista maestra del negocio.

    Ignora mayúsculas/minúsculas y espacios sobrantes. Cualquier valor
    vacío o no reconocido en CATEGORIAS se marca como 'Sin clasificar'
    en lugar de descartarse -- puede ser información valiosa que
    todavía no tiene una categoría asignada.
    """
    if raw is None:
        return "Sin clasificar"

    valor = str(raw).strip().lower()
    if not valor:
        return "Sin clasificar"

    return CATEGORIAS.get(valor, "Sin clasificar")


def remove_duplicates(tickets):
    """
    Elimina duplicados por id, conservando la última aparición de cada uno.
 
    tickets: lista de diccionarios (una fila del CSV cada uno).
 
    Las filas sin id (campo vacío) no se descartan aquí -- se dejan pasar
    tal cual, porque la falta de id es un problema de validación, no de
    duplicados, y se maneja en otra función.
 
    Devuelve una tupla: (lista_sin_duplicados, cantidad_de_duplicados_eliminados)
    """
    vistos = {}
    duplicados = 0
 
    for i, ticket in enumerate(tickets):
        id_ticket = (ticket.get("id") or "").strip()
        clave = id_ticket if id_ticket else f"__sin_id_{i}"
 
        if clave in vistos:
            duplicados += 1
 
        vistos[clave] = ticket  # si ya existía, se sobrescribe con la última versión
 
    return list(vistos.values()), duplicados


"""
Agrega esto a src/clean.py, debajo de remove_duplicates().
"""

CAMPOS_OBLIGATORIOS = ["id", "fecha_creacion", "area", "categoria", "prioridad", "solicitante", "asunto"]


def validate_record(ticket):
    """
    Valida que un ticket tenga todos los campos obligatorios.

    Obligatorios: id, fecha_creacion, area, categoria, prioridad,
    solicitante, asunto. Un campo vacío o solo espacios cuenta como faltante.
    También se valida que fecha_creacion, si viene, tenga un formato
    reconocible (usa normalize_date).

    Devuelve una tupla: (es_valido: bool, razones: list[str])
    Si es_valido es False, razones explica por qué, para poder
    registrar el motivo en el archivo de descartes.
    """
    razones = []

    for campo in CAMPOS_OBLIGATORIOS:
        valor = str(ticket.get(campo) or "").strip()
        if not valor:
            razones.append(f"falta el campo obligatorio '{campo}'")

    fecha_raw = ticket.get("fecha_creacion")
    if fecha_raw and normalize_date(fecha_raw) is None:
        razones.append("fecha_creacion no tiene un formato reconocido")

    return (len(razones) == 0, razones)


def apply_defaults(ticket):
    """
    Rellena los campos opcionales vacíos con un valor por defecto explícito.

    No modifica el diccionario original -- devuelve una copia. Así,
    ningún dato faltante queda simplemente vacío o ausente: queda
    marcado de forma visible (ej. 'Sin estado'), para que se note que
    faltaba, en vez de perderse silenciosamente.
    """
    resultado = dict(ticket)

    if not str(resultado.get("descripcion") or "").strip():
        resultado["descripcion"] = ""

    if not str(resultado.get("canal") or "").strip():
        resultado["canal"] = "Sin canal"

    if not str(resultado.get("estado") or "").strip():
        resultado["estado"] = "Sin estado"

    if not str(resultado.get("reaperturas") or "").strip():
        resultado["reaperturas"] = "0"

    return resultado
 