#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizar_CSVs_v3_nosup.py
================================================================

OBJETIVO
--------
Unificar tres orígenes heterogéneos de tickets (dos Kaggle + uno sintético),
normalizar sus campos y formatos, asignar una categoría según una taxonomía
de 8 clases usando diccionarios internos (ES/EN) y reglas contextuales,
y aplicar una revisión final (fechas/estado) para obtener un CSV
listo para aprendizaje supervisado.

PUNTOS CLAVE
------------
1) Entrada: rutas en `data/`.
2) Normalización: cabeceras (aliases), fechas a `YYYY-MM-DD HH:MM`,
   estado/prioridad a catálogos cerrados, `sla_met` a `{true,false,""}`.
3) Categorización: por keywords con pesos y reglas contextuales (ES/EN).
4) Postfix: 4 reglas de coherencia entre fechas y estado (ver función
   `_postfix_dates_states`).
5) Salidas: `data/s3/tickets_normalizados.csv` y cortes por canal, reporte
   en `logs/normalizar_report.json` y log detallado de postfix en
   `logs/postfix_changes.csv`.

"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


# -----------------------------------------------------------------------------
# RUTAS Y CONSTANTES GENERALES
# -----------------------------------------------------------------------------

ROOT: Path = Path(".").resolve()

# Entradas
KAGGLE_ORIGEN1: Path = ROOT / "data" / "s2" / "dataset_kaggle_english_V2.csv"
KAGGLE_ORIGEN2: Path = ROOT / "data" / "s2" / "dataset_kaggle_english_2_V2.csv"
SINTETICO:      Path = ROOT / "data" / "s2" / "tickets_soporte_sintetico.csv"

# Salidas
OUT_DIR:  Path = ROOT / "data" / "s3"; OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR: Path = ROOT / "logs";        LOGS_DIR.mkdir(parents=True, exist_ok=True)

OUT_ALL: Path = OUT_DIR / "tickets_normalizados.csv"
OUT_BY_CHANNEL: Dict[str, Path] = {
    "EMAIL":             OUT_DIR / "email.csv",
    "PORTAL_SOPORTE":    OUT_DIR / "portal_soporte.csv",
    "PORTAL_DOCUMENTAL": OUT_DIR / "portal_documental.csv",
    "PORTAL_INTERNO":    OUT_DIR / "portal_interno.csv",
}
REPORT_PATH: Path = LOGS_DIR / "normalizar_report.json"
POSTFIX_LOG: Path  = LOGS_DIR / "postfix_changes.csv"

# Esquema mínimo esperado en la salida. Si faltasen columnas en origen,
# se crean vacías para evitar errores y asegurar consistencia.
CAMPOS_FINALES: List[str] = [
    "id_ticket","canal","fecha_creacion","first_reply_at","fecha_cierre",
    "estado","prioridad","categoria","agente_id","sla_target_horas","sla_met",
    "resumen","descripcion"
]

# Mapeo de aliases (nombres alternativos) -> nombre canónico. 
ALIASES_MAP: Dict[str, str] = {k:k for k in CAMPOS_FINALES}
ALIASES_MAP.update({
    "ticket_id":"id_ticket","number":"id_ticket",
    "channel":"canal","contact_type":"canal","ticket_channel":"canal",
    "date":"fecha_creacion","created_at":"fecha_creacion","creation_date":"fecha_creacion","open_date":"fecha_creacion","created":"fecha_creacion",
    "first_response_time":"first_reply_at","first_response":"first_reply_at","response_time":"first_reply_at","first_contact_date":"first_reply_at",
    "resolved_at":"fecha_cierre","time_to_resolution":"fecha_cierre","closed_at":"fecha_cierre","resolution_date":"fecha_cierre","close_date":"fecha_cierre","resolved":"fecha_cierre",
    "status":"estado","ticket_status":"estado","state":"estado",
    "priority":"prioridad","ticket_priority":"prioridad",
    "agent":"agente_id","agent_id":"agente_id","assignee":"agente_id","owner":"agente_id",
    "sla_target_hours":"sla_target_horas","sla_target":"sla_target_horas",
    "subject":"resumen","short_description":"resumen","ticket_subject":"resumen",
    "content":"descripcion","description":"descripcion","ticket_description":"descripcion","body":"descripcion"
})

# Conjuntos de encodings. Muchos CSV pueden venir en cp1252/latin-1
# o con BOM (utf‑8‑sig). Se probará en orden hasta que uno funcione.
CODIGOS: List[str] = ["utf-8","utf-8-sig","latin-1","cp1252","utf-16","utf-16le","utf-16be"]


# -----------------------------------------------------------------------------
# DICCIONARIOS PARA CATEGORIZACIÓN (ES/EN)
# -----------------------------------------------------------------------------
# La etiqueta `categoria` se decide por:
#   1) Coincidencias de keywords base (peso = 1.0),
#   2) Términos de refuerzo en “ADD” (peso = +1.5),
#   3) Penalizaciones en “NEG” (peso = −1.0),
#   4) Reglas contextuales para casos ambiguos.
# Después de puntuar, si hay empate, se desempatan con `CAT_ORDER` (orden estable).

KW: Dict[str, List[str]] = {
    "ACC": [
        "login","inicio de sesión","iniciar sesion","autenticación","autenticacion","sso","mfa","2fa",
        "contraseña","contrasena","restablecer contraseña","cambiar contraseña","olvidé la contraseña","olvide la contrasena",
        "cuenta bloqueada","desbloquear cuenta","permiso denegado","acceso denegado",
        "credentials","credenciales","password","reset password","forgot password","account locked","access denied"
    ],
    "SW": [
        "instalar","instalación","instalacion","reinstalar","actualización","actualizacion","parche","licencia","serial",
        "driver","software","aplicación de escritorio","aplicacion de escritorio","desinstalar","update","patch",
        "license","product key","desktop app","uninstall","upgrade","downgrade","bug","error","crash"
    ],
    "HW": [
        "hardware","portátil","portatil","laptop","equipo","pc","teclado","ratón","raton","mouse","monitor","pantalla",
        "impresora","scanner","escáner","escaner","webcam","auriculares","ssd","disco","batería","bateria",
        "cargador","charger","dock","docking station","keyboard","display","printer","headset","battery"
    ],
    "NET": [
        "vpn","wi fi","wifi","red","conexión","conexion","conectividad","lan","wan","proxy","dns","ip","gateway","ping",
        "latencia","pérdida de paquetes","perdida de paquetes","cable de red","ethernet","switch","router",
        "network","connection","connectivity","packet loss","no internet","high latency"
    ],
    "MAIL": [
        "correo","email","buzón","buzon","outlook","exchange","smtp","imap","pop3","calendario","meeting","invite",
        "firma","signature","alias","mailbox","ndr","bounce","delivery failed","o365","microsoft 365"
    ],
    "APP": [
        "sap","erp","crm","bpm","salesforce","dynamics","navision","sage","jira","confluence",
        "power bi","sharepoint","servicenow","oracle","oracle database","oracle db","workday","netsuite","odoo","sccm","webex"
    ],
    "SRV": [
        "alta","baja","solicito","solicitud","petición","peticion","permiso de acceso","como hago","manual","procedimiento",
        "crear usuario","dar de alta","cambio planificado","aprobar","provisionar","provision","request",
        "new user","onboarding","offboarding","how to","grant access","please provide","standard change","service request","access to"
    ],
    "POL": [
        "antivirus","phishing","malware","ransomware","cifrado","encriptado","bloqueado por política","bloqueado por politica",
        "dlp","firewall","política de seguridad","politica de seguridad","seguridad","quarantine","blocked for security",
        "encryption","security policy","microsoft defender","windows defender","endpoint protection","network policy","policy"
    ],
}

# Refuerzos: términos que, si aparecen, empujan más hacia la categoría indicada.
ADD: Dict[str, List[str]] = {
    "ACC": ["active directory","otp","one time code","codigo mfa","codigo otp","failed login","invalid credentials"],
    "MAIL": ["shared mailbox","distribution list","delegation","ndr","delivery failed","auto-reply","out of office"],
    "NET": ["ip address","dns server","proxy auth","802.1x","ssid","packet drop","routing","no internet access"],
    "APP": ["sap gui","s 4hana","salesforce lightning","dynamics 365","sharepoint site","jira project","power bi dataset","webex app","configuration manager"],
    "POL": ["blocked by policy","security incident","threat detected","quarantined","bitlocker","filevault"],
    "HW":  ["battery not charging","ac adapter","power adapter","keyboard not working","screen flicker","paper jam"],
    "SW":  ["deprecated","obsolete feature","missing license","product activation","runtime error","dll"],
    "SRV": ["grant access to","please grant","need access","how do i","procedure steps"]
}

# Penalizaciones: términos cuya presencia restará puntuación a la categoría.
NEG: Dict[str, List[str]] = {
    "ACC": ["outlook","imap","smtp"],
    "MAIL": ["vpn","dns","proxy"],
    "NET": ["outlook","mailbox"],
    "APP": ["printer","monitor","battery"],
    "HW":  ["oracle","sharepoint","jira"],
    "SW":  ["oracle","sccm","webex","jira"],
    "POL": ["printer","monitor"]
}

# Pesos de las señales.
W_HIT: float = 1.0
W_ADD: float = 1.5
W_NEG: float = -1.0

# Reglas contextuales: si aparecen ciertos términos (“if_any”), preferimos una
# categoría y “degradamos” otras. Útil para casos ambiguos.
REGLAS_CONTEXTUALES: List[dict] = [
    {"if_any": ["outlook","mailbox","imap","smtp","email"], "prefer": "MAIL", "demote": ["ACC"], "boost": 0.5, "force": False},
    {"if_any": ["oracle","oracle database","sharepoint","jira","confluence","power bi","servicenow","sccm","webex"], "prefer": "APP", "demote": ["SW","HW"], "boost": 0.7, "force": False},
    {"if_any": ["defender","endpoint protection","security policy","network policy","blocked by policy","quarantine"], "prefer": "POL", "demote": ["NET","SW"], "boost": 0.7, "force": False},
    {"if_any": ["ip address","dns","vpn","proxy","router","switch","packet loss","latency"], "prefer": "NET", "demote": ["MAIL","SRV"], "boost": 0.5, "force": False},
]

# Orden estable de desempate entre categorías cuando las puntuaciones empatan.
CAT_ORDER: List[str] = ["ACC","MAIL","NET","HW","SW","APP","POL","SRV"]


# -----------------------------------------------------------------------------
# UTILIDADES DE LECTURA Y NORMALIZACIÓN BÁSICA
# -----------------------------------------------------------------------------

def _normalize_col(col: str) -> str:
    """
    Normaliza nombres de columnas:
      - elimina BOM/tildes,
      - reemplaza separadores por "_",
      - devuelve en minúsculas.
    Permite comparar con `ALIASES_MAP` sin depender del formato original.
    """
    if col is None: 
        return ""
    s = str(col).replace("\ufeff","")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Za-z0-9]+","_", s.strip()).strip("_").lower()
    return s


def _read_csv_any(path: Path) -> pd.DataFrame:
    """
    Lector de CSV:
      1) prueba múltiples encodings (ver `CODIGOS`),
      2) intenta deducir el separador con `csv.Sniffer` (entre `; , | \\t`),
      3) carga con `dtype=str` y sin NAs.
    """
    last = None
    import csv as _csv
    for enc in CODIGOS:
        try:
            sample = path.read_text(encoding=enc, errors="strict")[:4096]
        except Exception as e:
            last = e; continue
        try:
            sep = _csv.Sniffer().sniff(sample, delimiters=";,|\t").delimiter
        except Exception:
            sep = "," if sample.count(",") >= sample.count(";") else ";"
        try:
            return pd.read_csv(path, sep=sep, encoding=enc, dtype=str, keep_default_na=False, engine="python")
        except Exception as e:
            last = e; continue
    raise last or RuntimeError(f"Imposible leer {path}")


def _rename_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica el mapeo de aliases a nombres canónicos. Si tras renombrar
    quedan columnas duplicadas, se combina tomando la primera no vacía por fila.
    """
    mapping = {}
    for c in df.columns:
        key = _normalize_col(c)
        if key in ALIASES_MAP:
            mapping[c] = ALIASES_MAP[key]

    out = df.rename(columns=mapping).copy()

    # Combinar duplicadas
    dup = out.columns.duplicated(keep=False)
    if dup.any():
        names = list(dict.fromkeys(out.columns[dup]))
        for n in names:
            iguales = out.loc[:, out.columns == n].astype(str)
            combinado = (iguales.replace(r"^\s*$", pd.NA, regex=True)
                               .bfill(axis=1)
                               .iloc[:, 0]
                               .fillna(""))
            out = out.drop(columns=[c for c in out.columns if c == n])
            out[n] = combinado
    return out


def _to_iso(s: str) -> str:
    """
    Normaliza fechas a `YYYY-MM-DD HH:MM`. Intenta varios formatos frecuentes y
    como último recurso usa `pandas.to_datetime`. Si no puede, devuelve "".
    """
    if s is None: 
        return ""
    s = str(s).strip()
    if s == "": 
        return ""
    # Intento directo ISO
    if "T" in s:
        try:
            ss = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ss)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    # Intentos por patrones comunes
    fmts = ["%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S","%d/%m/%Y %H:%M","%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S","%m/%d/%Y %H:%M","%m/%d/%Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    # Último recurso
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return "" if pd.isna(dt) else dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _low(s: str) -> str:
    """Minúsculas sin espacios."""
    return (str(s) if s is not None else "").strip().lower()


# --- Mapeos de catálogos heterogéneos a valores canónicos ---

def _map_canal_k1(v: str) -> str:
    """Mapeo específico del dataset Kaggle 1 -> catálogo de canales interno."""
    t = _low(v)
    if t in {"chat","self-service","self service"}: return "PORTAL_SOPORTE"
    if t in {"mail","email"}: return "EMAIL"
    if t in {"phone"}: return "PORTAL_INTERNO"
    return "PORTAL_SOPORTE"


def _map_canal_k2(v: str) -> str:
    """Mapeo específico del dataset Kaggle 2 -> catálogo de canales interno."""
    t = _low(v)
    if t == "chat": return "PORTAL_SOPORTE"
    if t == "email": return "EMAIL"
    if t == "phone": return "PORTAL_INTERNO"
    if t == "social media": return "PORTAL_SOPORTE"
    return "PORTAL_SOPORTE"


def _map_priority(v: str) -> str:
    """Normaliza prioridad a Crítica, Alta, Media, Baja."""
    t = _low(v)
    if t in {"critical","critica","crítica","p1"}: return "Crítica"
    if t in {"high","alta","urgent","p2"}:        return "Alta"
    if t in {"medium","media","normal","p3"}:     return "Media"
    if t in {"low","baja","minor","p4"}:          return "Baja"
    return "Media"


def _map_state(v: str) -> str:
    """Normaliza estado a catálogo cerrado y consistente."""
    t = _low(v)
    if t in {"open","abierto","pendiente","new"}:               return "Abierto"
    if t in {"in progress","en progreso","en curso","working"}: return "En curso"
    if t in {"resolved","resuelto"}:                            return "Resuelto"
    if t in {"closed","cerrado","done"}:                        return "Cerrado"
    if t in {"reopened","reabierto"}:                           return "Reabierto"
    return "Abierto"


def _norm_sla(v: str) -> str:
    """
    Limpia `sla_met` a {true,false,""}:
      - elimina apóstrofes y variantes tipo Excel,
      - mapea alias (sí/no, 1/0, verdadero/falso).
    """
    s = ("" if v is None else str(v)).strip().lower().replace('="','').replace('"','').lstrip("'")
    if s in {"true","verdadero","v","1","yes","y"}:  return "true"
    if s in {"false","falso","f","0","no","n"}:      return "false"
    return ""


# -----------------------------------------------------------------------------
# CLASIFICACIÓN POR EXPR. REGULARES (KEYWORDS + REGLAS)
# -----------------------------------------------------------------------------

def _normalize_for_regex(token: str) -> str:
    """Quita tildes y convierte espacios en `\\s+` para cuadrar variantes.”"""
    t = "".join(c for c in unicodedata.normalize("NFD", token) if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", r"\\s+", t.strip())
    return t


# Pre‑compilar patrones (mejora rendimiento en bucles por fila).
PAT_BASE = {
    cat: [re.compile(rf"(?<!\w){_normalize_for_regex(tok)}(?!\w)", flags=re.I) for tok in toks]
    for cat, toks in KW.items()
}
PAT_ADD = {cat: [re.compile(rf"(?<!\w){_normalize_for_regex(tok)}(?!\w)", flags=re.I) for tok in toks] for cat, toks in ADD.items()}
PAT_NEG = {cat: [re.compile(rf"(?<!\w){_normalize_for_regex(tok)}(?!\w)", flags=re.I) for tok in toks] for cat, toks in NEG.items()}


def _score_text(text: str) -> Tuple[Dict[str, float], int, int]:
    """
    Devuelve:
      - scores: puntuación por categoría tras aplicar keywords base, ADD y NEG,
      - add_hit: nº de impactos ADD,
      - neg_hit: nº de impactos NEG.

    Nota: se usa regex con anclas de palabra para evitar falsos positivos en
    subcadenas (“mail” dentro de “examplemail” por ejemplo).
    """
    t = "".join(c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn")
    scores: Dict[str, float] = {c:0.0 for c in KW.keys()}
    add_hit = 0
    neg_hit = 0

    # Keywords base
    for cat, plist in PAT_BASE.items():
        for p in plist:
            if p.search(t): 
                scores[cat] += W_HIT

    # Refuerzos
    for cat, plist in PAT_ADD.items():
        for p in plist:
            if p.search(t): 
                scores[cat] += W_ADD
                add_hit += 1

    # Penalizaciones
    for cat, plist in PAT_NEG.items():
        for p in plist:
            if p.search(t): 
                scores[cat] += W_NEG
                neg_hit += 1

    return scores, add_hit, neg_hit


def _aplicar_reglas_contexto(text: str, scores: Dict[str, float]) -> Dict[str, float]:
    """
    Si el texto contiene términos de `if_any`, se potencia `prefer` y se
    degradan categorías de `demote`. Si `force=True`, fuerza que `prefer`
    quede por encima de cualquier otra puntuación.
    """
    t = "".join(c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn").lower()
    s = scores.copy()
    for regla in REGLAS_CONTEXTUALES:
        if any(tok in t for tok in regla["if_any"]):
            pref   = regla.get("prefer")
            demote = regla.get("demote", [])
            boost  = float(regla.get("boost", 0.0))
            force  = bool(regla.get("force", False))

            if pref:
                s[pref] = s.get(pref, 0.0) + boost
                if force:
                    # Forzar “prefer” por encima del resto
                    for c in s.keys():
                        if c != pref: 
                            s[c] = min(s[c], s[pref] - 1e-6)

            for c in demote:
                s[c] = s.get(c, 0.0) - (boost/2.0)
    return s


def _decide(scores: Dict[str, float]) -> str:
    """
    Devuelve la categoría ganadora tras puntuación y reglas.
    Si todas las puntuaciones son menor o = 0 -> asigna SRV (cajón seguro).
    En caso de empate usa `CAT_ORDER`.
    """
    mv = max(scores.values()) if scores else 0.0
    if mv <= 0.0:
        return "SRV"
    cands = [c for c,v in scores.items() if abs(v - mv) < 1e-12]
    for c in CAT_ORDER:
        if c in cands: 
            return c
    return "SRV"


# -----------------------------------------------------------------------------
# NORMALIZACIÓN POR FUENTE + CATEGORIZACIÓN
# -----------------------------------------------------------------------------

def _build_final_id(source_name: str, original_id: str, row_index: int) -> str:
    """
    Construye un id final “origen_idOriginal”; si no hay id original,
    genera uno sintético reproducible (`*_GEN{n}`).
    """
    orig = (original_id or "").strip()
    if orig == "":
        if source_name == "kaggle_1": return f"kaggle1_GEN{row_index+1}"
        if source_name == "kaggle_2": return f"kaggle2_GEN{row_index+1}"
        return f"synt_GEN{row_index+1}"
    prefix = "kaggle1_" if source_name == "kaggle_1" else ("kaggle2_" if source_name == "kaggle_2" else "synt_")
    return f"{prefix}{orig}"


def _normalize_source(path: Path, fuente: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Lee y normaliza origen:
      - aplica aliases,
      - mapea canal/estado/prioridad,
      - normaliza fechas y `sla_met`,
      - genera `id_ticket` final,
      - asigna `categoria` por diccionarios + reglas,
      - devuelve (dataframe_normalizado, stats_de_puntuación).
    """
    df_raw = _read_csv_any(path)
    df = _rename_cols(df_raw)

    # Garantizar columnas (si faltan en la fuente -> columnas vacías)
    for c in CAMPOS_FINALES:
        if c not in df.columns: 
            df[c] = ""

    # Canal: algunos orígenes codifican distinto; se normaliza por fuente
    if fuente == "kaggle_1":
        df["canal"] = df["canal"].apply(_map_canal_k1)
    elif fuente == "kaggle_2":
        df["canal"] = df["canal"].apply(_map_canal_k2)

    # Si el texto menciona documentación/KB -> Portal Documental
    full_txt = (df.get("resumen","").astype(str) + " " + df.get("descripcion","").astype(str))
    re_doc = re.compile(r"\b(?:documentation|manual|knowledge\s*base|kb|documentaci[oó]n)\b", re.I)
    df.loc[full_txt.str.contains(re_doc, na=False), "canal"] = "PORTAL_DOCUMENTAL"

    # Normalizaciones básicas
    df["prioridad"]      = df["prioridad"].apply(_map_priority)
    df["estado"]         = df["estado"].apply(_map_state)
    df["fecha_creacion"] = df["fecha_creacion"].apply(_to_iso)
    df["first_reply_at"] = df["first_reply_at"].apply(_to_iso)
    df["fecha_cierre"]   = df["fecha_cierre"].apply(_to_iso)
    df["sla_met"]        = df["sla_met"].apply(_norm_sla)

    # ID final
    base_ids = df.get("id_ticket","").astype(str).tolist()
    ids = [ _build_final_id(fuente, orig, i) for i, orig in enumerate(base_ids) ]
    df["id_ticket"] = pd.Series(ids, index=df.index)

    # Categorización por texto (resumen + descripción)
    cats: List[str] = []
    add_rows = 0
    neg_rows = 0
    ctx_rows = 0
    for _, r in df.iterrows():
        text = f"{r.get('resumen','')} | {r.get('descripcion','')}"
        scores, add_hit, neg_hit = _score_text(text)
        scores2 = _aplicar_reglas_contexto(text, scores)
        if scores2 != scores: 
            ctx_rows += 1
        cats.append(_decide(scores2))
        if add_hit > 0: 
            add_rows += 1
        if neg_hit > 0: 
            neg_rows += 1

    df["categoria"] = cats
    df = df[CAMPOS_FINALES].copy()

    stats = {"filas_con_add": int(add_rows), "filas_con_neg": int(neg_rows), "filas_ajustadas_por_reglas": int(ctx_rows)}
    return df, stats


# -----------------------------------------------------------------------------
# POSTFIX DE COHERENCIA EN FECHAS/ESTADO
# -----------------------------------------------------------------------------

OPEN_STATES_ES   = {"Abierto","En curso","Reabierto"}
CLOSED_STATES_ES = {"Cerrado","Resuelto"}


def _parse_dt_series(s: pd.Series) -> pd.Series:
    """
    Convierte una serie de strings a datetime. Primero intenta el
    formato objetivo, si falla y detecta dígitos, hace un intento final.
    """
    s3 = pd.to_datetime(s, format="%Y-%m-%d %H:%M", errors="coerce")
    mask = s3.isna() & s.astype(str).str.contains(r"\d", regex=True)
    if mask.any():
        s3.loc[mask] = pd.to_datetime(s.loc[mask], errors="coerce")
    return s3


def _fmt_iso(dt: pd.Series) -> pd.Series:
    """Formatea una serie datetime a `YYYY-MM-DD HH:MM`, manteniendo vacíos."""
    return dt.dt.strftime("%Y-%m-%d %H:%M").fillna("")


def _postfix_dates_states(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica 4 reglas de coherencia entre fechas y estado, registrando todas
    las correcciones en `logs/postfix_changes.csv`:

    0) `fecha_cierre` en futuro -> vaciar.
    1) Estado abierto/en curso/reabierto + `fecha_cierre` presente -> vaciar.
    3) `fecha_cierre` < `fecha_creacion` -> vaciar.
    4) `fecha_cierre` < `first_reply_at`:
       4a) Si estado Cerrado/Resuelto -> `fecha_cierre = max(first, crea)` si existe;
           en caso contrario -> vaciar.
       4b) Si estado NO es de cierre -> vaciar.

    Además, si el estado es Cerrado/Resuelto y la `fecha_cierre` está vacía,
    se imputa `fecha_cierre = max(first_reply_at, fecha_creacion)` cuando sea posible.
    """
    out = df.copy()

    crea  = _parse_dt_series(out["fecha_creacion"])
    first = _parse_dt_series(out["first_reply_at"])
    close = _parse_dt_series(out["fecha_cierre"])
    estado = out["estado"].astype(str)

    changes = []  # Aquí todas las modificaciones para auditar
    now = pd.Timestamp.now()

    # Regla 0: fecha_cierre en el futuro -> vaciar
    maskA = close.notna() & (close > now)
    if maskA.any():
        for _id, before in zip(out.loc[maskA, "id_ticket"], _fmt_iso(close[maskA])):
            changes.append({"id_ticket": _id, "regla": "A_future_close_cleared", "antes_fecha_cierre": before, "despues_fecha_cierre": ""})
        close.loc[maskA] = pd.NaT

    # Regla 1: abierto/en curso/reabierto + fecha_cierre -> vaciar
    mask1 = estado.isin(OPEN_STATES_ES) & close.notna()
    if mask1.any():
        for _id, before in zip(out.loc[mask1, "id_ticket"], _fmt_iso(close[mask1])):
            changes.append({"id_ticket": _id, "regla": "1_open_with_close_cleared", "antes_fecha_cierre": before, "despues_fecha_cierre": ""})
        close.loc[mask1] = pd.NaT

    # Regla 3: cierre < creación -> vaciar
    mask3 = close.notna() & crea.notna() & (close < crea)
    if mask3.any():
        for _id, before in zip(out.loc[mask3, "id_ticket"], _fmt_iso(close[mask3])):
            changes.append({"id_ticket": _id, "regla": "3_close_before_creation_cleared", "antes_fecha_cierre": before, "despues_fecha_cierre": ""})
        close.loc[mask3] = pd.NaT

    # Regla 4: cierre < first_reply_at
    mask4 = close.notna() & first.notna() & (close < first)
    # 4a) Si cerrado/resuelto -> fix a max(first, crea) si existe; si no, vaciar
    mask4a = mask4 & estado.isin(CLOSED_STATES_ES)
    if mask4a.any():
        target = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
        target.loc[mask4a] = pd.concat([first.loc[mask4a], crea.loc[mask4a]], axis=1).max(axis=1)
        repl = target.notna()
        if repl.any():
            for _id, before, after in zip(out.loc[mask4a & repl, "id_ticket"], _fmt_iso(close[mask4a & repl]), _fmt_iso(target[mask4a & repl])):
                changes.append({"id_ticket": _id, "regla": "4_close_before_first_fixed_to_max", "antes_fecha_cierre": before, "despues_fecha_cierre": after})
            close.loc[mask4a & repl] = target.loc[mask4a & repl]
        vaciar = mask4a & ~repl
        if vaciar.any():
            for _id, before in zip(out.loc[vaciar, "id_ticket"], _fmt_iso(close[vaciar])):
                changes.append({"id_ticket": _id, "regla": "4_close_before_first_cleared_no_candidate", "antes_fecha_cierre": before, "despues_fecha_cierre": ""})
            close.loc[vaciar] = pd.NaT

    # 4b) Si el estado no es de cierre -> vaciar
    mask4b = mask4 & ~estado.isin(CLOSED_STATES_ES)
    if mask4b.any():
        for _id, before in zip(out.loc[mask4b, "id_ticket"], _fmt_iso(close[mask4b])):
            changes.append({"id_ticket": _id, "regla": "4_close_before_first_cleared_open_state", "antes_fecha_cierre": before, "despues_fecha_cierre": ""})
        close.loc[mask4b] = pd.NaT

    # Regla 2: estado cerrado/resuelto y cierre vacío -> imputar a max(first, crea)
    mask2 = estado.isin(CLOSED_STATES_ES) & close.isna()
    if mask2.any():
        candidate = pd.concat([first, crea], axis=1).max(axis=1)
        apply2 = mask2 & candidate.notna()
        if apply2.any():
            for _id, after in zip(out.loc[apply2, "id_ticket"], _fmt_iso(candidate[apply2])):
                changes.append({"id_ticket": _id, "regla": "2_closed_without_close_imputed", "antes_fecha_cierre": "", "despues_fecha_cierre": after})
            close.loc[apply2] = candidate.loc[apply2]

    # Persistir cambios y devolver dataframe con `fecha_cierre` ya formateada.
    out["fecha_cierre"] = _fmt_iso(close)
    pd.DataFrame(changes, columns=["id_ticket","regla","antes_fecha_cierre","despues_fecha_cierre"]).to_csv(POSTFIX_LOG, index=False, encoding="utf-8-sig")
    return out


# -----------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# -----------------------------------------------------------------------------

def main() -> None:
    """
    Orquesta el pipeline:
      1) Normaliza/categoriza Kaggle1, Kaggle2 y Sintético.
      2) Concatena resultados.
      3) Aplica postfix de coherencia fechas/estado.
      4) Exporta CSV unificado y cortes por canal.
      5) Guarda reporte agregado con contadores de interés.
    """
    # 1) Normalización por fuente (devuelve DF + pequeñas métricas internas)
    k1, st1 = _normalize_source(KAGGLE_ORIGEN1, "kaggle_1")
    k2, st2 = _normalize_source(KAGGLE_ORIGEN2, "kaggle_2")
    sy, st3 = _normalize_source(SINTETICO,      "sintetico")

    # 2) Unificación (mismos campos en el mismo orden)
    final = pd.concat([k1, k2, sy], ignore_index=True)

    # 3) Postfix de coherencia temporal
    final = _postfix_dates_states(final)

    # 4) Exportación de artefactos
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUT_ALL, index=False, encoding="utf-8-sig", sep=";")
    for canal, ruta in OUT_BY_CHANNEL.items():
        final[final["canal"] == canal].to_csv(ruta, index=False, encoding="utf-8-sig", sep=";")

    # 5) Reporte de trazabilidad
    info = {
        "total": int(len(final)),
        "por_canal": final["canal"].value_counts(dropna=False).to_dict(),
        "por_categoria": final["categoria"].value_counts(dropna=False).to_dict(),
        "impacto_diccionarios": {
            "kaggle_1": st1,
            "kaggle_2": st2,
            "sintetico": st3
        },
        "salidas": {
            "todo": str(OUT_ALL),
            "por_canal": {k: str(v) for k, v in OUT_BY_CHANNEL.items()},
            "postfix_log": str(POSTFIX_LOG)
        }
    }
    REPORT_PATH.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    # Mensajes de consola
    print("[OK] Normalización + categorización + POST-FIX fechas/estado completadas.")
    print(f"Unificado: {OUT_ALL}")
    print(f"Postfix log: {POSTFIX_LOG}")
    print(f"Reporte:   {REPORT_PATH}")


if __name__ == "__main__":
    main()
