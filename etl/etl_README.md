# ETL - normalizar_CSVs.py (v4, sin Kaggle2)

## Propósito
Unificar tres orígenes (Kaggle1 y dos sintéticos) normalizar campos y formatos, asignar categorías con diccionarios ES/EN y reglas contextuales, y aplicar postfix de coherencia temporal/estado para obtener un dataset final.

## Entradas y salidas
- Entradas (estructura actual):  
  - `data/s2/dataset_kaggle_english_V2.csv`  (Kaggle 1)  
  - `data/s2/tickets_soporte_sintetico.csv`  (Sintético 1)  
  - `data/s2/tickets_soporte_sintetico_2.csv` (Sintético 2: incluye ids `synt2_` y `synt3_`)

- Salidas:  
  - `data/s3/tickets_normalizados.csv` (dataset final)  
  - `data/s3/email.csv`, `portal_soporte.csv`, `portal_documental.csv`, `portal_interno.csv`  
  - `logs/normalizar_report.json` (resumen + trazas)  
  - `logs/postfix_changes.csv` (correcciones de fechas/estado)

## Requisitos
- Python 3.10+
- `pip install -r requirements.txt` (pandas, numpy)

## Ejecución
```bash
python etl/normalizar_CSVs_sin_kaggle2.py
```

## Esquema de salida
`id_ticket | canal | fecha_creacion | first_reply_at | fecha_cierre | estado | prioridad | categoria | agente_id | sla_target_horas | sla_met | resumen | descripcion`

Catálogos:  
- **canal**: {EMAIL, PORTAL_SOPORTE, PORTAL_DOCUMENTAL, PORTAL_INTERNO}  
- **estado**: {Abierto, En curso, Resuelto, Cerrado, Reabierto}  
- **prioridad**: {Crítica, Alta, Media, Baja}  
- **categoria**: {ACC, SW, HW, NET, MAIL, APP, SRV, POL}  
- **sla_met**: {true, false, ""}  
- **Fechas** ISO `YYYY-MM-DD HH:MM`.

## Clasificación de categorías
- Diccionarios ES/EN por clase (KW base + ADD refuerzos + NEG penalizaciones).
- Reglas contextuales (prefer/demote) para ambigüedades (Outlook->MAIL; Oracle/Jira/SharePoint/Power BI/ServiceNow/Webex/SCCM->APP; Defender/policy->POL; IP/DNS/VPN->NET).
- Desempate estable: ACC > MAIL > NET > HW > SW > APP > POL > SRV.
- Expresiones regulares con anclas para reducir falsos positivos.

## Post-fix de coherencia (fecha/estado)
- (0) `fecha_cierre` en el futuro -> vaciar
- (1) Estado abierto/en curso/reabierto con `fecha_cierre` -> vaciar
- (3) `fecha_cierre` < `fecha_creacion` -> vaciar
- (4) `fecha_cierre` < `first_reply_at`  
  - 4a) si cerrado/resuelto → `fecha_cierre = max(first, crea)` si posible; si no, vaciar  
  - 4b) si no cerrado -> vaciar
- (2) Estado de cierre sin `fecha_cierre` -> imputar `max(first, crea)` cuando sea posible

## Auditoría
- `logs/normalizar_report.json` -> totales por canal/categoría, impacto de diccionarios y rutas de salida.
- `logs/postfix_changes.csv` -> detalle de cada corrección temporal.

## Convenciones de identificación
- Prefijos: `kaggle1_`, `synt_`, `synt2_` (y `synt3_` si aplica). Si no hay id de origen, se usa `*_GEN{n}` por fuente.
