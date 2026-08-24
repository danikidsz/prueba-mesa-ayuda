"""
tests/test_clasificador.py
Pruebas del modulo IA SIN llamar a ningun proveedor real: se usan
proveedores falsos. Esto ademas DEMUESTRA el desacoplamiento (punto
critico #4): la logica de negocio funciona con cualquier objeto que
tenga .clasificar(texto) -- cambiar de proveedor no exige reescribir.
"""
from src.clasificador import (
    clasificar_solicitud,
    ClasificadorPorReglas,
    ProveedorIAError,
)


class ProveedorFalsoOK:
    """Simula un proveedor de IA que responde bien."""

    def clasificar(self, texto):
        return {"categoria": "Hardware", "prioridad": "Alta"}


class ProveedorFalsoInvalido:
    """Simula un modelo que responde algo fuera del catalogo."""

    def clasificar(self, texto):
        return {"categoria": "CategoriaInventada", "prioridad": "Urgentisima"}


class ProveedorFalsoCaido:
    """Simula un proveedor que no responde (timeout, sin clave, 500...)."""

    def clasificar(self, texto):
        raise ProveedorIAError("proveedor caido")


def test_usa_el_resultado_del_proveedor_cuando_responde():
    r = clasificar_solicitud("mi computador no prende", proveedor=ProveedorFalsoOK())
    assert r == {"categoria": "Hardware", "prioridad": "Alta", "origen": "ia"}


def test_normaliza_etiquetas_fuera_de_catalogo():
    r = clasificar_solicitud("cualquier texto", proveedor=ProveedorFalsoInvalido())
    assert r["categoria"] == "Sin clasificar"
    assert r["prioridad"] == "Media"
    assert r["origen"] == "ia"


def test_cae_a_modo_degradado_si_el_proveedor_falla():
    r = clasificar_solicitud("no tengo acceso a la carpeta compartida", proveedor=ProveedorFalsoCaido())
    assert r["origen"] == "reglas_degradado"
    assert r["categoria"] == "Accesos"


def test_reglas_clasifica_hardware():
    r = ClasificadorPorReglas().clasificar("la impresora del piso 2 no funciona")
    assert r["categoria"] == "Hardware"


def test_reglas_detecta_urgencia():
    r = ClasificadorPorReglas().clasificar("URGENTE: el sistema esta caido para toda el area")
    assert r["prioridad"] == "Alta"


def test_reglas_texto_desconocido_cae_en_sin_clasificar():
    r = ClasificadorPorReglas().clasificar("asdf qwerty xyz")
    assert r["categoria"] == "Sin clasificar"
    assert r["prioridad"] == "Media"