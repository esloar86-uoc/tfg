# Diccionario de Datos de Dataset de Tickets Normalizados

Este documento describe las columnas del archivo `data/s3/tickets_normalizados.csv` generado por el script `etl/normalizar_CSVs.py`.

## Estructura general

| Campo                 | Tipo          | Ejemplo           | Descripción   | Reglas de normalización |
|-----------------------|---------------|-------------------|---------------|-------------------------|
| **id_ticket**         | String        | kaggle1_INC000000 | Identificador único del ticket. Se genera a partir del ID original del dataset. | Prefijos: kaggle1_, kaggle2_, synt_.|
| **canal**             | String        | EMAIL             | Canal de entrada de la solicitud o incidencia. | Se mapea según origen: Kaggle1/Kaggle2 -> {EMAIL, PORTAL_SOPORTE, PORTAL_INTERNO}; además, si el texto contiene “documentation/manual/KB”, se marca como PORTAL_DOCUMENTAL. |
| **fecha_creacion**    | Datetime      | 2024-07-07 07:07  | Fecha y hora de creación del ticket. | Conversión a formato ISO YYYY-MM-DD HH:MM. |
| **first_reply_at**    | Datetime      | 2025-07-07 07:07  | Fecha de la primera respuesta del agente. | Normalizada a ISO; si no se puede interpretar, se deja vacía. |
| **fecha_cierre**      | Datetime      | 2025-07-07 07:07  | Fecha de resolución o cierre. | Se limpia si el estado no es de cierre o si la fecha es incoherente. |
| **estado**            | String        | Cerrado           | Estado actual del ticket. | Catálogo cerrado: Abierto, En curso, Resuelto, Cerrado, Reabierto. |
| **prioridad**         | String        | Alta              | Nivel de prioridad asignado. | Catálogo cerrado: Crítica, Alta, Media, Baja. |
| **categoria**         | String        | SW                | Categoría funcional según taxonomía. | Asignada automáticamente por diccionarios ES/EN + reglas contextuales. |
| **agente_id**         | String        | Agent_4           | Identificador del agente asignado. | Limpieza básica. |
| **sla_target_horas**  | String        | 24                | Objetivo de tiempo de resolución (SLA). | Copiado de origen si existe. |
| **sla_met**           | Boolean/String| true              | Cumplimiento del SLA. | Limpieza a true, false, "". |
| **resumen**           | String        | Problema al iniciar sesión en SAP | Descripción breve. | Unificación de campos `subject`, `short_description`... |
| **descripcion**       | String        | El usuario indica que SAP muestra error de autenticación. | Descripción detallada. | Limpieza de texto. |

## Notas adicionales
- Las fechas están en zona local, sin TZ explícita.
- Los campos vacíos son cadenas vacías.
- Dataset final: 41.071 registros.
- Integridad temporal garantizada (creación < respuesta < cierre).
