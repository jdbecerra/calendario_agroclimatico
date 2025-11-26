# -*- coding: utf-8 -*- 
"""
Generador: Dataset A 
-----------------------------------------------------------------------
- Almácigos: fase = vivero_establecimiento, incluye edad_vivero_meses.
- Fertilización sin análisis: fase = floracion_llenado (MDS 1–24). Si MDS<=1, opcionalmente "vivero_establecimiento".
- Broca: fase = cosecha_postcosecha, incluye infestacion_pct y semanas desde último pase.
- Reglas climáticas realistas por altitud+mes (bimodal lluvias; gradiente térmico).
- Recomendaciones técnicas/tradicionales: ajustadas a 6 criterios explícitos.
- Validaciones de coherencia: dominio↔fase, rangos, campos obligatorios y consistencia climática básica.
- Salidas:
    - CBR_Cafe_Cauca_A.yaml
    - CBR_Cafe_Cauca_A_preview.csv
    - grafico_validacion.png
"""

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yaml
import re

# *************** Configuración

random.seed(42)
np.random.seed(42)

OUT_YAML = "CBR_Cafe_Cauca_A.yaml"
OUT_CSV  = "CBR_Cafe_Cauca_A_preview.csv"
OUT_PNG  = "grafico_validacion.png"

# Cantidad de casos generados por dominio
N_ALMACIGOS = 1000
N_FERT      = 1000
N_BROCA     = 1000

MUNICIPIOS = [
    "Popayan","Santander de Quilichao","Piendamo","Cajibio","El Tambo","Morales","Totoro","Silvia",
    "Sotara","Timbio","Patia","Buenos Aires","Bolivar","Almaguer","Argelia","La Sierra","Rosas",
    "Sucre","Paez","Jambalo","Caldono","Inza","Toribio","Purace"
]
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
VARIEDADES = ["Castillo","Caturra","Colombia","Tabi"]
LUNAS = ["nueva","creciente","llena","menguante"]


# *************** Utilidades climáticas (Cauca)

def pick_altitud():
    # altitudes cafeteras típicas del Cauca
    return int(np.clip(np.random.normal(1650, 220), 1200, 2100))

def temp_media_from_altitud(alt_m, mes):
    base = 27.0 - 0.006 * alt_m
    idx = MESES.index(mes)
    seasonal = 1.1 * math.sin((idx/12.0)*2*math.pi - math.pi/6)
    t = base + seasonal + np.random.normal(0, 0.5)
    return float(np.clip(round(t, 1), 12.0, 26.5))

def precip_from_month_alt(mes, alt_m):
    idx = MESES.index(mes)
    rain = 120 + 60*math.sin((idx/12.0)*2*math.pi - math.pi/3) \
               + 60*math.sin((idx/12.0)*4*math.pi - math.pi/4)
    rain += (alt_m - 1400)/10.0
    rain += np.random.normal(0, 20)
    return float(np.clip(round(rain, 1), 40, 260))

def humedad_from_precip(prec, mes):
    idx = MESES.index(mes)
    base = 60 + (prec/3.5)
    seasonal = 2.5 * math.sin((idx/12.0)*2*math.pi + math.pi/3)
    val = base + seasonal + np.random.normal(0, 3.5)
    return float(np.clip(round(val, 1), 55, 95))

def dias_lluvia_from_precip(prec):
    return int(np.clip(round(prec/10.0 + np.random.normal(0, 2)), 5, 25))

def brillo_from_precip(prec):
    v = 7.5 - (prec - 80)/65.0 + np.random.normal(0, 0.35)
    return float(np.clip(round(v, 1), 3.5, 8.0))

def temp_extremes(tmed):
    tmax = tmed + np.random.uniform(5.0, 8.0)
    tmin = tmed - np.random.uniform(4.0, 6.0)
    return float(round(np.clip(tmin, 8, 22), 1)), float(round(np.clip(tmax, 18, 35), 1))

def build_clima(alt, mes):
    p = precip_from_month_alt(mes, alt)
    tmed = temp_media_from_altitud(alt, mes)
    rh = humedad_from_precip(p, mes)
    tmin, tmax = temp_extremes(tmed)
    brillo = brillo_from_precip(p)
    d = dias_lluvia_from_precip(p)
    return {
        "temp_min": tmin, "temp_max": tmax, "temp_media": tmed,
        "humedad": rh, "prec_total_mm": p, "dias_lluvia": d, "brillo_solar": brillo
    }


# *************** Fase fenológica 

def fase_por_dominio(dominio, mds=None):
    if dominio == "almacigos":
        return "vivero_establecimiento"
    if dominio == "broca":
        return "cosecha_postcosecha"  # normalizamos con 'post'
    # fertilización: floración/llenado por defecto; MDS muy tempranos opcionalmente establecimiento
    if dominio == "fertilizacion_sin_analisis":
        if mds is not None and mds <= 1:
            return "vivero_establecimiento"
        return "floracion_llenado"
    return "floracion_llenado"

# Criterios (reglas)

def criterios(criterio_idx):
    """
    Devuelve (dominio, fase, ventana_MDS, tecnicas[], tradicionales[], luna_preferida|None).
    Ventana_MDS: tuple (min_mds, max_mds) si aplica; None para almácigos/broca.
    """
    if criterio_idx == 1:
        return ("almacigos", "vivero_establecimiento", None,
                [
                    "Uso de Micorrizas arbusculares 10–20 g/bolsa en germinadores y almácigos favorece la absorción de fósforo y otros nutrientes.",
                    "Aplicar Fosfato diamónico (DAP) 2 g/bolsa."
                ],
                [
                    "Preparar y aplicar insecticidas naturales a base de ají, ajenjo y ajo, los cuales funcionan como repelentes para prevenir y controlar insectos.",
                    "Sembrar plantas alelopáticas para repeler plagas en almácigos y en el cultivo de café.",
                    "Elaborar compost con cáscara de coco y residuos de finca o cocina.",
                    "Siembra de jengibre alrededor del cultivo como repelente natural contra serpientes."
                ],
                None)
    if criterio_idx == 2:
        return ("almacigos", "vivero_establecimiento", None,
                [
                    "Aplicar mezcla Urea:DAP (3:2) equivalente a NPK 20-10-10, 20 g/planta, dos meses después de la siembra, para estimular raíces y hojas verdaderas."
                ],
                [
                    "Sembrar hileras de maíz para incorporación orgánica tras su cosecha.",
                    "Sembrar leguminosas (frijol, habichuela) para fijar nitrógeno y mejorar la fertilidad   del suelo; además ayudan a suprimir ciertas malezas, atraen insectos benéficos como abejas y reducen el uso de abonos sintéticos.",
                    "Establecimiento de árboles maderables (nogal cafetero, guamo) como sombra natural para los cafetales.",
                    "Evitar limpieza de cafetales en luna menguante, pues se asocia con la proliferación de hormigas o cochinillas.",
                    "Siembra de jengibre alrededor del cultivo como repelente natural contra serpientes."
                ],
                "menguante")
    if criterio_idx == 3:
        return ("fertilizacion_sin_suelo", "floracion_llenado", (6,12),
                [
                    "Agregar cal dolomítica o cal agrícola hasta 150 g/planta/año al menos dos meses antes del trasplante o durante corrección del suelo; no mezclar con fertilizantes."
                ],
                [
                    "Sembrar hileras de maíz para incorporación orgánica tras su cosecha.",
                    "Sembrar leguminosas (frijol, habichuela) para fijar nitrógeno y mejorar la fertilidad   del suelo; además ayudan a suprimir ciertas malezas, atraen insectos benéficos como abejas y reducen el uso de abonos sintéticos.",
                    "Establecimiento de árboles maderables (nogal cafetero, guamo) como sombra natural para los cafetales",
                    "Evitar limpieza de cafetales en luna menguante, pues se asocia con la proliferación de hormigas o cochinillas.",
                    "Siembra de jengibre alrededor del cultivo como repelente natural contra serpientes."
                ],
                "menguante")
    if criterio_idx == 4:
        return ("fertilizacion_sin_analisis", "floracion_llenado", (18,24),
                [
                    "Fertilizar con NPK alto en K (25-4-24, 26-4-22 o 23-4-20-3Mg) 1000–1200 kg/ha/año en 2–3 aplicaciones (≈200–300 g/planta/año)."
                ],
                [
                    "Sembrar hileras de maíz para incorporación orgánica tras su cosecha.",
                    "Sembrar leguminosas (frijol, habichuela) para fijar nitrógeno y mejorar la fertilidad   del suelo; además ayudan a suprimir ciertas malezas, atraen insectos benéficos como abejas y reducen el uso de abonos sintéticos.",
                    "Establecimiento de árboles maderables (nogal cafetero, guamo) como sombra natural para los cafetales",
                    "Evitar limpieza de cafetales en luna menguante, pues se asocia con la proliferación de hormigas o cochinillas.",
                    "Evitar limpiezas en luna llena por aparición rápida de arvenses.",
                    "Siembra de jengibre alrededor del cultivo como repelente natural contra serpientes."
                ],
                None)  # reglas de luna; no es requisito de fase
    if criterio_idx == 5:
        return ("fertilizacion_sin_analisis", "cosecha_postcosecha", (24, 48),
                [
                    "Plan anual NPK potásico (25-4-24, 26-4-22 o 23-4-20-3Mg): 150–300 kg N/ha-año, 30–60 kg P₂O₅/ha-año, 150–300 kg K₂O/ha-año en 2–3 aplicaciones (≈200–300 g/planta/año)."
                ],
                [
                    "Evitar cosecha durante luna creciente (posible pérdida de peso del grano).",
                    "No dejar frutos secos en árboles o suelo; recolectar y solarizar para eliminar broca.",
                    "Utilizar frutos infestados por broca, hervirlos en agua para eliminar huevos o larvas y evitar su diseminación."

                ],
                "menguante")  # preferible no-cosecha creciente; usamos menguante como favorable para labores culturales
    if criterio_idx == 6:
        return ("fertilizacion_sin_analisis", "cosecha_postcosecha", (48, 72),
                [
                    "Aplicar compost + fuente potásica (K₂O) 200 g/planta para recuperar la fertilidad del suelo tras cosecha."
                ],
                [
                    "Evitar la cosecha de café durante la luna creciente, ya que se cree que el grano pierde peso en esta fase.",
                    "Utilizar frutos infestados por broca, hervirlos en agua para eliminar huevos o larvas y evitar su diseminación.",
                    "No eliminar chupones de las zocas en luna creciente, ya que los brotes crecen con mayor rapidez."
                ],
                "menguante")
    raise ValueError("criterio_idx inválido")


# *************** Reglas de recomendación por dominio (extienden criterios)

def recomendaciones_almacigos(case, criterio_idx):
    rec = {"tecnicas": [], "tradicionales": []}
    dominio, fase, _, tecnicas_pdf, trad_pdf, luna_pref = criterios(criterio_idx)
    # Añadimos texto del criterio
    rec["tecnicas"].extend(tecnicas_pdf)
    rec["tradicionales"].extend(trad_pdf)

    # Ajustes por contexto 
    edad = case["almacigos"]["edad_vivero_meses"]
    bolsa = case["almacigos"]["tamaño_bolsa_kg"]
    sombra = case["contexto"]["sombra_pct"]
    rh = case["clima"]["humedad"]
    tmed = case["clima"]["temp_media"]

    if edad is not None:
        if edad <= 2:
            rec["tecnicas"].append("Solución nutritiva 0,05% NPK cada 15 días; evitar 17-6-18 en edades ≤2 meses, solo aplicar este fertilizante en cafetales en fase de producción.")
        elif edad <= 4:
            rec["tecnicas"].append("0,1% NPK balanceado o 10 g/bolsa/mes fraccionado; monitorear sanidad del sustrato.")
        else:
            rec["tecnicas"].append("12–15 g/bolsa/mes (fraccionado quincenal) con NPK + Ca/Mg si hay deficiencias.")

    objetivo = "30–40%" if (sombra < 30 or sombra > 40) else "mantener 30–40%"
    rec["tecnicas"].append(f"Ajustar sombra a {objetivo} y mejorar ventilación del vivero.")
    rec["tecnicas"].append("Tratamiento preventivo con Trichoderma spp. en sustrato (1 vez/mes).")
    rec["tecnicas"].append("Riegos ligeros diarios; evitar encharcamientos y compactación.")

    if edad and edad >= 5 and (bolsa is not None and bolsa <= 1.0):
        rec["tecnicas"].append("Trasplantar a campo a los 5–6 meses o cambiar a bolsa de 2 kg si se retrasa.")
    if tmed < 18 and rh > 80:
        rec["tecnicas"].append("Barreras rompe-viento y drenajes para prevenir Phoma en condiciones frías y húmedas.")

    rec["tradicionales"].append("Evitar trasplantes con suelos saturados por lluvia.")
    return rec, luna_pref

def recomendaciones_fertilizacion(case, criterio_idx):
    rec = {"tecnicas": [], "tradicionales": []}
    dominio, fase, ventana, tecnicas_pdf, trad_pdf, luna_pref = criterios(criterio_idx)
    rec["tecnicas"].extend(tecnicas_pdf)
    rec["tradicionales"].extend(trad_pdf)

    mds = case["fertilizacion_sin_suelo"]["meses_despues_siembra"]
    prec = case["clima"]["prec_total_mm"]
    if mds is not None:
        if mds <= 2:
            rec["tecnicas"].append("Post-trasplante (≤2 MDS): 15–20 g/planta mezcla rica en N (urea:DAP 3:2); evitar excesos.")
        elif mds in (6,):
            rec["tecnicas"].append("6 MDS: 20 g/planta de urea; ajustar según vigor y precipitación.")
        elif mds in (10,):
            rec["tecnicas"].append("10 MDS: 40 g/planta NPK (urea:DAP:KCl 3:1.5:1) + 2 g MgO.")
        elif mds in (14,):
            rec["tecnicas"].append("14 MDS: 30 g/planta de urea; fraccionar si es lluvioso.")
        elif mds in (18,):
            rec["tecnicas"].append("18 MDS: 60 g/planta NPK (3:1.1:1.5) + 3 g MgO; incorporar levemente.")
        else:
            rec["tecnicas"].append("Interpolar dosis entre hitos; fraccionar cuando la lluvia es alta.")

    if prec > 150:
        rec["tecnicas"].append("Fraccionar la dosis en 2 aplicaciones separadas 45 días.")
    rec["tecnicas"].append("Aplicar en corona 25–35 cm e incorporar superficialmente; evitar suelo saturado.")
    # Tradicional con luna
    if luna_pref == "menguante":
        rec["tradicionales"].append("Aplicar Fertilizantes preferiblemente en menguante y en la tarde.")
    return rec, luna_pref

def recomendaciones_broca(case):
    rec = {"tecnicas": [], "tradicionales": []}
    semanas = case["broca"]["semanas_desde_ultimo_pase"]
    inf = case["broca"]["infestacion_pct"]
    rh = case["clima"]["humedad"]
    tmed = case["clima"]["temp_media"]

    if semanas >= 2:
        rec["tecnicas"].append("Realizar repase completo entre 21–25 días desde el último pase.")
    rec["tecnicas"].append("Recolectar todos los frutos del suelo y remanentes (cero frutos remanentes).")
    if (inf >= 2.0) or (tmed > 21 and rh < 75):
        rec["tecnicas"].append("Aplicar Beauveria bassiana (1×10^8 conidios/ml) 500 ml/planta cada 30 días con HR>70%.")
    rec["tecnicas"].append("Ajustar calendario de cosecha para no dejar >5% de frutos sobremaduros.")
    rec["tradicionales"].append("No dejar frutos secos en los árboles ni en el suelo; recolectarlos y almacenarlos en bolsas plásticas o estopas para que el calor elimine la broca.")
    rec["tradicionales"].append("Cosecha intensiva durante repases.")
    return rec

# *************** Caso común + constructores

def case_common():
    muni = random.choice(MUNICIPIOS)
    alt = pick_altitud()
    mes = random.choice(MESES)
    clima = build_clima(alt, mes)
    return {
        "contexto": {
            "ubicacion": muni,
            "altitud_msnm": alt,
            "mes": mes,
            "variedad": random.choice(VARIEDADES),
            "sombra_pct": int(np.clip(np.random.normal(35, 10), 10, 60))
        },
        "clima": clima
    }

def make_case_almacigos(idx):
    base = case_common()
    criterio_idx = random.choice([1,2])  # criterios de vivero
    edad = int(np.clip(round(np.random.normal(3.5, 1.5)), 1, 8))
    bolsa = 1.0 if random.random() < 0.7 else 2.0
    base["almacigos"] = {
        "edad_vivero_meses": edad,
        "tamaño_bolsa_kg": bolsa,
        "estado_sanitario": {
            "rhizoctonia": random.random() < 0.07,
            "nematodos": random.random() < 0.06,
            "mancha_hierro": random.random() < 0.16,
            "roya": round(max(0.0, np.random.normal(1.0, 1.0)), 1) if random.random() < 0.15 else 0.0,
            "phoma": random.random() < 0.05,
            "cochinillas": random.random() < 0.10
        },
        "sustrato_origen": random.choice(["suelo_limpio","mezcla_suelo+MO","compostado"]),
        "uso_micorrizas": True if criterio_idx == 1 else (random.random() < 0.4),
        "ventilacion": random.choice(["baja","media","alta"])
    }
    base["fertilizacion_sin_suelo"] = {
        "meses_despues_siembra": None, "numero_plantas": None,
        "disponibilidad_insumos": {"urea": None, "dap": None, "kcl": None, "oxido_magnesio": None},
        "densidad_siembra": None
    }
    base["broca"] = {"semanas_desde_ultimo_pase": None, "infestacion_pct": None,
                     "esquema_cosechas": None, "evento_climatico": None}
    base["fase_fenologica"] = "vivero_establecimiento"
    recs, luna_pref = recomendaciones_almacigos(base, criterio_idx)
    # Luna preferida si existe
    base["luna_fase"] = luna_pref if luna_pref else (random.choice(LUNAS) if random.random() < 0.35 else None)
    base.update({
        "id": f"ALM-{idx:04d}",
        "tipo": "almacigos",
        "recomendaciones": recs,
        "fuente_caso_base": f"Criterio {criterio_idx} + Lineamientos Cenicafé"
    })
    return base

def make_case_fertilizacion(idx):
    base = case_common()
    criterio_idx = random.choice([3,4,5,6])
    dominio, fase_pdf, ventana, _, _, luna_pref = criterios(criterio_idx)
    if ventana:
        mds = int(np.clip(round(np.random.uniform(*ventana)), 0, 72))
    else:
        mds = random.choice([1,2,3,4,5,6,8,10,12,14,16,18,20,22,24])
    base["fertilizacion_sin_suelo"] = {
        "meses_despues_siembra": mds,
        "numero_plantas": int(np.random.uniform(3000, 8000)),
        "disponibilidad_insumos": {"urea": True, "dap": True, "kcl": True, "oxido_magnesio": random.random() < 0.9},
        "densidad_siembra": int(np.random.uniform(3500, 7000))
    }
    base["almacigos"] = {"edad_vivero_meses": None, "tamaño_bolsa_kg": None,
                         "estado_sanitario": {"rhizoctonia": False,"nematodos": False,"mancha_hierro": False,"roya": 0.0,"phoma": False,"cochinillas": False},
                         "sustrato_origen": None, "uso_micorrizas": None, "ventilacion": None}
    base["broca"] = {"semanas_desde_ultimo_pase": None, "infestacion_pct": None,
                     "esquema_cosechas": None, "evento_climatico": None}
    # Fase: usamos la del criterio; si MDS<=1, permitir vivero_establecimiento
    base["fase_fenologica"] = fase_pdf if not (mds <= 1 and fase_pdf != "vivero_establecimiento") else "vivero_establecimiento"
    recs, luna_pdf = recomendaciones_fertilizacion(base, criterio_idx)
    base["luna_fase"] = luna_pdf if luna_pdf else (random.choice(LUNAS) if random.random() < 0.25 else None)
    base.update({
        "id": f"FERT-{idx:04d}",
        "tipo": "fertilizacion_sin_analisis",
        "recomendaciones": recs,
        "fuente_caso_base": f"Criterio {criterio_idx} + Lineamientos Cenicafé"
    })
    return base

def make_case_broca(idx):
    base = case_common()
    semanas = random.choice([1,2,3,4,5])
    t = base["clima"]["temp_media"]
    inf_base = 1.5 if t < 20 else (2.5 if t < 22 else 3.5)
    inf = float(np.clip(np.random.normal(inf_base + 0.4*(semanas-2), 0.7), 0.2, 9.0))
    base["broca"] = {
        "semanas_desde_ultimo_pase": semanas,
        "infestacion_pct": round(inf, 1),
        "esquema_cosechas": random.choice(["una_cosecha","principal+mitaca"]),
        "evento_climatico": random.choice(["Neutro","El_Nino","La_Nina"])
    }
    base["almacigos"] = {"edad_vivero_meses": None, "tamaño_bolsa_kg": None,
                         "estado_sanitario": {"rhizoctonia": False,"nematodos": False,"mancha_hierro": False,"roya": 0.0,"phoma": False,"cochinillas": False},
                         "sustrato_origen": None, "uso_micorrizas": None, "ventilacion": None}
    base["fertilizacion_sin_suelo"] = {"meses_despues_siembra": None,"numero_plantas": None,
                                       "disponibilidad_insumos": {"urea": None,"dap": None,"kcl": None,"oxido_magnesio": None},
                                       "densidad_siembra": None}
    base["fase_fenologica"] = "cosecha_postcosecha"
    base["luna_fase"] = None
    recs = recomendaciones_broca(base)
    base.update({
        "id": f"BRO-{idx:04d}",
        "tipo": "broca",
        "recomendaciones": recs,
        "fuente_caso_base": "Lineamientos Cenicafé (BRC) + manejo integrado"
    })
    return base

# *************** Validación de coherencia

def validar_caso(c):
    dom = c.get("tipo")
    fase = c.get("fase_fenologica")
    ok = True
    msg = []
    # Reglas dominio-fase
    if dom == "almacigos" and fase != "vivero_establecimiento":
        ok = False; msg.append("almácigos debe estar en vivero_establecimiento")
    if dom == "broca" and fase != "cosecha_postcosecha":
        ok = False; msg.append("broca debe estar en cosecha_postcosecha")
    if dom == "fertilizacion_sin_analisis":
        mds = (c.get("fertilizacion_sin_suelo") or {}).get("meses_despues_siembra")
        if mds is None:
            ok = False; msg.append("fertilización requiere meses_despues_siembra")
        if mds is not None and not (0 <= mds <= 72):
            ok = False; msg.append("MDS fuera de rango 0–72")
        fase_esperada = fase_por_dominio("fertilizacion_sin_analisis", mds)
        if fase not in ("floracion_llenado", "vivero_establecimiento", "cosecha_postcosecha"):
            ok = False; msg.append(f"fase '{fase}' no válida")
    # Rangos clima básicos
    clima = c.get("clima") or {}
    tmed = clima.get("temp_media")
    tmin = clima.get("temp_min")
    tmax = clima.get("temp_max")
    rh = clima.get("humedad")
    prec = clima.get("prec_total_mm")
    brillo = clima.get("brillo_solar")
    dllu = clima.get("dias_lluvia")
    if not (8 <= tmin <= 22 and 18 <= tmax <= 35 and 12 <= tmed <= 26.5):
        ok = False; msg.append("temperaturas fuera de umbrales realistas")
    if not (55 <= rh <= 98):
        ok = False; msg.append("humedad fuera de rango")
    if not (40 <= prec <= 260):
        ok = False; msg.append("precipitacion fuera de rango")
    if not (3.5 <= brillo <= 8.5):
        ok = False; msg.append("brillo solar fuera de rango")
    if not (5 <= dllu <= 27):
        ok = False; msg.append("días de lluvia fuera de rango")
    return ok, "; ".join(msg)

# *************** Exportadores

def save_yaml(cases, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cases, f, allow_unicode=True, sort_keys=False)

def flatten_for_preview(c):
    tecnicas = (c.get("recomendaciones") or {}).get("tecnicas", [])
    t1 = tecnicas[0] if len(tecnicas) > 0 else ""
    t2 = tecnicas[1] if len(tecnicas) > 1 else ""
    return {
        "id": c["id"],
        "tipo": c["tipo"],
        "fase": c.get("fase_fenologica"),
        "luna": c.get("luna_fase"),
        "ubicacion": c["contexto"]["ubicacion"],
        "altitud_msnm": c["contexto"]["altitud_msnm"],
        "mes": c["contexto"]["mes"],
        "sombra_pct": c["contexto"]["sombra_pct"],
        "temp_media": c["clima"]["temp_media"],
        "humedad": c["clima"]["humedad"],
        "prec_total_mm": c["clima"]["prec_total_mm"],
        "rec1": t1,
        "rec2": t2
    }

def save_preview_csv(cases, path, n=50):
    df = pd.DataFrame([flatten_for_preview(c) for c in cases])
    sample = df.sample(min(n, len(df)), random_state=123).reset_index(drop=True)
    sample.to_csv(path, index=False, encoding="utf-8")
    return sample

def plot_validacion(cases, path_png):
    altitudes = [c["contexto"]["altitud_msnm"] for c in cases]
    tmed = [c["clima"]["temp_media"] for c in cases]
    plt.figure(figsize=(7,5))
    plt.scatter(altitudes, tmed, s=10, alpha=0.5)
    plt.xlabel("Altitud (m s. n. m.)")
    plt.ylabel("Temperatura media (°C)")
    plt.title(f"Validación: Temperatura media vs Altitud (Cauca, {len(cases)} casos)")
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(path_png, dpi=150)
    plt.close()


# *************** Limpieza y coherencia textual

import unicodedata
from collections import Counter

def _normalize_text_line(s: str) -> str:
    if s is None:
        return ""
    s2 = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")
    s2 = s2.lower()
    s2 = s2.replace("–", "-").replace("—","-")
    s2 = re.sub(r"\s+", " ", s2).strip()
    s2 = re.sub(r"[.;:]+$", "", s2)
    return s2

def _titlecase_first(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    return s[0].upper() + s[1:] if s else s

def _ensure_period(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    return s if s.endswith(".") else s + "."

def _dedup_list_preserving_order(lines):
    seen = set()
    out = []
    for ln in lines:
        key = _normalize_text_line(ln)
        if key not in seen and key != "":
            seen.add(key)
            out.append(ln)
    return out

def limpiar_recomendaciones(caso):
    rec = (caso.get("recomendaciones") or {"tecnicas":[], "tradicionales":[]})
    tecnicas = list(rec.get("tecnicas") or [])
    tradicionales = list(rec.get("tradicionales") or [])
    clima = caso.get("clima") or {}
    alm = caso.get("almacigos") or {}
    removed = []

    # Reglas de eliminación por incoherencia contextual
    rh = clima.get("humedad")
    prec = clima.get("prec_total_mm")
    edad = alm.get("edad_vivero_meses")
    bolsa = alm.get("tamaño_bolsa_kg")
    uso_mic = alm.get("uso_micorrizas")

    def keep(line):
        n = _normalize_text_line(line)

        # 1) micorrizas incoherente
        if "micorriz" in n and uso_mic is False:
            removed.append(("micorrizas_incoherente", line)); return False

        # 2) beauveria con HR < 70
        if "beauveria" in n and isinstance(rh,(int,float)) and rh < 70:
            removed.append(("beauveria_hr<70", line)); return False

        # 3) fraccionar por lluvia sin lluvia alta
        if "fraccionar la dosis" in n and isinstance(prec,(int,float)) and prec <= 150:
            removed.append(("fraccionamiento_sin_lluvia", line)); return False

        # 4) dosis altas 12-15 g/bolsa/mes en edades <=2
        if ("12-15 g/bolsa/mes" in n or "12–15 g/bolsa/mes" in line) and (edad is not None and edad <= 2):
            removed.append(("dosis_alta_edad_baja", line)); return False

        # 5) cambiar a bolsa de 2 kg si ya es 2 kg
        if "cambiar a bolsa de 2 kg" in n and isinstance(bolsa,(int,float)) and bolsa >= 2.0:
            removed.append(("cambio_bolsa_innecesario", line)); return False

        return True

    tecnicas = [ln for ln in tecnicas if keep(ln)]
    tradicionales = [ln for ln in tradicionales if keep(ln)]

    # 6) Contradicciones de luna (preferimos "evitar" sobre "aplicar")
    def remove_luna_conflicts(lines):
        ns = [_normalize_text_line(x) for x in lines]
        if any(("evitar" in s and "menguante" in s) for s in ns) and any(("aplicar" in s and "menguante" in s) for s in ns):
            lines = [x for x in lines if not ("aplicar" in _normalize_text_line(x) and "menguante" in _normalize_text_line(x))]
            removed.append(("luna_contradictoria_menguante", "aplicar en menguante (eliminado)"))
        return lines

    tecnicas = remove_luna_conflicts(tecnicas)
    tradicionales = remove_luna_conflicts(tradicionales)

    # 7) Redundancias específicas almácigos: Urea:DAP 3:2 vs 0,1% NPK/10 g bolsa/mes
    ns_tecn = [_normalize_text_line(x) for x in tecnicas]
    has_urea_dap = any("urea:dap (3:2)" in s or "urea:dap 3:2" in s for s in ns_tecn)
    has_npk_010 = any("0,1% npk balanceado" in s or "10 g/bolsa/mes fraccionado" in s for s in ns_tecn)
    if caso.get("tipo") == "almacigos" and has_urea_dap and has_npk_010:
        # Mantener Urea:DAP (criterio 2) y quitar la línea de 0,1% para no redundar
        new_tecn = []
        for ln in tecnicas:
            n = _normalize_text_line(ln)
            if ("0,1% npk balanceado" in n) or ("10 g/bolsa/mes fraccionado" in n):
                removed.append(("redundancia_npk_010", ln))
                continue
            new_tecn.append(ln)
        tecnicas = new_tecn

    # Deduplicar preservando orden
    tecnicas = _dedup_list_preserving_order(tecnicas)
    tradicionales = _dedup_list_preserving_order(tradicionales)

    # Normalizar redacción: mayúscula inicial + punto final
    tecnicas = [_ensure_period(_titlecase_first(x)) for x in tecnicas]
    tradicionales = [_ensure_period(_titlecase_first(x)) for x in tradicionales]

    caso["recomendaciones"] = {"tecnicas": tecnicas, "tradicionales": tradicionales}
    return caso, removed

# *************** Main

def main():
    print("Generando Dataset A ...")
    cases = []

    print(f"  - Almácigos ({N_ALMACIGOS})...")
    for i in range(1, N_ALMACIGOS+1):
        c = make_case_almacigos(i)
        ok, why = validar_caso(c)
        if not ok:
            c["fase_fenologica"] = "vivero_establecimiento"
        c, _removed = limpiar_recomendaciones(c)
        cases.append(c)

    print(f"  - Fertilización sin análisis ({N_FERT})...")
    for i in range(1, N_FERT+1):
        c = make_case_fertilizacion(i)
        ok, why = validar_caso(c)
        if not ok:
            mds = (c.get("fertilizacion_sin_suelo") or {}).get("meses_despues_siembra")
            c["fase_fenologica"] = "vivero_establecimiento" if (mds is not None and mds <= 1) else ("floracion_llenado" if (mds is not None and mds < 36) else "cosecha_postcosecha")
        c, _removed = limpiar_recomendaciones(c)
        cases.append(c)

    print(f"  - Broca ({N_BROCA})...")
    for i in range(1, N_BROCA+1):
        c = make_case_broca(i)
        ok, why = validar_caso(c)
        if not ok:
            c["fase_fenologica"] = "cosecha_postcosecha"
        c, _removed = limpiar_recomendaciones(c)
        cases.append(c)

    random.shuffle(cases)
    print(f"Casos generados: {len(cases)}")

    print(f"Guardando YAML -> {OUT_YAML}")
    save_yaml(cases, OUT_YAML)

    print(f"Creando muestra CSV (50 casos) -> {OUT_CSV}")
    _ = save_preview_csv(cases, OUT_CSV, n=50)

    print(f"Generando gráfico de validación -> {OUT_PNG}")
    plot_validacion(cases, OUT_PNG)

    print("Listo.")
    print(f" - {Path(OUT_YAML).resolve()}")
    print(f" - {Path(OUT_CSV).resolve()}")
    print(f" - {Path(OUT_PNG).resolve()}")

if __name__ == "__main__":
    main()
