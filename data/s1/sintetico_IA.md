# ChatGPT — Texto para generar el CSV sintético de 5000 tickets de soporte


Quiero que generes un CSV sintético de tickets de soporte TI con ~[5000] filas, bien realista y NO trivial, cumpliendo TODAS estas condiciones y validaciones:

1) ESQUEMA Y FORMATO
- Codificación: UTF-8 (con BOM si lo vas a generar como archivo).
- Separador: ‘;’ (punto y coma).
- Cabeceras EXACTAS y en este ORDEN:
  id_ticket;canal;fecha_creacion;first_reply_at;fecha_cierre;estado;prioridad;categoria;agente_id;sla_target_horas;sla_met;resumen;descripcion
- No incluyas columnas adicionales, ni índices, ni comillas envolviendo todas las celdas.

2) TAXONOMÍA DE CATEGORÍAS (campo `categoria`)
- Usa SOLO estos códigos: ACC, SW, HW, NET, MAIL, APP, SRV, POL.
- Reparte las categorías de forma realista (no uniformes). 
  Pauta sugerida (ajústala ligeramente para parecer natural): 
  SW≈20–25%, MAIL≈15–20%, NET≈12–18%, SRV≈10–15%, APP≈10–15%, ACC≈8–12%, HW≈6–10%, POL≈3–6%.

3) CANALES (campo `canal`)
- Valores EXACTOS: EMAIL, PORTAL_SOPORTE, PORTAL_DOCUMENTAL, PORTAL_INTERNO.
- Distribución realista (EMAIL y PORTAL_SOPORTE predominan).

4) FECHAS Y COHERENCIA TEMPORAL
- `fecha_creacion`, `first_reply_at`, `fecha_cierre` en formato texto ISO `YYYY-MM-DD HH:MM` (24h).
- Rango de fechas: de [2023-01-01] a [2024-12-31], mezclando meses/días para evitar patrones.
- Reglas obligatorias por fila:
  a) `first_reply_at` >= `fecha_creacion` (mínimo +5 a +480 min aleatorio).
  b) Si `estado` ∈ {Cerrado, Resuelto} ⇒ `fecha_cierre` existe y `fecha_cierre` >= max(`fecha_creacion`,`first_reply_at`).
  c) Si `estado` ∈ {Abierto, En curso, Reabierto} ⇒ `fecha_cierre` vacío.
  d) No generar fechas futuras (más allá de hoy) ni anteriores a 2000.

5) CATÁLOGOS
- `estado` EXACTO en {Abierto, En curso, Resuelto, Cerrado, Reabierto}.
- `prioridad` EXACTA en {Crítica, Alta, Media, Baja} con distribución realista (pocas Críticas).
- `sla_target_horas`: uno de {8,24,72,120} según patrón lógico (p. ej., Crítica→8/24; Media→24/72; Baja→72/120).
- `sla_met`: EXACTO en {true,false} coherente con `sla_target_horas` y el delta de resolución (si no hay `fecha_cierre`, usar `false` con prob. alta, pero no siempre).

6) TEXTO (ES/EN mezcla, natural y coherente)
- `resumen`: 8–14 palabras, frase breve coherente con `descripcion`.
- `descripcion`: 1–3 párrafos cortos con detalles técnicos plausibles.
- Mantén coherencia entre categoría y texto. Ejemplos:
  - ACC: “no puedo iniciar sesión”, “MFA/SSO/contraseña”, “invalid credentials”.
  - SW: instalación/actualización/bug/crash; Office; drivers.
  - HW: batería/cargador/teclado/monitor/impresora.
  - NET: VPN/DNS/proxy/IP/latencia/conectividad Wi-Fi/LAN/WAN.
  - MAIL: Outlook/buzón/SMTP/IMAP/firma/listas compartidas.
  - APP: SAP/Oracle/Jira/SharePoint/Power BI/ServiceNow/Salesforce.
  - SRV: altas/bajas/“cómo hacer…”, permisos estándar, onboarding/offboarding.
  - POL: antivirus/Defender/malware/cifrado/DLP/bloqueos por política.
- Evita frases absurdas (“VPN al adjuntar PDF”), duplicidades y ruido (#123 en resumen, etc.).
- Mezcla ES/EN con naturalidad (p. ej., términos técnicos en EN).

7) ID Y AGENTE
- `id_ticket`: prefijos variados como synt_INCnnnnn/synt_TASKnnnnn (no colisiones).
- `agente_id`: Agent-1..Agent-5 (distribución desigual).

8) DISTRIBUCIONES Y VARIEDAD
- Evita patrones obvios (mismos minutos siempre, mismas palabras). Introduce sinónimos, abreviaturas, y ligeras faltas realistas (no ortografía inventada).
- Incluye adjuntos mencionados en el texto sin crear columnas (p. ej., “adjunto captura”).

9) VALIDACIONES FINALES (imprescindibles)
- Ningún registro incumple las reglas del punto 4.
- Los 13 campos están presentes en todas las filas.
- No hay `id_ticket` duplicados.

10) ENTREGA
- Devuélveme el archivo como bloque descargable (CSV) y un breve resumen de conteos por `categoria` y `canal`.
