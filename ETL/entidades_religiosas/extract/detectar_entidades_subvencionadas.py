
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import re
from difflib import SequenceMatcher
from collections import defaultdict
from unidecode import unidecode

# ============================================================
# BASE DEL PROYECTO
# ============================================================
BASE_DIR = r"C:\Users\Jose\dev\sipi-api\ETL"

# CSV de entrada
ENTIDADES_CSV = os.path.join(BASE_DIR, "entidades_religiosas", "extract", "entidades_catolicas_completo_20260127_081604.csv")
SUBVENCIONADAS_CSV = os.path.join(BASE_DIR, "entidades_religiosas", "extract", "Entidades_Catolicas_subvencionadas.csv")

# CSV de salida
OUTPUT_CSV = os.path.join(BASE_DIR, "entidades_religiosas", "extract", "matches_entidades_subvencionadas.csv")

# Parámetros
MATCH_THRESHOLD = 0.70   # 70%
VERBOSE = True

# Palabras genéricas a ignorar
STOPWORDS = {
    "de", "la", "el", "los", "las", "y", "del",
    "fundacion", "fundación", "asociacion", "asociación",
    "cofradia", "cofradía", "hermandad", "santo", "santisimo", "san",
    "real", "ilustre", "venerable", "antigua", "muy", "ilustrísima", "santa",
    "divino", "divina", "santisimo", "santísimo"
}

# Nombres propios conocidos (vírgenes y cristos)
NOMBRES_PROPIOS_RELIG = {
    "jesus", "cristo", "maria", "isabel", "angustias", "salvador",
    "redentor", "inmaculada", "trinidad", "corazon", "corazón",
    "cristo_rey", "sagrado corazon", "dolorosa", "peregrino", "nazareno"
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
    texto = unidecode(texto.lower())
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

# ============================================================
# EXTRAER NOMBRE PROPIO CENTRAL
# ============================================================

def extraer_nombre_propio(nombre: str) -> str:
    """
    Extrae el nombre propio relevante de la entidad subvencionada.
    - Lo que venga detrás de "de", "del", "de la"
    - Prioriza nombres propios conocidos de vírgenes o cristos
    - Si no hay nombres conocidos, toma la expresión completa
    """
    nombre_norm = normalizar(nombre)

    # Buscar detrás de preposición
    match = re.search(r"(?:de la |del |de )(.+)", nombre_norm)
    if match:
        nucleo = match.group(1).strip()
    else:
        nucleo = nombre_norm

    tokens = [t for t in nucleo.split() if t not in STOPWORDS]

    # Priorizar nombres propios conocidos
    propios = [t for t in tokens if t in NOMBRES_PROPIOS_RELIG]

    if propios:
        return " ".join(propios)
    elif tokens:
        return " ".join(tokens)
    else:
        # Si nada, devolver toda la cadena normalizada
        return nombre_norm

# ============================================================
# CARGA CSV
# ============================================================

def cargar_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el fichero: {path}")
    # Abrir con latin-1 para evitar problemas de acentos
    with open(path, newline="", encoding="latin-1") as f:
        data = list(csv.DictReader(f))
    # Normalizar cabeceras
    data = [{k.strip(): v for k, v in row.items()} for row in data]
    return data

# ============================================================
# INDEXADO DE ENTIDADES SUBVENCIONADAS
# ============================================================

def construir_indice_subvencionadas(subvencionadas):
    index = defaultdict(list)
    for e in subvencionadas:
        nombre = e.get("Entidad financiada", "")
        e["nombre_subvencionada"] = nombre
        e["provincia_detalle"] = e.get("Provincia", "")
        e["localidad"] = e.get("Localidad", "")
        e["nombre_propio"] = extraer_nombre_propio(nombre)
        # Crear índice semántico con cada palabra del nombre propio
        for tok in e["nombre_propio"].split():
            if tok:  # evitar tokens vacíos
                index[tok].append(e)
    log(f"\n🧱 Índice semántico creado con {len(index)} claves")
    for k in list(index.keys())[:5]:
        log(f"   · {k} → {len(index[k])} entidades subvencionadas")
    return index

# ============================================================
# MATCHING
# ============================================================

def similitud(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def ejecutar_matching(entidades, index):
    resultados = []
    log("\n🔗 Matching:")

    for ent in entidades:
        nombre_ent = ent.get("Nombre", "") or ent.get("nombre", "")
        if not nombre_ent:
            continue

        nombre_propio_ent = extraer_nombre_propio(nombre_ent)
        tokens_ent = nombre_propio_ent.split()
        provincia_ent = ent.get("Provincia", "").strip().lower()
        poblacion_ent = ent.get("Poblacion", "").strip().lower()

        candidatos = []
        vistos = set()

        for tok in tokens_ent:
            for e in index.get(tok, []):
                fid = e.get("nombre_subvencionada")
                if fid not in vistos:
                    vistos.add(fid)
                    candidatos.append(e)

        mejor_score = 0.0
        mejor_match = None

        for e in candidatos:
            nombre_propio_subv = e.get("nombre_propio", "")
            propios_ent = set(nombre_propio_ent.split())
            propios_subv = set(nombre_propio_subv.split())
            propios_comunes = propios_ent & propios_subv
            propios_diferentes = (propios_ent - propios_subv) | (propios_subv - propios_ent)

            score = similitud(normalizar(nombre_ent), normalizar(e.get("nombre_subvencionada", "")))

            if propios_comunes:
                # Penalización por nombres propios disconformes
                penalizacion = 0.2 * len(propios_diferentes)
                score -= penalizacion
                score = max(score, 0.0)

                # Bonus geográfico
                prov_subv = e.get("provincia_detalle", "").strip().lower()
                muni_subv = e.get("localidad", "").strip().lower()

                if provincia_ent and provincia_ent == prov_subv:
                    score += 0.1
                if poblacion_ent and poblacion_ent == muni_subv:
                    score += 0.05

                score = min(score, 1.0)
            else:
                # Sin coincidencia de nombres propios -> máximo 30%
                score = min(score, 0.3)

            if score > mejor_score:
                mejor_score = score
                mejor_match = e

        if mejor_match and mejor_score >= MATCH_THRESHOLD:
            log(
                f"✔ MATCH {int(mejor_score*100)}% → "
                f"{nombre_ent[:35]:35} ⇄ {mejor_match['nombre_subvencionada'][:35]}\n"
                f"     • Provincia Entidad: {provincia_ent} | Poblacion Entidad: {poblacion_ent}\n"
                f"     • Provincia Subvencionada: {mejor_match.get('provincia_detalle','').strip().lower()} | "
                f"Localidad Subvencionada: {mejor_match.get('localidad','').strip().lower()}"
            )
            resultados.append({
                "entidad_nombre": nombre_ent,
                "provincia_entidad": provincia_ent,
                "poblacion_entidad": poblacion_ent,
                "subvencionada_nombre": mejor_match["nombre_subvencionada"],
                "provincia_subvencionada": mejor_match.get("provincia_detalle", "").strip().lower(),
                "localidad_subvencionada": mejor_match.get("localidad", "").strip().lower()
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
                "subvencionada_nombre", "provincia_subvencionada", "localidad_subvencionada"
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
    subvencionadas = cargar_csv(SUBVENCIONADAS_CSV)
    log(f"   · Entidades religiosas: {len(entidades)}")
    log(f"   · Entidades subvencionadas: {len(subvencionadas)}")

    index = construir_indice_subvencionadas(subvencionadas)
    resultados = ejecutar_matching(entidades, index)
    guardar_resultados(resultados, OUTPUT_CSV)

    log(f"\n✅ Proceso terminado. Matches encontrados: {len(resultados)}")

if __name__ == "__main__":
    main()
