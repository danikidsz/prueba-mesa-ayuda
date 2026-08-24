# Mesa de Ayuda Inteligente — Prueba Técnica de Nivelación

Solución de la prueba técnica de La Fortuna S.A. — perfiles IA.

**Autor:** Daniel [REVISA: apellido]
**Etapa alcanzada:** Etapa 1 — Fundamentos (completa)

## Qué hace este proyecto

Etapa 1: limpieza del histórico de tickets, consumo del servicio externo
simulado y consultas SQL sobre el modelo relacional.

1. **Limpieza del CSV** (`src/clean.py` + `src/main.py`): lee
   `data/raw/tickets_historicos.csv` (2.000 registros con ruido real),
   normaliza fechas (3 formatos) y categorías, elimina duplicados,
   valida registros y produce:
   - `data/processed/tickets_limpios.csv` — registros válidos y normalizados
   - `data/processed/descartes.csv` — registros inválidos con su razón de descarte
   - `data/processed/resumen_area_prioridad.csv` — conteo por área y prioridad
2. **Cliente API** (`src/api_client.py`): consume el servicio mock
   (GET /health, GET /solicitudes, POST /solicitudes) con timeout,
   reintentos con espera creciente, respeto del Retry-After en 429 y
   errores finales comprensibles.
3. **Consultas SQL** (`sql/queries.sql`): agregación por área, join de
   tres tablas y tickets reabiertos, sobre `data/raw/esquema.sql`
   (SQLite). Resultados en `sql/resultados_queries.txt`.

## Cómo instalar

Requiere Python 3.10+ y sqlite3.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt        # dependencias propias
pip install -r mock/requirements.txt   # dependencias del servicio mock (provisto)
cp .env.example .env                   # y completar los valores (ver abajo)
```

Valores del `.env` para el servicio mock local:

```
MOCK_API_BASE_URL=http://localhost:8080
MOCK_API_TOKEN=demo-token-prueba-2026
```

(El token es el de prueba documentado en `mock/README.md`. Es material
sintético de la prueba; no hay credenciales reales en este proyecto.)

## Cómo ejecutar

**Limpieza del CSV:**
```bash
python3 -m src.main
```
Resultado de la corrida sobre los datos reales: 2000 leídos,
40 duplicados eliminados, 1771 válidos, 189 descartados con razón.

**Servicio mock + demo del cliente** (dos terminales):
```bash
# Terminal 1
cd mock && uvicorn app:app --port 8080

# Terminal 2
python3 -m src.api_client
```

**Pruebas (35):**
```bash
pytest tests/ -v
```

**Consultas SQL:**
```bash
sqlite3 data/tickets.db < data/raw/esquema.sql
sqlite3 data/tickets.db < sql/queries.sql
```

## Supuestos declarados

- **Fechas con `/`**: se asumen en formato `DD/MM/YYYY` (estándar
  colombiano), no `MM/DD/YYYY`.
- **Duplicados**: el CSV no trae columna de última actualización, así
  que se asume que el archivo está en orden cronológico; entre filas
  con el mismo `id`, se conserva la última aparición (estado más
  reciente del ticket).
- **Categorías**: se fusionaron equivalentes para no multiplicar
  categorías: `Conectividad` → `Red`, `Gestión de accesos` → `Accesos`.
  Valores no reconocidos caen en `Sin clasificar` (no se descartan).
- **Campos obligatorios**: id, fecha_creacion, area, categoria,
  prioridad, solicitante, asunto. Un registro sin alguno de estos se
  descarta con su razón registrada en `descartes.csv`.
- **Campos opcionales con valor por defecto**: descripcion (`""`),
  canal (`Sin canal`), estado (`Sin estado`), reaperturas (`0`).
  fecha_cierre puede ir vacía (ticket aún abierto).
- Las pruebas del cliente API simulan las respuestas del servicio
  (unittest.mock) porque el mock real falla al azar y las pruebas
  deben ser deterministas.

## Qué quedó fuera

- Etapas 2 a 5 [REVISA: actualizar si alcanzas a avanzar la Etapa 2].
- La normalización de prioridad (`1-Alta`, `ALTA`, etc.) quedó
  pendiente: el resumen por prioridad refleja los valores tal como
  vienen en el CSV. Se declara como límite conocido.
- No se cargó el CSV a la base SQL: `esquema.sql` trae su propio set
  de datos y las consultas corren sobre él, según el material entregado.

## Nota sobre la alerta de secreto en GitHub

Al hacer push, GitHub alertó por una clave de API presente en
`docs/pr_para_revision.diff`. Esa clave hace parte del material
entregado para la revisión de código (Etapa 5) y es sintética; se
conserva intencionalmente como parte del enunciado. No hay secretos
propios versionados en este repositorio.

## Declaración de uso de asistentes de IA

Se usó Claude (Anthropic) como asistente durante el desarrollo. Ver
`docs/declaracion_uso_ia.md` [REVISA: crear ese documento antes de entregar].