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
