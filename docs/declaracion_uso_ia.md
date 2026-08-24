# Declaración de uso de asistentes de IA

**Autor:** Juan Daniel Cardenas Montoya
**Prueba Técnica de Nivelación — perfiles IA · La Fortuna S.A.**
**Fecha:** 24 de agosto de 2026

## Asistente utilizado

Claude (Anthropic), a través de su interfaz de chat, durante toda la
sesión de desarrollo.

## Cómo se usó, por componente

| Componente | Uso del asistente | Aporte propio |
|---|---|---|
| Diseño de la Etapa 1 | Estructura de carpetas y contratos de funciones propuestos en conjunto | Decisión de alcance y de qué construir primero |
| `src/clean.py` — normalización de fechas | Redacción del código a partir de los tres formatos que identifiqué en el CSV real | Identificación de los formatos, decisión del supuesto `DD/MM/YYYY` |
| `src/clean.py` — categorías | Redacción del diccionario de mapeo | Decisión de negocio: qué categorías fusionar (`Conectividad`→`Red`, `Gestión de accesos`→`Accesos`) y que los valores no reconocidos no se descarten |
| `src/clean.py` — deduplicación | Implementación | Criterio: deduplicar por `id` y conservar la última aparición como estado más reciente |
| `src/clean.py` — validación | Implementación | Decisión de qué campos son obligatorios y cuáles opcionales con valor por defecto |
| `src/main.py` | Redacción del orquestador | Revisión y verificación de los resultados sobre los datos reales |
| `src/api_client.py` | Redacción del cliente con reintentos | Verificación contra el servicio real; lectura del código del mock para entender su comportamiento de fallo |
| `sql/queries.sql` | Redacción a partir del esquema | Verificación de la ejecución y los resultados |
| `src/legacy_module.py` (S1, S2, S3) | Confirmación de las causas raíz y redacción de las correcciones | Diagnóstico inicial propio de los tres síntomas antes de consultar; la hipótesis de S1 (fechas) fue correcta, S2 y S3 se corrigieron tras discutir el mecanismo real |
| `src/api.py` | Redacción de la API | Validación del diseño de recursos y del formato de error |
| `src/clasificador.py` | Redacción del módulo y del proveedor Gemini | Diagnóstico en vivo de los fallos del proveedor (modelo deprecado, timeout) y decisión de ajustar el timeout |
| `frontend/` (Angular) | Redacción del servicio, componente, plantilla y estilos | Ejecución, corrección de los errores de compilación y verificación funcional |
| Pruebas (50) | Redacción de los casos | Criterio sobre qué casos de borde probar, a partir del ruido observado en los datos reales |
| `docs/revision_pr.md` | Estructura del documento, redacción formal y hallazgos C3, A3, M1-M4 | Identificación propia de C1 (credencial), A1 (fechas frontera), A2 (división por cero) y C4 (llamada sin timeout, por comparación con mi propio cliente); comprensión y validación de C2 (inyección SQL) |
| `README.md` y este documento | Redacción | Verificación de que todo lo declarado corresponde a lo construido |

## Verificación y responsabilidad

- Todo el código entregado fue ejecutado y verificado por mí. Las 50
  pruebas corren en verde y los resultados sobre los datos reales fueron
  revisados manualmente.
- Cuando el asistente propuso código que no funcionó (por ejemplo, un
  provider de Angular que ya no existe en la versión 22, o un modelo de
  Gemini que fue deprecado), el diagnóstico y la corrección se hicieron
  leyendo el error real y ajustando el código.
- Entiendo cada decisión de diseño documentada en el README y puedo
  explicar y modificar cualquier parte del código entregado.

## Lo que no se hizo con IA

- La verificación funcional de cada componente contra los datos y
  servicios reales.
- Las decisiones de negocio (fusión de categorías, campos obligatorios,
  criterio de deduplicación, alcance de cada etapa).
- El diagnóstico inicial de los tres defectos del módulo heredado y de la
  mayoría de los hallazgos de la revisión de código.

## Datos de la compañía

No se usaron datos reales de la compañía en herramientas externas. Todo el
material procesado es el conjunto sintético entregado con la prueba.
