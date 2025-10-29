# Validaciones y Reglas de Calidad de Datos

El script `etl/normalizar_CSVs.py` aplica validaciones automáticas en tres niveles: estructural, semántico y temporal.

## 1. Validaciones estructurales
- Cabeceras normalizadas mediante `ALIASES_MAP`.
- Si falta una columna, se crea vacía.
- Todos los textos cargados como `str`, sin NaN.
- Detección automática de separador y codificación.

## 2. Validaciones semánticas
### 2.1 Campos categóricos
- estado: {Abierto, En curso, Resuelto, Cerrado, Reabierto}
- prioridad: {Crítica, Alta, Media, Baja}
- canal: {EMAIL, PORTAL_SOPORTE, PORTAL_INTERNO, PORTAL_DOCUMENTAL}
- categoria: {ACC, SW, HW, NET, MAIL, APP, SRV, POL}
- sla_met: {true, false, ""}

Valores fuera de catálogo se sustituyen por los neutros.

### 2.2 Coherencia textual
- resumen mayor o igual a 5 caracteres, descripcion mayor o igual a 10 caracteres.
- Si ambos vacíos, la fila es inválida.

## 3. Validaciones temporales (Postfix)
| Regla | Descripción                                               | Acción                            |
|-------|-----------------------------------------------------------|-----------------------------------|
| 0     | fecha_cierre en el futuro                                 | Vaciar                            |
| 1     | Estado abierto/en curso/reabierto con fecha_cierre        | Vaciar                            |
| 3     | fecha_cierre < fecha_creacion                             | Vaciar                            |
| 4a    | fecha_cierre < first_reply_at y estado cerrado/resuelto   | fecha_cierre = max(first, crea)   |
| 4b    | fecha_cierre < first_reply_at y estado abierto            | Vaciar                            |
| 2     | Estado cerrado/resuelto sin fecha_cierre                  | Imputar max(first, crea)          |
|-------|-----------------------------------------------------------|-----------------------------------|

## 4. Auditoría
- logs/normalizar_report.json -> resumen de canales, categorías, impacto de reglas.
- logs/postfix_changes.csv -> evidencia de correcciones (antes/después).

## 5. Resultado esperado
- Ningún ticket con cierre si sigue abierto.
- Fechas coherentes.
- Sin fechas futuras o anteriores al 2000.
- Dataset 100% válido para entrenamiento supervisado.
