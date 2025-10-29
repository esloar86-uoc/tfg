# MAPPING.md · Orígenes → Esquema canónico

Mapeo utilizado por `etl/normalizar_CSVs.py` con la estructura `data/s2` (entradas) y `data/s3` (salidas).

## 1. dataset_kaggle_english_V2.csv (data/s2/)
No contiene canal explícito. Se infiere por heurística textual.

| Origen            | Destino         | Regla                   |
|-------------------|-----------------|-------------------------|
| number            | id_ticket       | Si falta → kaggle1_GEN# |
| date              | fecha_creacion  | Parseo flexible -> ISO  |
| short_description | resumen         | —                       |
| content           | descripcion     | —                       |
| status / state    | estado          | A catálogo              |
| priority          | prioridad       | A catálogo              |
| resolved_at       | fecha_cierre    | A ISO                   |
| —                 | first_reply_at  | Vacío                   |
| —                 | sla_target_horas| Vacío                   |
| —                 | sla_met         | Vacío                   |
| agent / assignee  | agente_id       | —                       |

Heurística de canal (texto en resumen/descripcion):
    EMAIL si hay @ o términos de correo
    DOCUMENTAL si documentation/manual/knowledge base/kb/documentación
    INTERNO si phone/call/legal/agent/internal
    Otro caso SOPORTE.

## 2. dataset_kaggle_english_2_V2.csv (data/s2/)

| Origen               | Destino        | Regla         |
|----------------------|----------------|---------------|
| Ticket ID            | id_ticket      | —             |
| Ticket Channel       | canal          | Email->EMAIL; Chat->PORTAL_SOPORTE; Phone->PORTAL_INTERNO; Social media->PORTAL_DOCUMENTAL |
| creation_date        | fecha_creacion | Parseo → ISO  |
| First Response Time  | first_reply_at | Parseo → ISO  |
| Ticket Status        | estado         | A catálogo    |
| Ticket Priority      | prioridad      | A catálogo    |
| Ticket Subject       | resumen        | —             |
| Ticket Description   | descripcion    | —             |
| Resolved At          | fecha_cierre   | Parseo ->ISO si existe |

## 3. tickets_soporte_sintetico.csv (data/s2/)

| Origen                                        | Destino     | Regla               |
|-----------------------------------------------|-------------|---------------------|
| id_ticket                                     | id_ticket   | —                   |
| canal                                         | canal       | Normalización a EMAIL/PORTAL_SOPORTE/PORTAL_DOCUMENTAL/PORTAL_INTERNO |
| fecha_creacion, first_reply_at, fecha_cierre  | Homónimos   | ISO                 |
| estado, prioridad, categoria, agente_id, sla_target_horas, sla_met, resumen, descripcion | Homónimos | — |


## 4. Reglas de categorización
- Texto base: resumen + " | " + descripcion
- Puntuación: KW (+1.0), ADD (+1.5), NEG (−1.0)
- Reglas contextuales: Outlook->MAIL; Oracle/Jira/SharePoint/Power BI/ServiceNow/Webex/SCCM->APP; Defender/policy->POL; IP/DNS/VPN/Proxy/Router/Switch/Latency->NET
- Desempate: ACC > MAIL > NET > HW > SW > APP > POL > SRV

## 5. Postfix de coherencia
0, 1, 3, 4a, 4b, 2 (detalles en README de ETL).

## 6. Alias de cabeceras (extracto)
id_ticket: ticket_id, number, id, issue_id  
canal: channel, ticket_channel  
fecha_creacion: date, created_at, creation_date  
first_reply_at: first_response_time, first_response  
fecha_cierre: resolved_at, closed_at, resolution_date  
estado: status, state  
prioridad: priority, ticket_priority  
categoria: category, ticket_type, product_purchased  
agente_id: agent, agent_id, assignee, owner  
sla_target_horas: sla_target_hours, sla_target  
sla_met: sla_met, sla_ok  
resumen: subject, short_description, ticket_subject  
descripcion: content, description, ticket_description, body

## 7. Validaciones
- Total esperado: 41.071
- id_ticket sin duplicados
- Fechas ISO coherentes (postfix aplicado)
- categorias: ACC, SW, HW, NET, MAIL, APP, SRV, POL
- Los cuatro valores de canal presentes
