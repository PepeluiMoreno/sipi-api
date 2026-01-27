
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from unidecode import unidecode
import re
from datetime import datetime
import os
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configurar rutas específicas
RUTA_ENTIDADES = r"C:\Users\Jose\dev\sipi-api\ETL\entidades_religiosas\extract\entidades_catolicas_completo_20260127_081604.csv"
RUTA_FUNDACIONES = r"C:\Users\Jose\dev\sipi-api\ETL\fundaciones\extract\enlaces_fundaciones_20260127_184937.csv"

# LIMITAR A 10 ENTIDADES PARA PRUEBA SUPER DETALLADA
LIMITE_ENTIDADES = 10

# LISTA DE PALABRAS RELIGIOSAS CLAVE (para destacar coincidencias)
PALABRAS_RELIGIOSAS_CLAVE = {
    # Advocaciones marianas
    'fatima', 'lourdes', 'guadalupe', 'pilar', 'carmen', 'merced',
    'concepcion', 'concepción', 'inmaculada', 'purisima', 'purísima',
    'soledad', 'dolores', 'rosario', 'gracia', 'esperanza', 'caridad',
    'consuelo', 'remedio', 'auxilio', 'amparo', 'desamparados',
    'angustias', 'piedad', 'misericordia',
    
    # Nombres de santos
    'jesus', 'cristo', 'maria', 'jose', 'josé', 'juan', 'pedro',
    'pablo', 'francisco', 'antonio', 'teresa', 'isabel', 'ana',
    'joaquin', 'santiago', 'andres', 'mateo', 'lucas', 'marcos',
    'bernardo', 'agustin', 'benito', 'domingo', 'ignacio',
    
    # Conceptos religiosos
    'santisimo', 'santísimo', 'sagrado', 'sagrada', 'divino', 'divina',
    'corazon', 'corazón', 'espiritu', 'espíritu', 'trinidad',
    'redencion', 'redención', 'salvacion', 'salvación',
    'eucaristia', 'eucaristía', 'sacramento',
}

# PALABRAS COMUNES A IGNORAR (no religiosas)
PALABRAS_COMUNES_IGNORAR = {
    'la', 'el', 'los', 'las', 'de', 'del', 'y', 'o', 'en', 'por', 'para',
    'con', 'sin', 'sobre', 'bajo', 'entre', 'hacia', 'desde', 'a', 'ante',
    'cabe', 'contra', 'durante', 'hasta', 'mediante', 'según', 'so',
    'tras', 'versus', 'via',
}

def normalizar_y_destacar(texto):
    """
    Normaliza texto y extrae palabras religiosas
    """
    if pd.isna(texto):
        return '', []
    
    texto_orig = str(texto).strip()
    texto = texto_orig.lower()
    texto = unidecode(texto)
    
    # Extraer todas las palabras
    palabras = re.findall(r'\b\w+\b', texto)
    
    # Separar palabras religiosas de no religiosas
    palabras_religiosas = [p for p in palabras if p in PALABRAS_RELIGIOSAS_CLAVE]
    palabras_no_religiosas = [p for p in palabras if p not in PALABRAS_COMUNES_IGNORAR and p not in PALABRAS_RELIGIOSAS_CLAVE]
    
    return texto, palabras_religiosas, palabras_no_religiosas

def comparar_y_explicar(nombre_ent, nombre_fund, threshold=70):
    """
    Compara dos nombres y explica DETALLADAMENTE por qué sí/no son coincidencia
    """
    # Normalizar y extraer palabras
    ent_norm, ent_relig, ent_no_relig = normalizar_y_destacar(nombre_ent)
    fund_norm, fund_relig, fund_no_relig = normalizar_y_destacar(nombre_fund)
    
    # ENCONTRAR PALABRAS COINCIDENTES (todas, no solo religiosas)
    todas_palabras_ent = set(re.findall(r'\b\w+\b', ent_norm))
    todas_palabras_fund = set(re.findall(r'\b\w+\b', fund_norm))
    
    # PALABRAS COINCIDENTES DE TODO TIPO
    palabras_coincidentes_todas = todas_palabras_ent & todas_palabras_fund
    palabras_coincidentes_relig = set(ent_relig) & set(fund_relig)
    palabras_coincidentes_no_relig = (set(ent_no_relig) & set(fund_no_relig)) - palabras_coincidentes_relig
    
    # Eliminar palabras comunes de la lista de coincidentes
    palabras_coincidentes_todas = palabras_coincidentes_todas - PALABRAS_COMUNES_IGNORAR
    palabras_coincidentes_no_relig = palabras_coincidentes_no_relig - PALABRAS_COMUNES_IGNORAR
    
    # CALCULAR PUNTUACIONES
    similitudes = {}
    
    # 1. Similitud básica
    similitudes['token_set'] = fuzz.token_set_ratio(ent_norm, fund_norm)
    
    # 2. Bonus por palabras religiosas en común
    bonus_religioso = len(palabras_coincidentes_relig) * 20
    bonus_religioso = min(40, bonus_religioso)  # Máximo 40 puntos
    
    # 3. Bonus por palabras no religiosas en común
    bonus_no_religioso = len(palabras_coincidentes_no_relig) * 10
    bonus_no_religioso = min(30, bonus_no_religioso)  # Máximo 30 puntos
    
    # 4. Puntuación final
    puntuacion_final = similitudes['token_set'] + bonus_religioso + bonus_no_religioso
    puntuacion_final = min(100, max(0, puntuacion_final))
    
    # DETERMINAR VEREDICTO
    veredicto = "NO COINCIDENCIA"
    razones = []
    
    # RAZONES PARA ACEPTAR
    if puntuacion_final >= threshold:
        veredicto = "COINCIDENCIA"
        razones.append(f"✅ Puntuación total ({puntuacion_final}%) ≥ umbral ({threshold}%)")
        
        if palabras_coincidentes_relig:
            palabras_str = ", ".join(sorted(palabras_coincidentes_relig))
            razones.append(f"✅ Palabras religiosas en común: {palabras_str}")
        
        if palabras_coincidentes_no_relig:
            palabras_str = ", ".join(sorted(palabras_coincidentes_no_relig))
            razones.append(f"✅ Palabras no religiosas en común: {palabras_str}")
    
    # RAZONES PARA RECHAZAR (si no es coincidencia)
    else:
        razones.append(f"❌ Puntuación total ({puntuacion_final}%) < umbral ({threshold}%)")
        
        # Analizar por qué la puntuación es baja
        if similitudes['token_set'] < 50:
            razones.append(f"❌ Similitud básica muy baja: {similitudes['token_set']}%")
        
        if not palabras_coincidentes_relig:
            razones.append("❌ No hay palabras religiosas en común")
        else:
            palabras_str = ", ".join(sorted(palabras_coincidentes_relig))
            razones.append(f"⚠️  Palabras religiosas en común insuficientes: {palabras_str}")
        
        if not palabras_coincidentes_no_relig:
            razones.append("❌ No hay palabras distintivas no religiosas en común")
        else:
            palabras_str = ", ".join(sorted(palabras_coincidentes_no_relig))
            razones.append(f"⚠️  Palabras no religiosas en común: {palabras_str}")
    
    # INFORMACIÓN DETALLADA PARA MOSTRAR
    info_detallada = {
        # Nombres originales
        'entidad_original': nombre_ent,
        'fundacion_original': nombre_fund,
        
        # Nombres normalizados
        'entidad_normalizada': ent_norm,
        'fundacion_normalizada': fund_norm,
        
        # Palabras encontradas
        'palabras_entidad_religiosas': sorted(ent_relig),
        'palabras_entidad_no_religiosas': sorted(ent_no_relig),
        'palabras_fundacion_religiosas': sorted(fund_relig),
        'palabras_fundacion_no_religiosas': sorted(fund_no_relig),
        
        # Palabras coincidentes
        'palabras_coincidentes_religiosas': sorted(palabras_coincidentes_relig),
        'palabras_coincidentes_no_religiosas': sorted(palabras_coincidentes_no_relig),
        
        # Puntuaciones
        'similitud_token_set': similitudes['token_set'],
        'bonus_religioso': bonus_religioso,
        'bonus_no_religioso': bonus_no_religioso,
        'puntuacion_final': puntuacion_final,
        
        # Veredicto y razones
        'veredicto': veredicto,
        'razones': razones,
    }
    
    return veredicto, puntuacion_final, info_detallada

def mostrar_comparacion_detallada(info, provincia_ent, provincia_fund):
    """
    Muestra una comparación detallada en pantalla
    """
    print(f"\n{'═' * 80}")
    print(f"📊 COMPARACIÓN DETALLADA")
    print(f"{'═' * 80}")
    
    # Mostrar nombres
    print(f"\n🏛️  ENTIDAD RELIGIOSA:")
    print(f"   • Nombre: {info['entidad_original'][:80]}")
    print(f"   • Provincia: {provincia_ent}")
    print(f"   • Palabras religiosas: {', '.join(info['palabras_entidad_religiosas']) if info['palabras_entidad_religiosas'] else 'Ninguna'}")
    print(f"   • Otras palabras: {', '.join(info['palabras_entidad_no_religiosas'][:10]) if info['palabras_entidad_no_religiosas'] else 'Ninguna'}")
    
    print(f"\n💰 FUNDACIÓN:")
    print(f"   • Nombre: {info['fundacion_original'][:80]}")
    print(f"   • Provincia: {provincia_fund}")
    print(f"   • Palabras religiosas: {', '.join(info['palabras_fundacion_religiosas']) if info['palabras_fundacion_religiosas'] else 'Ninguna'}")
    print(f"   • Otras palabras: {', '.join(info['palabras_fundacion_no_religiosas'][:10]) if info['palabras_fundacion_no_religiosas'] else 'Ninguna'}")
    
    print(f"\n🎯 PALABRAS COINCIDENTES:")
    if info['palabras_coincidentes_religiosas']:
        print(f"   ✅ Religiosas: {', '.join(info['palabras_coincidentes_religiosas'])}")
    else:
        print(f"   ❌ Religiosas: Ninguna")
    
    if info['palabras_coincidentes_no_religiosas']:
        print(f"   📝 No religiosas: {', '.join(info['palabras_coincidentes_no_religiosas'])}")
    else:
        print(f"   ❌ No religiosas: Ninguna")
    
    print(f"\n📈 PUNTUACIÓN:")
    print(f"   • Similitud básica: {info['similitud_token_set']}%")
    print(f"   • Bonus palabras religiosas: +{info['bonus_religioso']}%")
    print(f"   • Bonus otras palabras: +{info['bonus_no_religioso']}%")
    print(f"   • PUNTUACIÓN TOTAL: {info['puntuacion_final']}%")
    
    print(f"\n⚖️  VEREDICTO: {info['veredicto']}")
    print(f"\n📝 RAZONES:")
    for razon in info['razones']:
        print(f"   {razon}")
    
    print(f"\n{'─' * 80}")

def procesar_y_mostrar_todo(entidades_df, fundaciones_df, threshold=70):
    """
    Procesa todas las entidades y muestra TODAS las comparaciones
    """
    print("=" * 100)
    print("ANÁLISIS COMPLETO - MOSTRANDO TODAS LAS COMPARACIONES")
    print("=" * 100)
    
    resultados_totales = []
    comparaciones_realizadas = 0
    coincidencias_encontradas = 0
    
    # Tomar muestra de entidades
    entidades_muestra = entidades_df.head(LIMITE_ENTIDADES).copy()
    
    print(f"\n📋 CONFIGURACIÓN:")
    print(f"   • Entidades a analizar: {len(entidades_muestra)}")
    print(f"   • Fundaciones disponibles: {len(fundaciones_df)}")
    print(f"   • Umbral para coincidencia: {threshold}%")
    print(f"   • Palabras religiosas clave: {len(PALABRAS_RELIGIOSAS_CLAVE)}")
    
    # Para cada entidad, comparar con TODAS las fundaciones
    for i, (idx_ent, entidad) in enumerate(entidades_muestra.iterrows()):
        print(f"\n{'=' * 100}")
        print(f"ENTIDAD {i+1}/{len(entidades_muestra)}")
        print(f"{'=' * 100}")
        
        nombre_entidad = entidad['Nombre']
        provincia_entidad = entidad.get('Provincia', 'Desconocida')
        tipo_entidad = entidad.get('Tipo de Entidad', 'Desconocido')
        
        print(f"\n🔍 ANALIZANDO: {nombre_entidad}")
        print(f"   📍 Provincia: {provincia_entidad}")
        print(f"   🏛️  Tipo: {tipo_entidad}")
        
        coincidencias_esta_entidad = 0
        
        # Comparar con cada fundación
        for j, (idx_fund, fundacion) in enumerate(fundaciones_df.iterrows()):
            nombre_fundacion = fundacion['nombre_fundacion']
            provincia_fundacion = fundacion.get('nombre_provincia', 'Desconocida')
            
            # Realizar comparación
            veredicto, puntuacion, info_detallada = comparar_y_explicar(
                nombre_entidad, nombre_fundacion, threshold
            )
            
            comparaciones_realizadas += 1
            
            # MOSTRAR LA COMPARACIÓN (todas, no solo las que pasan el threshold)
            mostrar_comparacion_detallada(info_detallada, provincia_entidad, provincia_fundacion)
            
            # Si es coincidencia, guardarla
            if veredicto == "COINCIDENCIA":
                coincidencias_esta_entidad += 1
                coincidencias_encontradas += 1
                
                resultado = {
                    'numero_inscripcion': entidad['Número de Inscripción'],
                    'nombre_entidad': nombre_entidad,
                    'tipo_entidad': tipo_entidad,
                    'provincia_entidad': provincia_entidad,
                    
                    'nombre_fundacion': nombre_fundacion,
                    'codigo_registro': fundacion.get('codigo_registro', ''),
                    'provincia_fundacion': provincia_fundacion,
                    
                    'puntuacion': puntuacion,
                    'palabras_religiosas_comunes': ', '.join(info_detallada['palabras_coincidentes_religiosas']),
                    'palabras_no_religiosas_comunes': ', '.join(info_detallada['palabras_coincidentes_no_religiosas']),
                    'veredicto': veredicto,
                    'razones': ' | '.join(info_detallada['razones']),
                    
                    'indice_entidad': i,
                    'indice_fundacion': j,
                }
                
                resultados_totales.append(resultado)
        
        print(f"\n📊 RESUMEN PARA ESTA ENTIDAD:")
        print(f"   • Comparaciones realizadas: {len(fundaciones_df)}")
        print(f"   • Coincidencias encontradas: {coincidencias_esta_entidad}")
        
        if coincidencias_esta_entidad == 0:
            print(f"   ⚠️  No se encontraron coincidencias para esta entidad")
    
    # RESUMEN FINAL
    print(f"\n{'=' * 100}")
    print(f"RESUMEN FINAL DEL ANÁLISIS")
    print(f"{'=' * 100}")
    
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"   • Entidades analizadas: {len(entidades_muestra)}")
    print(f"   • Comparaciones realizadas: {comparaciones_realizadas}")
    print(f"   • Coincidencias totales encontradas: {coincidencias_encontradas}")
    print(f"   • Tasa de coincidencia: {coincidencias_encontradas/comparaciones_realizadas*100:.2f}%")
    print(f"   • Umbral utilizado: {threshold}%")
    
    if resultados_totales:
        df_resultados = pd.DataFrame(resultados_totales)
        print(f"\n🏆 MEJORES COINCIDENCIAS (Top 5):")
        
        mejores = df_resultados.nlargest(5, 'puntuacion')
        for idx, (_, row) in enumerate(mejores.iterrows()):
            print(f"\n   {idx+1}. Puntuación: {row['puntuacion']}%")
            print(f"      Entidad: {row['nombre_entidad'][:60]}")
            print(f"      Fundación: {row['nombre_fundacion'][:60]}")
            print(f"      Palabras religiosas en común: {row['palabras_religiosas_comunes']}")
            print(f"      Palabras otras en común: {row['palabras_no_religiosas_comunes']}")
    
    return pd.DataFrame(resultados_totales) if resultados_totales else pd.DataFrame()

def main():
    """Función principal"""
    print("=" * 100)
    print("ANALIZADOR COMPLETO DE COINCIDENCIAS ENTIDADES-FUNDACIONES")
    print("MOSTRANDO TODAS LAS COMPARACIONES Y RAZONES")
    print("=" * 100)
    
    # Cargar datos
    print(f"\n📂 Cargando archivos...")
    
    try:
        entidades_df = pd.read_csv(RUTA_ENTIDADES, encoding='utf-8', dtype=str)
        fundaciones_df = pd.read_csv(RUTA_FUNDACIONES, encoding='utf-8', dtype=str)
        
        print(f"   ✓ Entidades religiosas: {len(entidades_df)} registros")
        print(f"   ✓ Fundaciones: {len(fundaciones_df)} registros")
        print(f"   ✓ Para esta prueba analizando solo: {LIMITE_ENTIDADES} entidades")
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return
    
    # Configurar
    print(f"\n🔧 Configuración del análisis:")
    threshold = 70
    
    try:
        user_input = input(f"   Umbral de coincidencia (60-80%, Enter para {threshold}%): ").strip()
        if user_input:
            threshold = int(user_input)
            if threshold < 50 or threshold > 90:
                threshold = 70
    except:
        pass
    
    print(f"   ✓ Umbral establecido en: {threshold}%")
    print(f"   ✓ Se mostrarán TODAS las comparaciones, no solo las coincidencias")
    
    # Ejecutar análisis
    print(f"\n{'=' * 100}")
    print(f"INICIANDO ANÁLISIS COMPLETO")
    print(f"{'=' * 100}")
    
    input("\n⚠️  Presiona Enter para comenzar (se mostrarán MUCHAS comparaciones)...")
    
    resultados_df = procesar_y_mostrar_todo(entidades_df, fundaciones_df, threshold)
    
    # Guardar resultados
    if not resultados_df.empty:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'coincidencias_COMPLETAS_{LIMITE_ENTIDADES}_th{threshold}_{timestamp}.csv'
        
        resultados_df.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 RESULTADOS GUARDADOS EN: {nombre_archivo}")
        print(f"   Contiene {len(resultados_df)} coincidencias encontradas")
    
    print(f"\n{'=' * 100}")
    print(f"ANÁLISIS FINALIZADO")
    print(f"{'=' * 100}")

if __name__ == "__main__":
    main()