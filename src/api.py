"""
api.py
API REST propia de la Mesa de Ayuda (Etapa 2).

Tres recursos:
    POST /solicitudes            -- crear una solicitud
    GET  /solicitudes/{id}       -- consultar el estado de una solicitud
    GET  /solicitudes            -- listar, con filtros por area y estado

Decisiones declaradas:
- Validacion de entrada con Pydantic (mismos limites que el servicio
  externo, para mantener compatibilidad de contratos).
- Todos los errores responden con la misma forma JSON:
  {"error": {"codigo": <int>, "mensaje": <str>}}
- Almacenamiento en memoria (diccionario): el alcance de la etapa no
  exige persistencia; se declara como limite conocido en el README.

Ejecucion:
    uvicorn src.api:app --reload --port 8000
"""
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mesa de Ayuda -- API propia",
    version="1.0.0",
    description="API de solicitudes internas. Etapa 2 de la prueba tecnica.",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALMACEN: dict[str, dict] = {}


class SolicitudEntrada(BaseModel):
    asunto: str = Field(..., min_length=5, max_length=200)
    descripcion: str = Field("", max_length=4000)
    area: str = Field(..., min_length=2, max_length=80)
    solicitante: str = Field(..., min_length=5, max_length=120)


class SolicitudSalida(SolicitudEntrada):
    id: str
    estado: str
    fecha_creacion: str


@app.exception_handler(HTTPException)
async def errores_uniformes(request, exc):
    """Todos los errores HTTP salen con la misma forma JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"codigo": exc.status_code, "mensaje": exc.detail}},
    )


@app.post("/solicitudes", response_model=SolicitudSalida, status_code=201)
def crear_solicitud(cuerpo: SolicitudEntrada):
    id_solicitud = f"SOL-{uuid.uuid4().hex[:8].upper()}"
    registro = {
        **cuerpo.model_dump(),
        "id": id_solicitud,
        "estado": "Abierto",
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }
    ALMACEN[id_solicitud] = registro
    return registro


@app.get("/solicitudes/{id_solicitud}", response_model=SolicitudSalida)
def obtener_solicitud(id_solicitud: str):
    if id_solicitud not in ALMACEN:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    return ALMACEN[id_solicitud]


@app.get("/solicitudes", response_model=list[SolicitudSalida])
def listar_solicitudes(
    area: str | None = Query(None, description="Filtra por area (sin distinguir mayusculas)"),
    estado: str | None = Query(None, description="Filtra por estado"),
    limite: int = Query(50, ge=1, le=200),
):
    items = list(ALMACEN.values())
    if area:
        items = [s for s in items if s["area"].lower() == area.lower()]
    if estado:
        items = [s for s in items if s["estado"].lower() == estado.lower()]
    return items[:limite]

from src.clasificador import clasificar_solicitud


class TextoClasificar(BaseModel):
    texto: str = Field(..., min_length=5, max_length=4000)


@app.post("/clasificar")
def clasificar(cuerpo: TextoClasificar):
    return clasificar_solicitud(cuerpo.texto)