
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import re
from difflib import SequenceMatcher
from collections import defaultdict

# ============================================================
# BASE DEL PROYECTO
# ============================================================
BASE_DIR = r"C:\Users\Jose\dev\sipi-api\ETL"

# CSV de entrada
ENTIDADES_CSV = os.path.join(BASE_DIR, "entidades_religiosas", "extract", "entidades_catolicas_completo_20260127_081604.csv")
FUNDACIONES_CSV = os.path.join(BASE_DIR, "fundaciones", "extract", "fundaciones_completas_20260127_191805.csv")

# CSV de salida
OUTPUT_CSV = os.path.join(BASE_DIR, "entidades_religiosas", "extract", "matches_fundaciones_catolicas.csv")

# Parámetros
MATCH_THRESHOLD = 0.70   # 70%
VERBOSE = True

# Palabras genéricas a ignorar
STOPWORDS = {
    "de", "la", "el", "los", "las", "y", "del",
    "fundacion", "fundación", "asociacion", "asociación",
    "cofradia", "cofradía", "hermandad", "santo", "santisimo", "san", "virgen"
}

# ============================================================
# UTILIDADES
# ============================================================

def log(msg):
    if VERBOSE:
        print(msg)

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

# ============================================================
# EXTRAER NOMBRE PROPIO CENTRAL DE LA ADVOCACIÓN
# ============================================================

def extraer_nombre_propio_advocacion(nombre: str):
    nombre_norm = normalizar(nombre)
    match = re.search(r"(?:de la |del |de )(.+)", nombre_norm)
    if match:
        nucleo = match.group(1).strip()
        tokens = [t for t in nucleo.split() if t not in STOPWORDS]
        return " ".join(tokens) if tokens else nucleo
    else:
        tokens = [t for t in nombre_norm.split() if t not in STOPWORDS]
        return tokens[-1] if tokens else nombre_norm

# ============================================================
# CARGA CSV
# ============================================================

def cargar_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el fichero: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ============================================================
# INDEXADO DE FUNDACIONES
# ============================================================

def construir_indice_fundaciones(fundaciones):
    index = defaultdict(list)
    for f in fundaciones:
        nombre = f.get("nombre_fundacion", "")
        f["nombre_propio"] = extraer_nombre_propio_advocacion(nombre)
        for tok in f["nombre_propio"].split():
            index[tok].append(f)
    log(f"\n🧱 Índice semántico creado con {len(index)} claves")
    for k in list(index.keys())[:5]:
        log(f"   · {k} → {len(index[k])} fundaciones")
    return index

# ============================================================
# MATCHING
# ============================================================

def similitud(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

def ejecutar_matching(entidades, index):
    resultados = []
    log("\n🔗 Matching:")

    for ent in entidades:
        nombre_ent = ent.get("Nombre", "") or ent.get("nombre", "")
        if not nombre_ent:
            continue

        nombre_propio_ent = extraer_nombre_propio_advocacion(nombre_ent)
        tokens_ent = nombre_propio_ent.split()
        provincia_ent = ent.get("Provincia", "").strip().lower()
        poblacion_ent = ent.get("Poblacion", "").strip().lower()

        candidatos = []
        vistos = set()

        for tok in tokens_ent:
            for fund in index.get(tok, []):
                fid = fund.get("codigo_registro") or fund.get("nombre_fundacion")
                if fid not in vistos:
                    vistos.add(fid)
                    candidatos.append(fund)

        mejor_score = 0.0
        mejor_match = None

        for fund in candidatos:
            nombre_propio_fund = fund.get("nombre_propio", "")
            propios_ent = set(nombre_propio_ent.split())
            propios_fund = set(nombre_propio_fund.split())
            propios_comunes = propios_ent & propios_fund

            score = similitud(normalizar(nombre_ent), normalizar(fund.get("nombre_fundacion", "")))

            if propios_comunes:
                penalizacion = 0.15 * (len(propios_ent - propios_fund) + len(propios_fund - propios_ent))
                score -= penalizacion
                score = max(score, 0.0)

                prov_fund = fund.get("provincia_detalle", "").strip().lower()
                muni_fund = fund.get("localidad", "").strip().lower()

                if provincia_ent and provincia_ent == prov_fund:
                    score += 0.1
                if poblacion_ent and poblacion_ent == muni_fund:
                    score += 0.05

                score = min(score, 1.0)
            else:
                score = min(score, 0.3)

            if score > mejor_score:
                mejor_score = score
                mejor_match = fund

        if mejor_match and mejor_score >= MATCH_THRESHOLD:
            log(
                f"✔ MATCH {int(mejor_score*100)}% → "
                f"{nombre_ent[:35]:35} ⇄ {mejor_match['nombre_fundacion'][:35]}\n"
                f"     • Provincia Entidad: {provincia_ent} | Poblacion Entidad: {poblacion_ent}\n"
                f"     • Provincia Fundación: {mejor_match.get('provincia_detalle','').strip().lower()} | "
                f"Localidad Fundación: {mejor_match.get('localidad','').strip().lower()}"
            )
            resultados.append({
                "entidad_nombre": nombre_ent,
                "provincia_entidad": provincia_ent,
                "poblacion_entidad": poblacion_ent,
                "fundacion_nombre": mejor_match["nombre_fundacion"],
                "provincia_fundacion": mejor_match.get("provincia_detalle", "").strip().lower(),
                "localidad_fundacion": mejor_match.get("localidad", "").strip().lower()
            })

    return resultados

# ============================================================
# GUARDAR RESULTADOS
# ============================================================

def guardar_resultados(resultados, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "entidad_nombre", "provincia_entidad", "poblacion_entidad",
                "fundacion_nombre", "provincia_fundacion", "localidad_fundacion"
            ]
        )
        writer.writeheader()
        writer.writerows(resultados)
    log(f"\n💾 Resultados guardados en: {path}")

# ============================================================
# MAIN
# ============================================================

def main():
    log("📥 Cargando CSVs...")
    entidades = cargar_csv(ENTIDADES_CSV)
    fundaciones = cargar_csv(FUNDACIONES_CSV)
    log(f"   · Entidades religiosas: {len(entidades)}")
    log(f"   · Fundaciones: {len(fundaciones)}")

    index = construir_indice_fundaciones(fundaciones)
    resultados = ejecutar_matching(entidades, index)
    guardar_resultados(resultados, OUTPUT_CSV)

    log(f"\n✅ Proceso terminado. Matches encontrados: {len(resultados)}")

if __name__ == "__main__":
    main()
