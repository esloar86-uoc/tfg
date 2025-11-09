
# Prompt reproducible — Dataset sintético de tickets TI (1.000 filas)

**Objetivo:** generar con Python un CSV de **1.000 tickets de soporte TI** realistas, cumpliendo reglas estrictas de esquema, coherencia temporal, SLA y originalidad de textos (sin frases repetidas). El asistente debe validar con aserciones y devolver el archivo descargable + conteos. Cuando se ha conseguido un dataset estable, se ha pedido a la IA: `"Necesito que me digas exactamente el texto/prompt que debería ponerte en una nueva ventana donde no tengas acceso al historial de mi cuenta, qué debería de ponerte para que saques exactamente un CSV como este, con estas mismas características"`

---

## PROMPT

Quiero que generes con Python un dataset sintético de **tickets de soporte TI** con **1000 filas** y me entregues el **archivo CSV descargable**. Sigue estas reglas **al pie de la letra** y valida con aserciones antes de guardar. Si alguna validación falla, regenera lo mínimo necesario hasta cumplir todo. Usa una semilla fija (`random.seed(30303)`, `np.random.seed(30303)`) para reproducibilidad.

### 1) Salida (formato)
- Codificación: **UTF-8 con BOM**.
- Separador: **;** (punto y coma).
- **Sin** índice y **sin** comillas envolviendo todas las celdas.
- Cabeceras **exactas** y en este **orden**:  
  `id_ticket;canal;fecha_creacion;first_reply_at;fecha_cierre;estado;prioridad;categoria;agente_id;sla_target_horas;sla_met;resumen;descripcion`
- Reemplaza cualquier **;** que aparezca dentro de los textos por coma.

### 2) Distribuciones y catálogos
- `categoria` ∈ {ACC, SW, HW, NET, MAIL, APP, SRV, POL}. Reparte de forma realista (no uniforme):  
  **SW≈20–25%**, **MAIL≈15–20%**, **NET≈12–18%**, **SRV≈10–15%**, **APP≈10–15%**, **ACC≈8–12%**, **HW≈6–10%**, **POL≈3–6%**.
- `canal` ∈ {EMAIL, PORTAL_SOPORTE, PORTAL_DOCUMENTAL, PORTAL_INTERNO}, con **EMAIL** y **PORTAL_SOPORTE** predominantes.
- `estado` ∈ {Abierto, En curso, Resuelto, Cerrado, Reabierto}.
- `prioridad` ∈ {Crítica, Alta, Media, Baja} (pocas **Crítica**).
- `agente_id` ∈ {Agent-1..Agent-5} con distribución desigual (Agent-1/2 más frecuentes).
- `sla_target_horas` ∈ {8,24,72,120} según prioridad: **Crítica→8/24**, **Alta→24/72**, **Media→24/72**, **Baja→72/120**.

### 3) Fechas y coherencia temporal
- Formato texto ISO **YYYY-MM-DD HH:MM** (24h).
- Rango: de **2023-01-01** a **2024-12-31** (mezcla meses/días para evitar patrones).
- Reglas por fila:  
  a) `first_reply_at` ≥ `fecha_creacion` (**+5 a +480 min** aleatorio).  
  b) Si `estado` ∈ {Cerrado, Resuelto} ⇒ `fecha_cierre` existe y `fecha_cierre` ≥ max(`fecha_creacion`,`first_reply_at`).  
  c) Si `estado` ∈ {Abierto, En curso, Reabierto} ⇒ `fecha_cierre` vacío.  
  d) No generar fechas futuras ni anteriores a 2000.

### 4) SLA
- Calcula `sla_met` ∈ {true,false} comparando el tiempo desde `fecha_creacion` hasta `fecha_cierre` con `sla_target_horas`.  
- Si no hay `fecha_cierre` (estados abiertos), `sla_met` será mayoritariamente **false** (no siempre, para simular casos atípicos).

### 5) Identificadores
- `id_ticket` único con prefijos variados: **synt_INCnnnnn** y **synt_TASKnnnnn** (sin colisiones).  
- `agente_id` como arriba.

### 6) Texto natural (primera persona, ES/EN)
- **Un idioma por ticket** (≈90% ES / 10% EN). Nada de “spanglish”.
- `resumen`: **8–14 palabras**, breve y coherente con `descripcion`.
- `descripcion`: **1–3 frases** cortas (sin pasos de resolución). Puede mencionar adjuntos (“Adjunto captura…”).
- **Coherencia estricta:** resumen y descripción salen del **mismo escenario** (tema único).
- **Variedad fuerte:** evita plantillas repetidas; alterna sinónimos, conectores y calificadores (“a ratos”, “intermitente”, “desde ayer”…). Lugar/hora **solo a veces**.
- **Prohibido repetir**:  
  - Ningún `resumen` repetido.  
  - Ninguna `descripcion` repetida **como texto completo**.  
  - Además, **ninguna oración** de la columna `descripcion` debe repetirse literalmente en otra fila (lleva un `set` global de oraciones y **refrasea** si choca).
- **Pistas por categoría (no exhaustivas):**  
  - **ACC:** inicio de sesión / contraseña / bloqueo / MFA / SSO / credenciales VPN.  
  - **SW:** instalación/actualización/bug/crash; Office; drivers.  
  - **HW:** ratón/teclado/monitor/dock/impresora/batería.  
  - **NET:** VPN/DNS/proxy/IP/latencia/Wi‑Fi/LAN.  
  - **MAIL:** Outlook/OWA/IMAP/SMTP/firma/buzón compartido/reglas.  
  - **APP:** SAP/Oracle/Jira/SharePoint/Power BI/ServiceNow/Salesforce (roles, permisos, informes).  
  - **SRV:** altas/bajas, permisos estándar, listas de distribución, licencias, renovación de equipo.  
  - **POL:** antivirus/Defender, DLP, BitLocker, proxy riesgo, Intune/compliance.  
- Evita contradicciones (“desde casa” vs “en la oficina” en la misma fila).

### 7) Validaciones obligatorias (antes de guardar)
- 1000 filas × 13 columnas presentes.
- `id_ticket` **único**.
- `resumen` **único** y `descripcion` **única**; y **sin oraciones repetidas** entre descripciones.
- Comprobaciones de fechas/estados del punto 3.
- `sla_met` coherente con `sla_target_horas` y delta de resolución.
- Reemplaza “;” en los textos por coma.

### 8) Entrega
1. Guarda el CSV como **tickets_soporte_sinteticos_1000.csv** (UTF-8 con BOM, separador `;`).  
2. Muestra un **resumen de conteos** por `categoria` y por `canal`.  
3. Devuélveme el **enlace de descarga** del CSV.

> Implementa todo en un **único script de Python** dentro de la sesión, con aserciones que aborten si se incumple algo y con lógica de **re‑fraseo** para evitar repeticiones de oraciones. Mantén una semilla fija para reproducibilidad.
