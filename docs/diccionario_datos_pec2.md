# Diccionario de datos (PEC2)

| Campo             | Tipo                 | Descripción                                                             | Canal   |
|-------------------|----------------------|-------------------------------------------------------------------------|---------|
| id_ticket         | string               | Identificador único del ticket.                                         | Todos   |
| canal             | string               | EMAIL, PORTAL_SOPORTE, PORTAL_DOCUMENTAL, PORTAL_INTERNO.               | Todos   |
| fecha_creacion    | datetime (ISO 8601)  | Fecha/hora de creación.                                                 | Todos   |
| first_reply_at    | datetime (ISO 8601)  | Primera respuesta del agente (opcional).                                | Todos   |
| fecha_cierre      | datetime (ISO 8601)  | Cierre (opcional).                                                      | Todos   |
| estado            | string               | Abierto, En curso, Resuelto, Cerrado, Reabierto.                        | Todos   |
| prioridad         | string               | Baja, Media, Alta, Crítica.                                             | Todos   |
| categoria         | string               | C01–C08 (catálogo).                                                     | Todos   |
| agente_id         | string               | Identificador del agente (opcional).                                    | Todos   |
| sla_target_horas  | integer              | Objetivo SLA (horas).                                                   | Todos   |
| sla_met           | boolean              | true/false si cumplió SLA.                                              | Todos   |
| resumen           | string               | Título breve / asunto.                                                  | Todos   |
| descripcion       | string               | Texto libre con la incidencia.                                          | Todos   |
|-------------------|----------------------|-------------------------------------------------------------------------|---------|

**Extras por canal**
- **EMAIL**: `remitente_email (string)`, `destinatario_email (string)`
- **PORTAL_SOPORTE**: `form_id (string)`, `adjuntos (integer)`
- **PORTAL_DOCUMENTAL**: `doc_id (string)`, `tipo_documento (string)`
- **PORTAL_INTERNO**: `area (string: IT, RRHH, Operaciones, Legal, Finanzas)`, `origen_interno (string: AGENTE, BACKOFFICE, SISTEMA)`
