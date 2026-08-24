# Revisión de código — `pr_para_revision.diff`

**Revisor:** Juan Daniel Cardenas Montoya
**Fecha:** 24 de agosto de 2026
**Cambio revisado:** `feat(mesa-ayuda): resumen mensual con clasificacion asistida por IA` (`app/reportes.py`, +118 líneas)

## Veredicto

**Rechazado — requiere cambios antes de una nueva revisión.** El cambio
introduce vulnerabilidades críticas de seguridad y defectos de robustez
que provocarían caídas e inconsistencia de datos en producción. El código
presenta señales de haber sido generado con asistencia de IA sin revisión
posterior (patrones repetitivos, mezcla de estilos, ausencia total de
manejo de errores), que es precisamente el riesgo que esta revisión debe
contener. Paradójicamente, algunos de estos errores se evidenciaron en la prueba y pudieron ser corregidos a tiempo.

---

## Hallazgos críticos

### C1 · Credencial escrita y versionada en el código
**Evidencia:** línea 5, `OPENAI_API_KEY = "sk-proj-..."`.
**Impacto:** cualquiera con acceso de lectura al repositorio obtiene la
clave del proveedor (costo económico, suplantación). Quedó además en el
historial de Git, por lo que moverla después no elimina la exposición.
GitHub la detectó automáticamente al hacer push (alerta de secret
scanning adjunta como evidencia). Incumple la política interna
POL-TIC-03 §7: "está prohibido incorporar credenciales en el código
fuente o en archivos de configuración versionados".
**Corrección:** cargar la clave desde variable de entorno (`.env`
ignorado por Git + `.env.example` documentando la variable), y **revocar
y rotar** la clave expuesta — moverla no basta, ya es pública para
cualquiera que haya visto el repo.

### C2 · Inyección SQL en la consulta principal
**Evidencia:** líneas 22-31 — la consulta se construye concatenando
texto, incluyendo entrada del usuario:
`"... WHERE correo = '" + usuario_solicitante + "')"`.
**Impacto:** un valor como `x') OR ('1'='1` anula el filtro y expone
tickets de todos los usuarios; variantes permiten modificar o borrar
datos. Las consultas secundarias usan `%` de formato de cadena
(`"... WHERE id_area = %s" % row[2]`), que parece parametrización pero
es concatenación: mismo riesgo. La conocida inyección SQL.
**Corrección:** consultas parametrizadas reales en todos los casos:
`cursor.execute("... WHERE correo = %s", (usuario_solicitante,))`.

### C3 · Salida del modelo de IA usada sin validar, y escrita a la base por concatenación
**Evidencia:** líneas 76-84 — `categoria_ia` (texto libre devuelto por el
modelo) se asigna directamente al ticket y se persiste con
`"UPDATE tickets SET categoria = '" + categoria_ia + "' ..."`.
**Impacto:** (a) el modelo puede devolver cualquier cosa — una frase
larga, una categoría inexistente en el catálogo, texto con comillas que
rompe el SQL — y queda escrita en la base como si fuera un dato válido;
(b) es una segunda vía de inyección SQL, esta vez a través de la
respuesta de un modelo que es manipulable (prompt injection desde el
contenido del ticket); (c) un proceso de *lectura* (generar un informe)
no debería tener el efecto secundario de *escribir* clasificaciones en
la base — sorprende al operador y dificulta la trazabilidad.
**Corrección:** validar la respuesta contra el catálogo cerrado de
categorías (si no coincide, `Sin clasificar`), parametrizar el UPDATE, y
separar la clasificación masiva del informe (proceso aparte y explícito).

### C4 · Llamada al proveedor de IA sin timeout ni manejo de error
**Evidencia:** líneas 71-75 — `requests.post(MODEL_URL, ...)` sin
`timeout`, sin `try/except`, sin reintentos; acceso directo a
`respuesta.json()["choices"][0]...`.
**Impacto:** si el proveedor no responde, el informe queda colgado
indefinidamente; si responde error (429/500, algo cotidiano en
proveedores externos), la función entera revienta por un solo ticket.
Además la llamada ocurre dentro del bucle: un mes con muchos tickets sin
clasificar implica decenas de llamadas secuenciales, con costo y latencia
sin control ni registro.
**Corrección:** timeout explícito, reintentos con espera creciente,
manejo del fallo con degradación (dejar el ticket como estaba y
reportarlo), y sacar la clasificación del camino del informe.

---

## Hallazgos altos

### A1 · El filtro de fechas excluye los días frontera del periodo
**Evidencia:** línea 22 — `fecha_creacion > inicio AND fecha_creacion < fin`.
**Impacto:** los tickets creados exactamente el primer día del mes quedan
fuera del informe. Es el mismo defecto ya diagnosticado como S1 en
`legacy_module.py` (corregido en este repositorio con su prueba): el
patrón se está repitiendo en código nuevo, lo que sugiere que falta una
prueba de referencia compartida para periodos.
**Corrección:** `fecha_creacion >= inicio AND fecha_creacion < fin`
(el fin ya está calculado como el día 1 del mes siguiente, así que el
`<` estricto en ese extremo sí es correcto).

### A2 · División por cero en el promedio de días de atención
**Evidencia:** línea 96 — `promedio = suma_dias / contador_dias`.
**Impacto:** en un mes sin tickets cerrados (escenario normal),
`contador_dias` vale 0 y la función revienta con `ZeroDivisionError`:
el informe completo se cae.
**Corrección:** `promedio = suma_dias / contador_dias if contador_dias else 0`
(o reportar `null` para distinguir "sin datos" de "promedio 0").

### A3 · Totales inconsistentes cuando se excluyen cerrados
**Evidencia:** líneas 60-90 — los contadores (`total_abiertos`,
`total_cerrados`, `total_reaperturas`) se acumulan ANTES del
`if incluirCerrados == False ... continue`, pero `"total"` se calcula
como `len(resultado)` DESPUÉS de excluir.
**Impacto:** con `incluirCerrados=False`, el resumen reporta un `total`
que no cuadra con `abiertos + cerrados` — cifras contradictorias en un
informe gerencial.
**Corrección:** decidir una semántica (¿los totales describen el periodo
o el listado?) y aplicar el filtro en un solo lugar, idealmente en la
propia consulta SQL.

---

## Hallazgos medios

### M1 · Consultas N+1 dentro del bucle
Por cada ticket se ejecutan 3 consultas adicionales (área, adjuntos,
reaperturas): un mes con 500 tickets son ~1.500 consultas. Corrección:
resolver con JOIN/agregaciones en la consulta principal.

### M2 · Sin manejo transaccional ante fallos
Se abre transacción (`conn.begin()`) y se hacen UPDATEs, pero no hay
`rollback` si algo falla a mitad de camino: clasificaciones parciales
quedan escritas o la conexión queda abierta. Corrección: `try/finally`
con rollback en error y cierre garantizado de conexión.

### M3 · Exportación CSV construida por concatenación, sin escapado
Un asunto o categoría que contenga una coma rompe las columnas del CSV.
Corrección: usar el módulo `csv` estándar.

### M4 · Estilo inconsistente y nombres mezclados
`incluirCerrados` (camelCase) junto a `area_filtro` (snake_case);
comparación `== False` en lugar de `not`; constante llamada
`OPENAI_API_KEY` para un proveedor genérico. Son señales típicas de
código generado por partes y no unificado. Corrección: pasada de estilo
(PEP 8) y linter en CI.

---

## Resumen

| # | Hallazgo | Severidad |
|---|---|---|
| C1 | Credencial versionada en el código | Crítica |
| C2 | Inyección SQL (consulta principal y secundarias) | Crítica |
| C3 | Salida de IA sin validar escrita a la base | Crítica |
| C4 | Llamada a IA sin timeout ni manejo de error | Crítica |
| A1 | Días frontera excluidos del periodo (patrón S1 repetido) | Alta |
| A2 | División por cero en el promedio | Alta |
| A3 | Totales inconsistentes al excluir cerrados | Alta |
| M1-M4 | N+1, transacciones, CSV, estilo | Media |

**Condición para re-revisión:** corregidos C1-C4 y A1-A2, con sus pruebas
(en particular: prueba de periodo con tickets en los días frontera y
prueba del mes sin cierres), y la clave del proveedor rotada.
