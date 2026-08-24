# Mesa de Ayuda Inteligente — Prueba Técnica de Nivelación

Solución de la prueba técnica de La Fortuna S.A. — perfiles IA.

**Autor:** Juan Daniel Cardenas Montoya

**Alcance alcanzado:** Etapa 1 y Etapa 2 completas (incluido el opcional de
pantalla Angular), y de la Etapa 3 el componente de RAG sobre las políticas
con citación de fuente y comportamiento de abstención. Los demás
entregables de la Etapa 3 y las Etapas 4 y 5 no se desarrollaron, con
excepción de la revisión escrita del PR que se solicita en la Etapa 5.

## Entregables y dónde están

| Entregable | Ubicación |
|---|---|
| Limpieza del histórico | `src/clean.py`, `src/main.py` |
| Cliente del servicio externo | `src/api_client.py` |
| Consultas SQL | `sql/queries.sql` · resultados en `sql/resultados_queries.txt` |
| API REST propia | `src/api.py` |
| Módulo IA desacoplado | `src/clasificador.py` |
| Corrección del módulo heredado | `src/legacy_module.py` · pruebas en `tests/test_legacy_module.py` |
| RAG sobre políticas | `src/rag_ingesta.py`, `src/rag_consulta.py` |
| Pantalla Angular (opcional) | `frontend/` |
| Pruebas (50) | `tests/` |
| Revisión de código del PR | `docs/revision_pr.md` |
| Declaración de uso de IA | `docs/declaracion_uso_ia.md` |
| Video de recorrido (Youtube) | https://youtu.be/jzwOt6saaUY |

## Qué hace

### Etapa 1 — Fundamentos

**Limpieza del CSV** (`src/clean.py` + `src/main.py`): procesa los 2.000
registros de `data/raw/tickets_historicos.csv`, normaliza fechas (tres
formatos: ISO, `DD-Mes-YYYY` en español y `DD/MM/YYYY`) y categorías,
elimina duplicados por id, valida campos obligatorios y produce
`tickets_limpios.csv`, `descartes.csv` (con la razón de cada descarte) y
`resumen_area_prioridad.csv`.

Resultado sobre los datos reales: **2.000 leídos · 40 duplicados
eliminados · 1.771 válidos · 189 descartados**.

**Cliente del servicio externo** (`src/api_client.py`): consume el mock
(GET `/health`, GET `/solicitudes`, POST `/solicitudes`) asumiendo que
falla —12 % de errores 500 y 5 % de 429—: timeout explícito, reintentos con
espera creciente, respeto de la cabecera `Retry-After`, y errores finales
comprensibles. No reintenta ante 401, porque un token inválido no se
resuelve reintentando.

**Consultas SQL** (`sql/queries.sql`): agregación por área, join de tres
tablas y tickets reabiertos, sobre `data/raw/esquema.sql` en SQLite.

### Etapa 2 — Autonomía e integración

**API REST propia** (`src/api.py`): crear solicitud (`POST /solicitudes`),
consultar estado (`GET /solicitudes/{id}`), listar con filtros por área y
estado (`GET /solicitudes`) y clasificar texto (`POST /clasificar`).
Validación con Pydantic (422 automático), códigos de estado correctos y
forma uniforme de error: `{"error": {"codigo": ..., "mensaje": ...}}`.

**Módulo IA desacoplado** (`src/clasificador.py`): clasifica texto libre en
categoría y prioridad. La lógica de negocio no conoce al proveedor: recibe
cualquier objeto con un método `.clasificar(texto)`. `ProveedorGemini` es
una implementación intercambiable, y las pruebas corren con tres
proveedores falsos distintos sin tocar la lógica. Si el proveedor falla, se
degrada a clasificación por reglas y el resultado declara su origen (`ia` o
`reglas_degradado`). La respuesta del modelo se valida contra el catálogo
cerrado de categorías: nunca se acepta una etiqueta inventada.

Durante el desarrollo el proveedor falló de tres formas reales —el modelo utilizado fue deprecado (404), hubo timeouts, y se agotó la cuota (429)—, y el sistema siguió respondiendo en modo degradado sin interrumpirse.

**Corrección del módulo heredado** (`src/legacy_module.py`): los tres
síntomas reportados, cada uno con su causa raíz y su prueba escrita antes
de la corrección (el par test→fix es visible en el historial de Git):

- **S1** — el filtro de periodo usaba comparaciones estrictas (`>`, `<`) y
  excluía los tickets creados el primer y último día del mes.
- **S2** — `resumir_por_area` usaba un diccionario como valor por defecto
  mutable; en Python se evalúa una sola vez al definir la función, así que
  todas las llamadas compartían el mismo acumulador y las cifras se
  arrastraban entre corridas.
- **S3** — el conteo de reaperturas comparaba `estado == "reabierto"`:
  sensible a mayúsculas y ciego a los tickets reabiertos que ya se
  cerraron. La fuente confiable es la columna `reaperturas`.

**Pantalla Angular** (`frontend/`, opcional con puntaje): consume la API
propia —crear solicitud, listar con filtros, y clasificar texto mostrando
el origen de la clasificación.

### Etapa 3 (parcial) — RAG sobre las políticas

**Ingesta** (`src/rag_ingesta.py`): extrae el texto de los cinco PDF y los
fragmenta **por sección numerada**, no por bloques fijos de caracteres.
Cada sección es una unidad de sentido completa: permite citar
"POL-ADM-04 sección 3" con precisión y evita cortar una tabla de montos por
la mitad. Resultado: 37 fragmentos. Los embeddings se calculan con
`gemini-embedding-001` y se guardan en un índice JSON.

**Consulta** (`src/rag_consulta.py`): recupera los 3 fragmentos más
similares por similitud coseno y genera una respuesta fundamentada que cita
documento y sección.

**Abstención — dos barreras.** El corpus no cubre todos los temas, y eso es
intencional según el material entregado:

1. **Umbral de similitud** (0.60): si el mejor fragmento no lo supera, no
   se llama al modelo.
2. **Instrucción explícita** en el prompt: responder únicamente con los
   fragmentos entregados, y declarar cuando no alcanzan.

Casos de prueba verificados:

| Pregunta | Resultado |
|---|---|
| Anticipación para solicitar vacaciones | Responde: 15 días calendario · POL-GTH-01 §3 |
| Monto de hospedaje en ciudades capitales | Responde: $260.000 · POL-ADM-04 §3 |
| Tiempo de entrega de un monitor adicional | Responde: 5 días hábiles · POL-TIC-02 §3 |
| Días de licencia de paternidad | **Se abstiene** (tema no cubierto) |
| Hospedaje en Cartagena | Se abstiene — falso negativo, ver abajo |

El caso de la licencia de paternidad es ilustrativo: la similitud fue 0.674
y **superó el umbral**, así que la primera barrera no alcanzó; fue la
instrucción del prompt la que evitó la invención. Por eso están las dos.

**Trade-off asumido.** La pregunta por el hospedaje en Cartagena se abstiene
aunque la respuesta existe: la política habla de "ciudades capitales" y
nunca menciona Cartagena, y el modelo —siguiendo la instrucción estricta—
no hace el salto inferencial. Es un falso negativo conocido. Se prefiere
errar hacia la abstención: según el propio enunciado, una respuesta
equivocada sobre montos o plazos genera reclamación formal ante Talento
Humano. Errar callando cuesta menos que errar inventando.

## Cómo instalar

Requiere Python 3.10+, Node 20+ y sqlite3.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt        # dependencias propias
pip install -r mock/requirements.txt   # dependencias del servicio mock (provisto)
cp .env.example .env                   # y completar los valores
cd frontend && npm install             # dependencias del frontend
```

Variables del `.env`:

```
MOCK_API_BASE_URL=http://localhost:8080
MOCK_API_TOKEN=demo-token-prueba-2026
IA_PROVIDER_API_KEY=<clave del proveedor de IA>
```

El token del mock es el documentado en `mock/README.md` (material sintético
de la prueba). No hay credenciales propias versionadas en este repositorio.

## Cómo ejecutar

```bash
# Limpieza del CSV
python3 -m src.main

# Pruebas (50)
pytest tests/ -v

# Consultas SQL
sqlite3 data/tickets.db < data/raw/esquema.sql
sqlite3 data/tickets.db < sql/queries.sql

# RAG: primero construir el índice (tarda ~2 min), luego consultar
python3 -m src.rag_ingesta
python3 -m src.rag_consulta "¿Con cuánta anticipación debo pedir vacaciones?"

# Servicios (cada uno en su terminal)
cd mock && uvicorn app:app --port 8080          # servicio externo simulado
uvicorn src.api:app --reload --port 8000        # API propia · docs en /docs
cd frontend && npx ng serve                     # pantalla · localhost:4200
```

## Supuestos declarados

- **Fechas con `/`**: formato `DD/MM/YYYY` (estándar colombiano), no `MM/DD/YYYY`.
- **Duplicados**: el CSV no trae columna de última actualización; se asume
  orden cronológico y entre filas con el mismo `id` se conserva la última
  aparición como estado más reciente.
- **Categorías**: se fusionaron equivalentes para no multiplicar el
  catálogo (`Conectividad` → `Red`, `Gestión de accesos` → `Accesos`). Los
  valores no reconocidos caen en `Sin clasificar` y no se descartan: un
  ticket sin categorizar puede ser importante.
- **Campos obligatorios**: id, fecha_creacion, area, categoria, prioridad,
  solicitante, asunto. Los opcionales reciben un valor por defecto
  explícito (`Sin canal`, `Sin estado`, `0`) para que la ausencia quede
  visible en lugar de silenciosa.
- **Fragmentación del RAG**: por sección numerada, aprovechando la
  estructura de las políticas.
- **Índice vectorial en JSON**: con 37 fragmentos, comparar todos contra la
  pregunta es instantáneo. Una base vectorial dedicada (FAISS, Chroma,
  pgvector) sería la respuesta correcta a partir de miles de documentos;
  aquí sería complejidad sin beneficio.
- **Pruebas del cliente API y del clasificador**: simulan las respuestas
  del servicio y del proveedor, porque el mock real falla al azar y las
  pruebas deben ser deterministas.
- **Almacenamiento de la API propia**: en memoria.
- **CORS**: la API autoriza únicamente el origen del frontend
  (`http://localhost:4200`), no `*`.

## Qué quedó fuera

- **Etapa 3**: quedaron fuera el pipeline de CI, el informe de seguridad
  sobre código generado por IA, la instrumentación de latencia y tokens, y
  el artefacto de estándares para el equipo. Solo se desarrolló el RAG.
- **Etapas 4 y 5**: no desarrolladas, salvo la revisión escrita del PR
  (`docs/revision_pr.md`), que corresponde a la Etapa 5 y a la
  sustentación.
- **Normalización de prioridad**: el CSV trae variantes (`alta`, `ALTA`,
  `1-Alta`, `CRITICA`) que no se normalizaron; el resumen las refleja tal
  como vienen. Es el mismo patrón ya resuelto para categorías y quedó
  pendiente por tiempo.
- **Carga del histórico a la API**: la API gestiona solicitudes creadas a
  través de ella; no se precargó el histórico limpio del CSV. Son dos
  flujos independientes por alcance: el CSV es procesamiento por lotes con
  salida en archivos, la API es gestión transaccional. La evolución natural
  sería persistir ambos en el modelo relacional de `esquema.sql`.
- **Persistencia**: los datos de la API se pierden al reiniciar.
- **Pruebas del frontend**: el proyecto Angular se generó con `--skip-tests`.
- **Medición de costo y latencia**: no se instrumentó. Corresponde a la
  Etapa 3 y es la primera mejora que abordaría con más tiempo.
- **Calibración del umbral del RAG**: se fijó observando la similitud de
  preguntas dentro y fuera del corpus. Es una estimación, no una medición
  contra un conjunto de referencia etiquetado.
- **Autoevaluación de competencias**: el formato PC-GTH-68 se diligencia
  durante la entrevista, según confirmó el área de Gestión Humana. No
  corresponde a esta entrega.

## Nota sobre la alerta de secreto en GitHub

Al hacer push, GitHub alertó por una clave de API presente en
`docs/pr_para_revision.diff`. Esa clave hace parte del material entregado
para la revisión de código y es sintética; se conserva intencionalmente
como parte del enunciado y su análisis es el hallazgo C1 de
`docs/revision_pr.md`. No hay secretos propios versionados.

## Nota de seguridad sobre el RAG

Un sistema RAG sobre documentos corporativos es vulnerable a inyección de
instrucciones incrustadas en los propios documentos: texto oculto que
instruya al modelo a ignorar sus reglas. Se verificó que los PDF y demás
materiales entregados no contuvieran texto oculto, caracteres invisibles ni
instrucciones dirigidas a un modelo. En producción esto debería ser un
control automatizado en la ingesta, no una revisión manual.

## Uso de asistentes de IA

Se utilizó Claude (Anthropic) como asistente durante el desarrollo. El
detalle por componente está en `docs/declaracion_uso_ia.md`.
