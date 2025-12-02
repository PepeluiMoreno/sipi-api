#!/usr/bin/env python3
"""
Script para procesar el Excel de inmatriculaciones de la CEE
Genera un CSV por cada comunidad autónoma expandiendo comillas y filtrando totalizadores

Estructura esperada:
    proyecto/
        script/
            procesar_inmatriculaciones.py
        data/
            input/
                nombre_del_excel.xlsx
            output/
                (aquí se generarán los CSVs)

Uso:
    python script/procesar_inmatriculaciones.py nombre_del_excel.xlsx
"""

import pandas as pd
import os
import sys
from pathlib import Path
import unicodedata

# Provincias españolas principales para detectar CCAA multiprovinciales
PROVINCIAS_PRINCIPALES = {
    'ALAVA', 'ALBACETE', 'ALICANTE', 'ALMERIA', 'AVILA', 'BADAJOZ', 'BARCELONA',
    'BURGOS', 'CACERES', 'CADIZ', 'CASTELLON', 'CIUDAD REAL', 'CORDOBA', 'A CORUÑA',
    'CUENCA', 'GIRONA', 'GRANADA', 'GUADALAJARA', 'GUIPUZCOA', 'HUELVA', 'HUESCA',
    'JAEN', 'LEON', 'LLEIDA', 'LUGO', 'MALAGA', 'OURENSE', 'PALENCIA', 'PONTEVEDRA',
    'SALAMANCA', 'SEGOVIA', 'SEVILLA', 'SORIA', 'TARRAGONA', 'TERUEL', 'TOLEDO',
    'VALENCIA', 'VALLADOLID', 'VIZCAYA', 'ZAMORA', 'ZARAGOZA'
}


def normalizar_texto(texto):
    """
    Elimina acentos y caracteres especiales del texto.
    Ejemplo: Cádiz -> Cadiz, León -> Leon
    """
    if pd.isna(texto):
        return texto
    
    texto = str(texto)
    # Normalizar a NFD (descomponer caracteres acentuados)
    texto_nfd = unicodedata.normalize('NFD', texto)
    # Filtrar solo caracteres ASCII (elimina acentos)
    texto_sin_acentos = ''.join(char for char in texto_nfd if unicodedata.category(char) != 'Mn')
    
    return texto_sin_acentos


def es_comilla(valor):
    """Verifica si un valor es comilla (") que debe ser expandida"""
    if pd.isna(valor):
        return False
    val_str = str(valor).strip()
    return val_str == '"' or val_str == '\"'


def es_provincia_multiprovincial(texto):
    """Determina si un texto es nombre de provincia en CCAA multiprovinciales"""
    if not texto:
        return False
    texto_upper = texto.upper().strip()
    
    # Si contiene "Nº", NO es provincia, es un registro
    if 'Nº' in texto or 'NÚM' in texto_upper or 'Nº' in texto_upper:
        return False
    
    # Verificar si está en la lista de provincias principales
    for prov in PROVINCIAS_PRINCIPALES:
        if texto_upper == prov:
            return True
    return False


def es_totalizador(registro_val):
    """Detecta si un registro es un totalizador (contiene palabra TOTAL)"""
    if pd.isna(registro_val):
        return False
    texto = str(registro_val).strip().upper()
    return 'TOTAL' in texto


def es_valor_booleano(valor):
    """Detecta si un valor es SI/NO o 0/1"""
    if pd.isna(valor):
        return False
    
    # Normalizar: quitar espacios y convertir a mayúsculas
    valor_str = str(valor).strip().upper()
    return valor_str in ['SI', 'SÍ', 'NO', '0', '1', '0.0', '1.0']


def convertir_a_booleano(valor):
    """Convierte valores SI/NO o 1/0 a booleanos"""
    if pd.isna(valor):
        return None
    
    # Normalizar: quitar espacios y convertir a mayúsculas
    valor_str = str(valor).strip().upper()
    if valor_str in ['SI', 'SÍ', '1', '1.0']:
        return True
    elif valor_str in ['NO', '0', '0.0']:
        return False
    
    return None


def convertir_templo_dependencias(valor):
    """
    Convierte el campo 'Templo y dependencias complementarias':
    - SI -> True
    - vacío/blanco -> False
    - otros valores -> mantener como texto
    """
    if pd.isna(valor):
        return False
    
    valor_str = str(valor).strip().upper()
    
    if valor_str == '' or valor_str == 'NAN':
        return False
    elif valor_str in ['SI', 'SÍ']:
        return True
    else:
        # Mantener otros valores como texto (ej: "sólo consta parcela")
        return str(valor).strip()


def limpiar_comillas_externas(texto):
    """Elimina solo las comillas que rodean completamente el texto"""
    if pd.isna(texto):
        return texto
    
    texto = str(texto).strip()
    
    # Si el texto empieza y termina con comillas, eliminarlas
    if len(texto) >= 2 and texto[0] == '"' and texto[-1] == '"':
        texto = texto[1:-1].strip()
    
    return texto


def capitalizar_palabra(palabra):
    """
    Capitaliza una palabra considerando guiones, apóstrofes, etc.
    Ejemplos: asidonia-jerez -> Asidonia-Jerez, l'hospitalet -> L'Hospitalet
    """
    if not palabra:
        return palabra
    
    # Si contiene guion, capitalizar cada parte
    if '-' in palabra:
        partes = palabra.split('-')
        return '-'.join([capitalizar_palabra(p) for p in partes])
    
    # Si contiene apóstrofe, capitalizar cada parte
    if "'" in palabra:
        partes = palabra.split("'")
        return "'".join([capitalizar_palabra(p) for p in partes])
    
    # Capitalización normal
    return palabra.capitalize()


def capitalizar_toponimos(texto):
    """
    Convierte texto a minúsculas pero mantiene mayúsculas iniciales en palabras que lo requieren.
    Preserva topónimos, nombres propios y algunas palabras especiales.
    Maneja correctamente palabras con guiones (ej: Asidonia-Jerez)
    """
    if pd.isna(texto):
        return texto
    
    # Primero limpiar comillas externas
    texto = limpiar_comillas_externas(texto)
    texto = str(texto)
    
    # Contar palabras en mayúsculas (excluyendo "Nº" y números)
    palabras = texto.split()
    palabras_mayusculas = 0
    total_palabras_significativas = 0
    
    for palabra in palabras:
        palabra_clean = palabra.replace('Nº', '').replace('nº', '')
        if len(palabra_clean) > 1 and not palabra_clean.isdigit():
            total_palabras_significativas += 1
            if palabra_clean.isupper():
                palabras_mayusculas += 1
    
    # Si la mayoría de palabras están en mayúsculas, capitalizar todo
    debe_capitalizar = False
    if total_palabras_significativas > 0:
        porcentaje_mayusculas = palabras_mayusculas / total_palabras_significativas
        debe_capitalizar = porcentaje_mayusculas > 0.5 or texto.isupper() or texto.islower()
    else:
        debe_capitalizar = texto.isupper() or texto.islower()
    
    # Si es todo mayúsculas, todo minúsculas, o mayoría en mayúsculas: aplicar capitalización inteligente
    if debe_capitalizar:
        # Palabras que deben ir en minúsculas (preposiciones, artículos, conjunciones)
        minusculas = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'e', 'o', 'u', 'a', 'en', 
                      'con', 'por', 'para', 'sobre', 'bajo', 'entre', 'sin'}
        
        # Dividir en palabras
        resultado = []
        
        for i, palabra in enumerate(palabras):
            palabra_lower = palabra.lower()
            
            # Preservar "Nº" tal cual
            if palabra_lower == 'nº' or palabra == 'Nº':
                resultado.append('Nº')
            # Preservar números
            elif palabra.isdigit():
                resultado.append(palabra)
            # Primera palabra siempre con mayúscula inicial
            elif i == 0:
                resultado.append(capitalizar_palabra(palabra))
            # Palabras cortas que van en minúsculas (excepto si es la primera)
            elif palabra_lower in minusculas:
                resultado.append(palabra_lower)
            # Resto de palabras con mayúscula inicial
            else:
                resultado.append(capitalizar_palabra(palabra))
        
        return ' '.join(resultado)
    
    # Si tiene formato mixto correcto, mantenerlo
    return texto


def procesar_excel(excel_path, output_dir):
    """
    Procesa el archivo Excel y genera un CSV por cada comunidad autónoma
    
    Args:
        excel_path: Ruta al archivo Excel
        output_dir: Directorio donde guardar los CSVs
    """
    os.makedirs(output_dir, exist_ok=True)
    
    xls = pd.ExcelFile(excel_path)
    
    # Hojas a procesar (todas excepto Hoja1 que es residual)
    hojas_ca = [sheet for sheet in xls.sheet_names if sheet != 'Hoja1']
    
    print(f"Procesando {len(hojas_ca)} hojas de comunidades autónomas...\n")
    
    estadisticas_globales = []
    
    for sheet_name in hojas_ca:
        print(f"Procesando: {sheet_name}")
        
        # Leer la hoja completa
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        
        # Fila 0: Nombre de la comunidad autónoma
        comunidad_autonoma = str(df.iloc[0, 0]).strip()
        
        # Fila 1: Cabeceras
        headers = list(df.iloc[1].values)
        
        # Datos desde fila 2
        df_raw = df.iloc[2:].reset_index(drop=True)
        
        filas_procesadas = []
        provincia_actual = None
        registro_actual = None
        
        # Detectar si es uniprovincial o multiprovincial
        es_multiprovincial = False
        for idx, row in df_raw.iterrows():
            col_registro = row.iloc[0]
            col_orden = row.iloc[1]
            if pd.isna(col_orden) or str(col_orden).strip() == '' or str(col_orden).strip() == '0':
                if pd.notna(col_registro) and not es_comilla(col_registro):
                    texto = str(col_registro).strip()
                    if es_provincia_multiprovincial(texto):
                        es_multiprovincial = True
                        break
        
        # Si es uniprovincial, la provincia es la misma que la CA
        if not es_multiprovincial:
            provincia_actual = comunidad_autonoma
        
        # Procesar cada fila
        for idx, row in df_raw.iterrows():
            col_registro = row.iloc[0]
            col_orden = row.iloc[1]
            
            # Si col_orden está vacío o es 0, es una fila separadora
            if pd.isna(col_orden) or str(col_orden).strip() == '' or str(col_orden).strip() == '0':
                if pd.notna(col_registro) and not es_comilla(col_registro):
                    texto = str(col_registro).strip()
                    if len(texto) > 0:
                        if es_multiprovincial and es_provincia_multiprovincial(texto):
                            provincia_actual = texto
                        else:
                            registro_actual = texto
                continue
            
            # Es una fila de datos válida
            fila_dict = {}
            
            # Procesar cada columna
            for col_idx, header in enumerate(headers):
                if pd.isna(header):
                    continue
                
                valor = row.iloc[col_idx] if col_idx < len(row) else None
                
                # Expandir comillas
                if es_comilla(valor):
                    for prev_idx in range(idx - 1, -1, -1):
                        prev_valor = df_raw.iloc[prev_idx, col_idx] if col_idx < len(df_raw.iloc[prev_idx]) else None
                        if pd.notna(prev_valor) and not es_comilla(prev_valor):
                            valor = prev_valor
                            break
                
                fila_dict[str(header)] = valor
            
            # Expandir REGISTRO si es comilla o vacío
            if 'REGISTRO' in fila_dict:
                if pd.isna(fila_dict['REGISTRO']) or es_comilla(fila_dict['REGISTRO']):
                    fila_dict['REGISTRO'] = registro_actual
            
            # FILTRAR TOTALIZADORES
            if es_totalizador(fila_dict.get('REGISTRO')):
                continue
            
            # Añadir columnas de Comunidad Autónoma y Provincia
            fila_dict['Comunidad Autónoma'] = comunidad_autonoma
            fila_dict['Provincia'] = provincia_actual
            
            filas_procesadas.append(fila_dict)
        
        # Crear DataFrame final
        df_final = pd.DataFrame(filas_procesadas)
        
        # Reordenar columnas: CA y Provincia al inicio, eliminar Nº Orden y Total
        columnas_ordenadas = ['Comunidad Autónoma', 'Provincia']
        for col in df_final.columns:
            if col not in columnas_ordenadas and col not in ['Nº Orden', 'Total']:
                columnas_ordenadas.append(col)
        
        df_final = df_final[columnas_ordenadas]
        
        # Eliminar columnas completamente vacías
        df_final = df_final.dropna(axis=1, how='all')
        
        # Convertir "Templo y dependencias complementarias" específicamente
        if 'Templo y dependencias complementarias' in df_final.columns:
            df_final['Templo y dependencias complementarias'] = df_final['Templo y dependencias complementarias'].apply(convertir_templo_dependencias)
        
        # Convertir otras columnas booleanas (SI/NO, 1/0)
        for col in df_final.columns:
            if col in ['Comunidad Autónoma', 'Provincia', 'REGISTRO', 'Templo y dependencias complementarias']:
                continue
            
            # Verificar si la columna contiene valores booleanos
            valores_muestra = df_final[col].dropna().head(200)
            if len(valores_muestra) > 0 and all(es_valor_booleano(v) for v in valores_muestra):
                df_final[col] = df_final[col].apply(convertir_a_booleano)
        
        # PASO 1: Aplicar capitalización a TODAS las columnas de texto
        for col in df_final.columns:
            if df_final[col].dtype == 'object' and col != 'Templo y dependencias complementarias':
                df_final[col] = df_final[col].apply(capitalizar_toponimos)
        
        # PASO 2: NORMALIZAR (quitar acentos) en campos específicos DESPUÉS de capitalizar
        campos_normalizar = ['Comunidad Autónoma', 'Provincia', 'REGISTRO', 'Municipio']
        for col in campos_normalizar:
            if col in df_final.columns:
                df_final[col] = df_final[col].apply(normalizar_texto)
        
        # Generar estadísticas por provincia
        stats_provincias = df_final['Provincia'].value_counts().to_dict()
        for provincia, count in stats_provincias.items():
            estadisticas_globales.append({
                'Comunidad Autónoma': comunidad_autonoma,
                'Provincia': provincia,
                'Número de inmatriculaciones': count
            })
        
        # Generar nombre de archivo CSV
        csv_filename = sheet_name.strip().replace(' ', '_').replace('/', '-') + '.csv'
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Guardar CSV con encoding UTF-8 con BOM
        df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"  ✓ Guardado: {csv_filename} ({len(df_final)} filas)")
    
    # Guardar estadísticas globales
    df_stats = pd.DataFrame(estadisticas_globales)
    df_stats = df_stats.sort_values(['Comunidad Autónoma', 'Provincia'])
    stats_path = os.path.join(output_dir, 'estadisticas_por_provincia.csv')
    df_stats.to_csv(stats_path, index=False, encoding='utf-8-sig')
    
    print(f"\n✓ Estadísticas guardadas: estadisticas_por_provincia.csv")
    print(f"\n¡Completado! {len(hojas_ca)} archivos CSV generados en {output_dir}")


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python script/procesar_inmatriculaciones.py <nombre_excel>")
        print("\nEjemplo:")
        print("  python script/procesar_inmatriculaciones.py Inmatriculaciones_CEE.xlsx")
        print("\nEstructura esperada:")
        print("  proyecto/")
        print("      script/")
        print("          procesar_inmatriculaciones.py")
        print("      data/")
        print("          input/")
        print("              nombre_del_excel.xlsx")
        print("          output/")
        print("              (aquí se generarán los CSVs)")
        sys.exit(1)
    
    # Obtener nombre del archivo Excel del parámetro
    excel_filename = sys.argv[1]
    
    # El script está en script/, data/ está al mismo nivel
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'data'
    input_dir = data_dir / 'input'
    output_dir = data_dir / 'output'
    excel_path = input_dir / excel_filename
    
    # Verificar que existe el archivo
    if not excel_path.exists():
        print(f"Error: No se encuentra el archivo '{excel_path}'")
        print(f"\nAsegúrate de que el archivo esté en: {input_dir}")
        sys.exit(1)
    
    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Archivo de entrada: {excel_path}")
    print(f"Directorio de salida: {output_dir}")
    print()
    
    procesar_excel(str(excel_path), str(output_dir))


if __name__ == '__main__':
    main()