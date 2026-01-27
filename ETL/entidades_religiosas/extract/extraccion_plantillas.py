import pandas as pd
import re
from collections import Counter
from unidecode import unidecode
import json
from pathlib import Path

# Configurar rutas
RUTA_ENTIDADES = r"C:\Users\Jose\dev\sipi-api\ETL\entidades_religiosas\extract\entidades_catolicas_completo_20260127_081604.csv"

def extraer_estructuras_sintacticas():
    """
    Extrae las estructuras sintácticas REALES usadas en nombres de entidades religiosas
    """
    
    print("=" * 80)
    print("EXTRACCIÓN DE ESTRUCTURAS SINTÁCTICAS DE ENTIDADES RELIGIOSAS")
    print("=" * 80)
    
    # Cargar datos
    try:
        df = pd.read_csv(RUTA_ENTIDADES, encoding='utf-8', dtype=str)
        print(f"✓ Cargadas {len(df)} entidades religiosas")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Diccionarios para estructuras
    estructuras_sintacticas = Counter()
    patrones_especificos = []
    elementos_por_posicion = {
        'inicio': Counter(),    # Primer elemento
        'medio': Counter(),     # Elementos intermedios  
        'final': Counter(),     # Último elemento
        'conector': Counter(),  # Palabras conectivas
    }
    
    # Clasificación de palabras
    CATEGORIAS = {
        # Tipos de entidad
        'TIPO': {
            'cofradia', 'cofradía', 'hermandad', 'archicofradia', 'archicofradía',
            'asociacion', 'asociación', 'fundacion', 'fundación',
            'comunidad', 'congregacion', 'congregación', 'instituto', 'orden',
            'monasterio', 'convento', 'abadia', 'abadía', 'ermita', 'santuario',
            'parroquia', 'iglesia', 'capilla', 'oratorio', 'obra', 'provincia',
            'casa', 'colegio', 'residencia', 'hospital', 'asilo', 'albergue',
        },
        
        # Títulos/calificativos
        'TITULO': {
            'real', 'ilustre', 'venerable', 'antigua', 'muy', 'muy ilustre',
            'santa', 'santo', 'san', 'santísimo', 'santisimo', 'divino', 'divina',
            'nacional', 'regional', 'provincial', 'diocesano', 'diocesana',
        },
        
        # Artículos/preposiciones
        'CONECTOR': {
            'la', 'el', 'los', 'las', 'de', 'del', 'y', 'o', 'en', 'por', 'para',
            'con', 'sin', 'sobre', 'bajo', 'entre', 'hacia', 'desde', 'a',
        },
        
        # Términos religiosos genéricos
        'RELIG_GENERICO': {
            'nuestra', 'señora', 'señor', 'virgen', 'maria', 'jesus', 'cristo',
            'madre', 'padre', 'hermanos', 'hermanas', 'sagrado', 'sagrada',
            'corazon', 'corazón', 'espiritu', 'espíritu', 'trinidad',
        },
    }
    
    # Para nombres propios (se detectan dinámicamente)
    nombres_propios = Counter()
    
    print("\n🔍 ANALIZANDO ESTRUCTURAS SINTÁCTICAS...")
    
    for idx, nombre in enumerate(df['Nombre'].dropna()):
        nombre = str(nombre).strip()
        if not nombre:
            continue
        
        # Normalizar
        nombre_norm = unidecode(nombre.lower())
        
        # Tokenizar
        tokens = nombre_norm.split()
        
        if len(tokens) < 2:
            continue
        
        # 1. Extraer estructura sintáctica (categorías de palabras)
        estructura = []
        elementos_reales = []
        
        for i, token in enumerate(tokens):
            categoria_encontrada = 'PROPIO'  # Por defecto, nombre propio
            
            # Buscar en categorías
            for categoria, palabras in CATEGORIAS.items():
                if token in palabras:
                    categoria_encontrada = categoria
                    break
            
            # Si no está en categorías conocidas, es probablemente nombre propio
            if categoria_encontrada == 'PROPIO' and len(token) > 2:
                nombres_propios[token] += 1
            
            estructura.append(categoria_encontrada)
            elementos_reales.append(token)
        
        # 2. Guardar estructura sintáctica
        estructura_str = ' '.join(estructura)
        estructuras_sintacticas[estructura_str] += 1
        
        # 3. Analizar por posición
        if len(tokens) >= 1:
            elementos_por_posicion['inicio'][tokens[0]] += 1
        
        if len(tokens) >= 2:
            elementos_por_posicion['final'][tokens[-1]] += 1
        
        # Elementos del medio (excluyendo primero y último)
        for i in range(1, len(tokens) - 1):
            elementos_por_posicion['medio'][tokens[i]] += 1
        
        # 4. Guardar patrón específico con ejemplos
        patron_especifico = {
            'estructura': estructura_str,
            'ejemplo': nombre,
            'tokens_reales': elementos_reales,
            'categorias': estructura,
        }
        patrones_especificos.append(patron_especifico)
        
        # Mostrar progreso
        if idx < 10:  # Mostrar primeros 10 ejemplos
            print(f"\n  Ejemplo {idx+1}:")
            print(f"    Original: {nombre}")
            print(f"    Tokens: {elementos_reales}")
            print(f"    Estructura: {estructura_str}")
    
    # ANALIZAR RESULTADOS
    print("\n" + "=" * 80)
    print("RESULTADOS DEL ANÁLISIS SINTÁCTICO")
    print("=" * 80)
    
    # 1. Estructuras sintácticas más comunes
    print(f"\n🏗️  ESTRUCTURAS SINTÁCTICAS MÁS COMUNES (Top 20):")
    print("-" * 60)
    
    for estructura, count in estructuras_sintacticas.most_common(20):
        print(f"  {count:4d} | {estructura}")
    
    # 2. Nombres propios más comunes
    print(f"\n🏛️  NOMBRES PROPIOS MÁS FRECUENTES (Top 20):")
    print("-" * 60)
    
    for nombre, count in nombres_propios.most_common(20):
        print(f"  {count:4d} | {nombre}")
    
    # 3. Elementos por posición
    print(f"\n📍 ELEMENTOS MÁS COMUNES POR POSICIÓN:")
    
    print(f"\n  AL INICIO:")
    for elemento, count in elementos_por_posicion['inicio'].most_common(10):
        print(f"    {count:4d} | {elemento}")
    
    print(f"\n  AL FINAL:")
    for elemento, count in elementos_por_posicion['final'].most_common(10):
        print(f"    {count:4d} | {elemento}")
    
    # 4. Patrones sintácticos específicos para búsqueda
    print(f"\n🔍 PATRONES SINTÁCTICOS PARA BÚSQUEDA:")
    print("-" * 60)
    
    # Agrupar patrones por estructura
    patrones_agrupados = {}
    for patron in patrones_especificos:
        estructura = patron['estructura']
        if estructura not in patrones_agrupados:
            patrones_agrupados[estructura] = []
        patrones_agrupados[estructura].append(patron['ejemplo'])
    
    # Mostrar los patrones más comunes con ejemplos
    for estructura, count in estructuras_sintacticas.most_common(10):
        if count > 5:  # Solo patrones con múltiples ocurrencias
            print(f"\n  🏷️  Patrón: {estructura} ({count} ocurrencias)")
            print(f"  📝 Ejemplos:")
            ejemplos = patrones_agrupados.get(estructura, [])
            for i, ejemplo in enumerate(ejemplos[:3]):  # Mostrar hasta 3 ejemplos
                print(f"     {i+1}. {ejemplo}")
    
    # 5. Generar plantillas de búsqueda inteligentes
    print(f"\n🎯 PLANTILLAS DE BÚSQUEDA INTELIGENTES:")
    print("-" * 60)
    
    plantillas_busqueda = []
    
    for estructura, count in estructuras_sintacticas.most_common(15):
        if count < 5:
            continue
        
        # Crear plantilla a partir de estructura
        tokens_estructura = estructura.split()
        plantilla = []
        
        for token in tokens_estructura:
            if token == 'PROPIO':
                plantilla.append('[NOMBRE_PROPIO]')
            elif token == 'TIPO':
                plantilla.append('[TIPO_ENTIDAD]')
            elif token == 'TITULO':
                plantilla.append('[TITULO]')
            elif token == 'RELIG_GENERICO':
                plantilla.append('[TERMINO_RELIGIOSO]')
            elif token == 'CONECTOR':
                plantilla.append('[CONECTOR]')
            else:
                plantilla.append(token)
        
        plantilla_str = ' '.join(plantilla)
        
        # Obtener ejemplos reales
        ejemplos = patrones_agrupados.get(estructura, [])
        
        plantillas_busqueda.append({
            'plantilla': plantilla_str,
            'estructura_original': estructura,
            'frecuencia': count,
            'ejemplos': ejemplos[:3],  # Primeros 3 ejemplos
        })
        
        print(f"\n  📋 Plantilla: {plantilla_str}")
        print(f"     Frecuencia: {count} ocurrencias")
        if ejemplos:
            print(f"     Ejemplo: {ejemplos[0]}")
    
    # 6. Identificar patrones problemáticos (para depuración)
    print(f"\n⚠️  PATRONES PROBLEMÁTICOS DETECTADOS:")
    print("-" * 60)
    
    patrones_problematicos = []
    
    # Patrones que pueden generar falsos positivos
    for estructura, count in estructuras_sintacticas.items():
        tokens = estructura.split()
        
        # Identificar patrones con muchos términos genéricos
        count_genericos = sum(1 for t in tokens if t in ['RELIG_GENERICO', 'CONECTOR'])
        ratio_genericos = count_genericos / len(tokens) if tokens else 0
        
        if ratio_genericos > 0.7 and count > 3:  # Más del 70% genérico
            patrones_problematicos.append({
                'estructura': estructura,
                'ratio_genericos': ratio_genericos,
                'count': count,
                'ejemplos': patrones_agrupados.get(estructura, [])[:2]
            })
    
    for problema in patrones_problematicos[:5]:  # Mostrar primeros 5
        print(f"\n  ❗ Estructura: {problema['estructura']}")
        print(f"     Ratio términos genéricos: {problema['ratio_genericos']:.1%}")
        print(f"     Ocurrencias: {problema['count']}")
        if problema['ejemplos']:
            print(f"     Ejemplo: {problema['ejemplos'][0]}")
    
    # GUARDAR RESULTADOS
    resultados = {
        'estructuras_sintacticas': dict(estructuras_sintacticas.most_common(100)),
        'nombres_propios_comunes': dict(nombres_propios.most_common(100)),
        'elementos_por_posicion': {k: dict(v.most_common(50)) for k, v in elementos_por_posicion.items()},
        'plantillas_busqueda': plantillas_busqueda,
        'patrones_especificos': patrones_especificos[:100],  # Primeros 100
        'patrones_problematicos': patrones_problematicos,
    }
    
    with open('estructuras_sintacticas.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados guardados en: estructuras_sintacticas.json")
    
 

if __name__ == "__main__":
    extraer_estructuras_sintacticas()