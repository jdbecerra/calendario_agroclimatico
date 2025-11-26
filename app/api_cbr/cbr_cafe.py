# -*- coding: utf-8 -*-
"""
CBR Café – Cauca (fase fenológica + aplicabilidad por dominio + almácigos con edad_vivero_meses + extras B)
-----------------------------------------------------------------------------------------------------------
- Fase del cultivo como variable de entrada (--fase) o inferida (altitud+mes o MDS).
- Reglas de aplicabilidad por dominio con explicación (sin penalización, solo inclusión/exclusión).
- Un solo bloque de pesos por dominio con renormalización dinámica.
- 'meses_despues_siembra' solo afecta a fertilización.
- 'edad_vivero_meses' afecta a almácigos (entrada y casos).
- 'mes_sin' / 'mes_cos' codifican el mes (variable circular).
- Recuperación k-NN, fusión dinámica de recomendaciones (k) por dominio.
- Extras “históricos por estación” (Dataset B) con bono por cercanía de altitud,
  combinados APARTE a partir de kB y agrupados por categoría.
- Retención opcional de nuevos casos en un YAML (Dataset C).

Ejemplo CLI:
python cbr_cafe.py --data CBR_Cafe_Cauca_A.yaml CBR_Cafe_Cauca_B_historicos.yaml \
  --tipo auto --altitud 1650 --mes abril --sombra 35 --temp_media 20.5 --humedad 78 \
  --prec_total_mm 150 --dias_lluvia 16 --brillo_solar 95 --meses_despues_siembra 10 \
  --edad_vivero_meses 3 --luna llena --k 5 --kB 5 --usar_extras_b true \
  --save_case_to CBR_Cafe_Cauca_C.yaml
"""

import argparse, math, json, sys, re
from pathlib import Path

try:
    import yaml
except Exception:
    print("ERROR: Se requiere PyYAML (pip install pyyaml).", file=sys.stderr)
    sys.exit(1)

MESES = ["enero","febrero","marzo","abril","mayo","junio",
         "julio","agosto","septiembre","octubre","noviembre","diciembre"]

# =========================
# Fases y reglas de dominio
# =========================
FASES = ["vivero_establecimiento", "floracion_llenado", "cosecha_poscosecha"]

APLICA_DOMINIO = {
    "almacigos": {
        "aplica_en": {"vivero_establecimiento"},
        "razon_no_aplica": "Almácigos aplica solo en vivero/establecimiento (antes del trasplante)."
    },
    "fertilizacion_sin_analisis": {
        "aplica_en": {"vivero_establecimiento", "floracion_llenado"},
        "razon_no_aplica": "Fertilización sin análisis no aplica en cosecha/poscosecha."
    },
    "broca": {
        "aplica_en": {"cosecha_poscosecha"},
        "razon_no_aplica": "Broca aplica cuando hay frutos (cosecha/poscosecha)."
    }
}

# =========================
# Utilidades numéricas
# =========================
def mes_to_sin_cos(mes: str):
    m = (mes or "").strip().lower()
    idx = MESES.index(m) if m in MESES else 0
    ang = 2.0 * math.pi * (idx / 12.0)
    return math.sin(ang), math.cos(ang)

def safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

def clip01(x):
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0

# =========================
# Inferencia de fase
# =========================
def inferir_fase(altitud: float, mes: str, mds: float | None) -> str:
    """
    Prioriza MDS (meses después de siembra):
        <=0.5 -> vivero_establecimiento (siembra muy reciente)
        1–24  -> floracion_llenado
        >24   -> cosecha_poscosecha
    Si no hay MDS, usa regla altitud+mes (coherente con Dataset A).
    """
    try:
        if mds is not None:
            if mds <= 0.5:
                return "vivero_establecimiento"
            elif mds <= 24:
                return "floracion_llenado"
            else:
                return "cosecha_poscosecha"
    except Exception:
        pass

    m = (mes or "").strip().lower()
    idx = MESES.index(m) if m in MESES else 0
    alt = float(altitud) if altitud is not None else 1650.0

    if alt >= 1500:
        if idx in [0,1,2,3]:
            return "vivero_establecimiento"
        elif idx in [4,5,6,7]:
            return "floracion_llenado"
        else:
            return "cosecha_poscosecha"
    else:
        if idx in [11,0,1,2]:
            return "vivero_establecimiento"
        elif idx in [3,4,5,6]:
            return "floracion_llenado"
        else:
            return "cosecha_poscosecha"

def dominio_aplica(dominio: str, fase: str, mds: float | None):
    """
    Devuelve (aplica: bool, razon: str | None).
    Excepción: fertilización con MDS válido (>=1 y <=24) se considera aplicable,
    aun si la fase declarada fuese vivero_establecimiento (trasplante temprano).
    """
    regla = APLICA_DOMINIO.get(dominio, {})
    aplica_en = regla.get("aplica_en", set())
    razon = regla.get("razon_no_aplica", "Dominio no aplicable a la fase actual.")

    if dominio == "fertilizacion_sin_analisis":
        if mds is not None and 1 <= mds <= 24:
            return True, None

    return (fase in aplica_en), (None if fase in aplica_en else razon)

# =========================
# Cargar casos desde YAML
# =========================
def load_cases(paths):
    cases = []
    for p in paths:
        pth = Path(p)
        if not pth.exists():
            print(f"AVISO: no se encontró el archivo de casos: {pth}", file=sys.stderr)
            continue
        with open(pth, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            cases.extend(data)
        else:
            print(f"AVISO: {pth} no es una lista YAML de casos; se ignora.", file=sys.stderr)
    return cases

# =========================
# Pesos (A y B)
# =========================
WEIGHTS = {
    "almacigos": {
        "temp_media": 0.23, "humedad": 0.23, "prec_total_mm": 0.22,
        "dias_lluvia": 0.04, "brillo_solar": 0.03, "altitud_msnm": 0.08,
        "sombra_pct": 0.05, "mes_sin": 0.015, "mes_cos": 0.015,
        "edad_vivero_meses": 0.08,
        "luna_fase": 0.06
    },
    "fertilizacion_sin_analisis": {
        "temp_media": 0.15, "humedad": 0.20, "prec_total_mm": 0.20,
        "dias_lluvia": 0.05, "brillo_solar": 0.05, "altitud_msnm": 0.10,
        "sombra_pct": 0.05, "mes_sin": 0.025, "mes_cos": 0.025,
        "meses_despues_siembra": 0.15,
        "luna_fase": 0.07
    },
    "broca": {
        "temp_media": 0.30, "humedad": 0.25, "prec_total_mm": 0.20,
        "dias_lluvia": 0.05, "brillo_solar": 0.05, "altitud_msnm": 0.10,
        "sombra_pct": 0.03, "mes_sin": 0.01, "mes_cos": 0.01
    }
}

WEIGHTS_B = {
    "temp_media": 0.28, "humedad": 0.22, "prec_total_mm": 0.22,
    "dias_lluvia": 0.06, "brillo_solar": 0.06,
    "altitud_msnm": 0.10, "sombra_pct": 0.04, "mes_sin": 0.01, "mes_cos": 0.01
}

STATIONS_ALT = {
    "Estacion_Tambo": 1735.0,
    "Estacion_Piendamo": 1671.0
}

# =========================
# Rangos de normalización
# =========================
RANGES = {
    "temp_media": (10.0, 30.0),
    "humedad": (40.0, 100.0),
    "prec_total_mm": (0.0, 400.0),
    "dias_lluvia": (0.0, 30.0),
    "brillo_solar": (0.0, 200.0),
    "altitud_msnm": (1000.0, 2300.0),
    "sombra_pct": (0.0, 80.0),
    "mes_sin": (-1.0, 1.0),
    "mes_cos": (-1.0, 1.0),
    "meses_despues_siembra": (0.0, 24.0),
    "edad_vivero_meses": (0.0, 6.0)
}

def norm01(val, key):
    if val is None:
        return None
    lo, hi = RANGES[key]
    if hi <= lo:
        return 0.0
    return clip01((val - lo) / (hi - lo))

def sim_numeric(a, b, key):
    if a is None or b is None:
        return None
    na = norm01(a, key)
    nb = norm01(b, key)
    if na is None or nb is None:
        return None
    return clip01(1.0 - abs(na - nb))

# =========================
# Fase lunar (categórica)
# =========================
ADYACENTES = {
    "nueva": {"creciente"},
    "creciente": {"nueva","llena"},
    "llena": {"creciente","menguante"},
    "menguante": {"llena"}
}

def sim_luna(a, b):
    if not a or not b:
        return None
    a = a.strip().lower()
    b = b.strip().lower()
    if a == b:
        return 1.0
    if b in ADYACENTES.get(a, set()):
        return 0.5
    return 0.0

# =========================
# Bono por estación (B)
# =========================
def station_bonus(query_alt, case_station, case_alt=None):
    qa = safe_float(query_alt)
    if qa is None:
        return 1.0
    ref = STATIONS_ALT.get(case_station, safe_float(case_alt))
    if ref is None:
        return 1.0
    diff = abs(qa - ref)
    if diff <= 60:
        return 1.00
    if diff <= 120:
        return 0.85
    if diff <= 200:
        return 0.70
    return 0.55

# =========================
# Vectores (entrada/caso)
# =========================
def extract_input_vector(args_dict):
    mes_sin, mes_cos = mes_to_sin_cos(args_dict.get("mes"))
    return {
        "temp_media": safe_float(args_dict.get("temp_media")),
        "humedad": safe_float(args_dict.get("humedad")),
        "prec_total_mm": safe_float(args_dict.get("prec_total_mm")),
        "dias_lluvia": safe_float(args_dict.get("dias_lluvia")),
        "brillo_solar": safe_float(args_dict.get("brillo_solar")),
        "altitud_msnm": safe_float(args_dict.get("altitud")),
        "sombra_pct": safe_float(args_dict.get("sombra")),
        "mes_sin": mes_sin, "mes_cos": mes_cos,
        "meses_despues_siembra": safe_float(args_dict.get("meses_despues_siembra")),
        "edad_vivero_meses": safe_float(args_dict.get("edad_vivero_meses")),
        "luna_fase": args_dict.get("luna")
    }

def extract_case_vector_A(case):
    ctx = case.get("contexto", {}) or {}
    cli = case.get("clima", {}) or {}
    mes_sin, mes_cos = mes_to_sin_cos(ctx.get("mes"))

    evm = None
    if isinstance(case.get("almacigos_meta"), dict):
        evm = safe_float(case["almacigos_meta"].get("edad_vivero_meses"))
    if evm is None:
        evm = safe_float(ctx.get("edad_vivero_meses"))

    base = {
        "temp_media": safe_float(cli.get("temp_media")),
        "humedad": safe_float(cli.get("humedad")),
        "prec_total_mm": safe_float(cli.get("prec_total_mm")),
        "dias_lluvia": safe_float(cli.get("dias_lluvia")),
        "brillo_solar": safe_float(cli.get("brillo_solar")),
        "altitud_msnm": safe_float(ctx.get("altitud_msnm")),
        "sombra_pct": safe_float(ctx.get("sombra_pct")),
        "mes_sin": mes_sin, "mes_cos": mes_cos,
        "meses_despues_siembra": safe_float((case.get("fertilizacion_sin_suelo") or {}).get("meses_despues_siembra")),
        "edad_vivero_meses": evm,
        "luna_fase": case.get("luna_fase")
    }
    return base

def extract_case_vector_B(case):
    ctx = case.get("contexto", {}) or {}
    cli = case.get("clima", {}) or {}
    mes_sin, mes_cos = mes_to_sin_cos(ctx.get("mes"))
    return {
        "estacion": ctx.get("estacion"),
        "altitud_msnm": safe_float(ctx.get("altitud_msnm")),
        "sombra_pct": safe_float(ctx.get("sombra_pct")),
        "mes_sin": mes_sin, "mes_cos": mes_cos,
        "temp_media": safe_float(cli.get("temp_media")),
        "humedad": safe_float(cli.get("humedad")),
        "prec_total_mm": safe_float(cli.get("prec_total_mm")),
        "dias_lluvia": safe_float(cli.get("dias_lluvia")),
        "brillo_solar": safe_float(cli.get("brillo_solar"))
    }

# =========================
# Similitud ponderada
# =========================
def similarity_weighted_A(qvec, cvec, domain):
    weights = WEIGHTS[domain]
    s_num = 0.0
    s_den = 0.0
    for k, w in weights.items():
        if qvec.get(k) is None:
            continue
        if k == "luna_fase":
            simk = sim_luna(qvec["luna_fase"], cvec.get("luna_fase"))
        else:
            simk = sim_numeric(qvec.get(k), cvec.get(k), k)
        if simk is None:
            continue
        s_num += w * clip01(simk)
        s_den += w
    return 0.0 if s_den <= 0 else clip01(s_num / s_den)

def similarity_weighted_B(qvec, cvec, query_alt):
    s_num = 0.0
    s_den = 0.0
    for k, w in WEIGHTS_B.items():
        if qvec.get(k) is None:
            continue
        simk = sim_numeric(qvec.get(k), cvec.get(k), k)
        if simk is None:
            continue
        s_num += w * clip01(simk)
        s_den += w
    base = 0.0 if s_den <= 0 else clip01(s_num / s_den)
    bonus = station_bonus(query_alt, cvec.get("estacion"), cvec.get("altitud_msnm"))
    return clip01(base * bonus)

# =========================
# Recuperación (k-NN)
# =========================
def top_k_A(cases, query_vec, domain, k, fase_actual, mds):
    """
    Si el dominio no aplica en la fase actual:
      - no se recuperan casos (lista vacía),
      - se devuelve la razón en el meta.
    """
    aplica, razon = dominio_aplica(domain, fase_actual, mds)

    if not aplica:
        meta = {"aplica": False, "razon_no_aplica": razon}
        return [], meta

    hits = []
    for c in cases:
        if c.get("tipo") != domain:
            continue
        sv = extract_case_vector_A(c)
        s = similarity_weighted_A(query_vec, sv, domain)
        hits.append((s, c))

    hits.sort(key=lambda x: x[0], reverse=True)
    meta = {"aplica": True, "razon_no_aplica": None}
    return hits[:max(1, k)], meta

def extras_from_B(cases, query_context, kB):
    """
    Recupera vecinos históricos (Dataset B) y devuelve una lista de 'extras':
    cada extra tiene: texto, categoria_b, estacion, similitud, id_caso.
    """
    msin, mcos = mes_to_sin_cos(query_context.get("mes"))
    qvec = {
        "temp_media": query_context.get("temp_media"),
        "humedad": query_context.get("humedad"),
        "prec_total_mm": query_context.get("prec_total_mm"),
        "dias_lluvia": query_context.get("dias_lluvia"),
        "brillo_solar": query_context.get("brillo_solar"),
        "altitud_msnm": query_context.get("altitud"),
        "sombra_pct": query_context.get("sombra"),
        "mes_sin": msin, "mes_cos": mcos
    }
    scored = []
    for c in cases:
        ctx = c.get("contexto") or {}
        if not (c.get("tipo") == "historico" or ctx.get("estacion")):
            continue
        sv = extract_case_vector_B(c)
        s = similarity_weighted_B(qvec, sv, query_context.get("altitud"))
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max(1, kB)]
    extras = []
    for s, c in top:
        recs = (c.get("recomendaciones") or {})
        for categoria, txt in recs.items():
            if not txt:
                continue
            extras.append({
                "texto": str(txt).strip(),
                "categoria_b": categoria,
                "fuente": "Dataset B (histórico por estación)",
                "estacion": (c.get("contexto") or {}).get("estacion"),
                "similitud": round(float(s), 3),
                "id_caso": c.get("id")
            })
    return extras, top

# =========================
# Módulo dinámico de recomendaciones (A: k)
# =========================

COMPONENTES_FERT = ["urea", "DAP", "KCl", "NPK", "MgO"]

def extraer_mds_de_texto(txt: str) -> float | None:
    txt = txt or ""
    m = re.search(r'(\d+)\s*MDS', txt)
    if m:
        return float(m.group(1))
    m = re.search(r'≤\s*(\d+)\s*MDS', txt)
    if m:
        return float(m.group(1))
    return None

def extraer_componentes(txt: str) -> list[str]:
    comps = []
    for comp in COMPONENTES_FERT:
        if re.search(comp, txt, re.IGNORECASE):
            comps.append(comp.lower())
    return comps

def combinar_recs_fertilizacion(hits_fert, mds_query: float | None):
    """
    Combina recs de fertilización SOLO a partir de k (Dataset A):
    - Elimina duplicados.
    - Para cada componente (urea, NPK, etc.) selecciona una sola dosis,
      la más cercana a los meses_despues_siembra de la consulta.
    """
    recs_genericas = set()
    mejor_por_componente = {}

    for sim, case in hits_fert:
        recs = (case.get("recomendaciones") or {}).get("tecnicas") or []
        for txt in recs:
            if not txt:
                continue
            texto = txt.strip()
            comps = extraer_componentes(texto)
            if not comps:
                recs_genericas.add(texto)
                continue

            mds_txt = extraer_mds_de_texto(texto)
            if mds_query is not None and mds_txt is not None:
                dist = abs(mds_query - mds_txt)
            else:
                dist = 999.0

            for comp in comps:
                actual = mejor_por_componente.get(comp)
                if actual is None or dist < actual[0]:
                    mejor_por_componente[comp] = (dist, texto)

    resultado = set(recs_genericas)
    for comp, (dist, texto) in mejor_por_componente.items():
        resultado.add(texto)

    return sorted(resultado)

def combinar_recs_genericas(hits_dom):
    """
    Combina recomendaciones técnicas y tradicionales de k (Dataset A),
    eliminando repeticiones textuales.
    """
    tecnicas = []
    tradicionales = []
    seen_t = set()
    seen_trad = set()

    for sim, case in hits_dom:
        rec = case.get("recomendaciones") or {}
        for t in rec.get("tecnicas") or []:
            t = (t or "").strip()
            if t and t not in seen_t:
                seen_t.add(t)
                tecnicas.append(t)
        for tr in rec.get("tradicionales") or []:
            tr = (tr or "").strip()
            if tr and tr not in seen_trad:
                seen_trad.add(tr)
                tradicionales.append(tr)

    return {"tecnicas": tecnicas, "tradicionales": tradicionales}

# =========================
# Combinación aparte para kB (extras_B)
# =========================
def agrupar_extras_B(extras_B):
    """
    Agrupa las recomendaciones de B (kB) por 'categoria_b'
    y elimina duplicados dentro de cada categoría.
    """
    grupos = {}
    for e in extras_B:
        cat = e.get("categoria_b") or "general"
        txt = (e.get("texto") or "").strip()
        if not txt:
            continue
        if cat not in grupos:
            grupos[cat] = []
        if txt not in grupos[cat]:
            grupos[cat].append(txt)
    return grupos

# =========================
# Retención (Dataset C)
# =========================
def append_case_to_yaml(save_path: Path, new_case: dict) -> str:
    cases_existing = []
    if save_path.exists():
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    cases_existing = data
        except Exception:
            pass
    next_id = len(cases_existing) + 1
    new_case["id"] = f"NEW-{next_id:04d}"
    cases_existing.append(new_case)
    with open(save_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cases_existing, f, allow_unicode=True, sort_keys=False)
    return new_case["id"]

# =========================
# Ejecución principal
# =========================
def run_cbr(params, verbose: bool = True):
    # Cargar casos A+B
    cases = load_cases(params["data"])
    if not cases:
        print("No se cargaron casos desde los YAML indicados.", file=sys.stderr)
        return None

    fase_in = params.get("fase")
    fase_actual = fase_in or inferir_fase(
        params.get("altitud"),
        params.get("mes"),
        params.get("meses_despues_siembra")
    )
    mds = params.get("meses_despues_siembra")

    query_vec = extract_input_vector(params)

    dominios = ["almacigos","fertilizacion_sin_analisis","broca"] if params["tipo"] == "auto" else [params["tipo"]]

    # 1) Recuperación k (Dataset A)
    hits_por_dom = {}
    meta_por_dom = {}
    for dom in dominios:
        klist, meta = top_k_A(cases, query_vec, dom, params["k"], fase_actual, mds)
        hits_por_dom[dom] = klist
        meta_por_dom[dom] = meta

    # 2) Recuperación kB (Dataset B) y combinación aparte
    extras = []
    extras_agrupados = {}
    if params.get("usar_extras_b", True):
        extras, _ = extras_from_B(cases, params, params["kB"])
        extras_agrupados = agrupar_extras_B(extras)

    # 3) Fusión de recomendaciones SOLO con k (A), por dominio
    resultados = {}
    for dom in dominios:
        klist = hits_por_dom[dom]
        meta = meta_por_dom[dom]

        hits_res = [
            {
                "similitud": round(float(s), 3),
                "id": c.get("id"),
                "tipo": c.get("tipo"),
                "ubicacion": (c.get("contexto") or {}).get("ubicacion")
            }
            for s, c in klist
        ]

        if not meta.get("aplica", True):
            recomendaciones = {"tecnicas": [], "tradicionales": []}
        else:
            if dom == "fertilizacion_sin_analisis":
                recs_tecnicas = combinar_recs_fertilizacion(klist, mds_query=mds)
                base = combinar_recs_genericas(klist)
                recs_trad = base.get("tradicionales", [])
                recomendaciones = {
                    "tecnicas": recs_tecnicas,
                    "tradicionales": recs_trad
                }
            else:
                recomendaciones = combinar_recs_genericas(klist)

        resultados[dom] = {
            "hits": hits_res,
            "recomendaciones": recomendaciones,
            "aplicabilidad": meta
        }

    # 4) Retención (opcional)
    saved_id = None
    if params.get("save_case_to"):
        out_case = {
            "id": None,
            "tipo": params["tipo"],
            "contexto": {
                "ubicacion": params.get("ubicacion"),
                "altitud_msnm": params.get("altitud"),
                "mes": params.get("mes"),
                "variedad": params.get("variedad"),
                "sombra_pct": params.get("sombra"),
                "edad_vivero_meses": params.get("edad_vivero_meses")
            },
            "clima": {
                "temp_media": params.get("temp_media"),
                "humedad": params.get("humedad"),
                "prec_total_mm": params.get("prec_total_mm"),
                "dias_lluvia": params.get("dias_lluvia"),
                "brillo_solar": params.get("brillo_solar")
            },
            "fertilizacion_sin_suelo": {
                "meses_despues_siembra": params.get("meses_despues_siembra")
            } if params["tipo"] in ["auto","fertilizacion_sin_analisis"] else None,
            "almacigos_meta": {
                "edad_vivero_meses": params.get("edad_vivero_meses")
            } if params["tipo"] in ["auto","almacigos"] else None,
            "luna_fase": params.get("luna"),
            "fase_fenologica": fase_actual,
            "recomendaciones": resultados.get(
                params["tipo"] if params["tipo"] != "auto" else "fertilizacion_sin_analisis",
                {}
            ).get("recomendaciones"),
            "fuente_caso_base": "CBR generado"
        }
        try:
            save_path = Path(params["save_case_to"])
            saved_id = append_case_to_yaml(save_path, out_case)
        except Exception as e:
            print(f"AVISO: no se pudo guardar el caso en '{params['save_case_to']}': {e}", file=sys.stderr)

    # 5) Resumen legible (solo si verbose)
    if verbose:
        print(f"\nFase fenológica usada: {fase_actual} (entrada: {params.get('fase') or 'inferida'})")
        for dom in dominios:
            data = resultados.get(dom, {})
            print("\nDominio:", dom.upper())
            print("-" * 60)
            meta = data.get("aplicabilidad", {})
            if not meta.get("aplica", True):
                print(f"  No aplicable en fase '{fase_actual}'. Motivo: {meta.get('razon_no_aplica')}")
                continue

            hits = data.get("hits", [])
            if not hits:
                print("  No se encontraron casos similares.")
                continue
            print("  Casos más similares (k):")
            for h in hits[:params["k"]]:
                sid = h.get("id", "?")
                ubi = h.get("ubicacion") or "N/D"
                sim = h.get("similitud", 0.0)
                print(f"    {sid} ({ubi})  -> similitud: {sim:.3f}")

            recs = data.get("recomendaciones") or {}
            if recs.get("tecnicas"):
                print("\n  Recomendaciones técnicas (k, Dataset A):")
                for r in recs["tecnicas"][:5]:
                    print(f"   - {r}")
            if recs.get("tradicionales"):
                print("\n  Recomendaciones tradicionales (k, Dataset A):")
                for r in recs["tradicionales"][:3]:
                    print(f"   - {r}")

        if extras_agrupados:
            print("\nEXTRAS (kB, Dataset B – agrupados por categoría):")
            for cat, lista in extras_agrupados.items():
                print(f"  Categoría: {cat}")
                for txt in lista[:4]:
                    print(f"   - {txt}")

        if saved_id:
            print(f"\nNuevo caso guardado con ID: {saved_id} en '{params['save_case_to']}'")
        print(json.dumps(output, ensure_ascii=False, indent=2))

    output = {
        "consulta": {
            "tipo": params["tipo"], "k": params["k"], "kB": params["kB"],
            "usar_extras_b": bool(params.get("usar_extras_b", True)),
            "fase": fase_actual
        },
        "resultados_A": resultados,
        "extras_B_raw": extras,           # lista detallada
        "extras_B_agrupados": extras_agrupados,
        "saved_case_id": saved_id
    }
    return output


# =========================
# CLI / PRUEBA
# =========================
def parse_args_or_defaults():
    if len(sys.argv) > 1:
        ap = argparse.ArgumentParser()
        ap.add_argument("--data", nargs="+", required=True, help="YAML con casos (A y/o B; listas).")
        ap.add_argument("--tipo", choices=["auto","almacigos","fertilizacion_sin_analisis","broca"], default="auto")
        ap.add_argument("--ubicacion", default=None)
        ap.add_argument("--altitud", type=float, required=True)
        ap.add_argument("--mes", required=True, choices=MESES)
        ap.add_argument("--variedad", default=None)
        ap.add_argument("--sombra", type=float, required=True)
        ap.add_argument("--temp_media", type=float, required=True)
        ap.add_argument("--humedad", type=float, required=True)
        ap.add_argument("--prec_total_mm", type=float, required=True)
        ap.add_argument("--dias_lluvia", type=float, default=None)
        ap.add_argument("--brillo_solar", type=float, default=None)
        ap.add_argument("--meses_despues_siembra", type=float, default=None,
                        help="Solo para fertilización (o auto).")
        ap.add_argument("--edad_vivero_meses", type=float, default=None,
                        help="Solo para almácigos (opcional).")
        ap.add_argument("--luna", choices=["nueva","creciente","llena","menguante"], default=None,
                        help="Fase lunar (opcional).")
        ap.add_argument("--fase", choices=FASES, default=None,
                        help="Fase fenológica actual; si no se pasa, se infiere.")
        ap.add_argument("--k", type=int, default=5, help="Vecinos para A.")
        ap.add_argument("--kB", type=int, default=5, help="Vecinos para B (extras).")
        ap.add_argument("--usar_extras_b", type=str, default="true",
                        help="true/false: agregar extras del histórico B.")
        ap.add_argument("--save_case_to", default=None, help="Ruta YAML para guardar nuevo caso (Dataset C).")
        args = ap.parse_args()
        return {
            "data": args.data,
            "tipo": args.tipo,
            "ubicacion": args.ubicacion,
            "altitud": args.altitud,
            "mes": args.mes,
            "variedad": args.variedad,
            "sombra": args.sombra,
            "temp_media": args.temp_media,
            "humedad": args.humedad,
            "prec_total_mm": args.prec_total_mm,
            "dias_lluvia": args.dias_lluvia,
            "brillo_solar": args.brillo_solar,
            "meses_despues_siembra": args.meses_despues_siembra,
            "edad_vivero_meses": args.edad_vivero_meses,
            "luna": args.luna,
            "fase": args.fase,
            "k": args.k,
            "kB": args.kB,
            "usar_extras_b": (args.usar_extras_b or "true").strip().lower() in ("true","1","yes","y","si"),
            "save_case_to": args.save_case_to
        }
    else:
        print("Modo PRUEBA: ejecutando con parámetros por defecto (sin CLI).")
        return {
            "data": ["CBR_Cafe_Cauca_A.yaml", "CBR_Cafe_Cauca_B_historicos.yaml"],
            "tipo": "auto",
            "ubicacion": "Popayan",
            "altitud": 1678,
            "mes": "noviembre",
            "variedad": "Castillo",
            "sombra": 25,
            "temp_media": 17.6,
            "humedad": 97,
            "prec_total_mm": 192.2,
            "dias_lluvia": 18,
            "brillo_solar": 95,
            "meses_despues_siembra": 10,
            "edad_vivero_meses": 3,
            "luna": "creciente",
            "fase": "vivero_establecimiento",
            "k": 3,
            "kB": 1,
            "usar_extras_b": True,
            "save_case_to": "CBR_Cafe_Cauca_C.yaml"
        }

if __name__ == "__main__":
    params = parse_args_or_defaults()
    run_cbr(params, verbose=True)
