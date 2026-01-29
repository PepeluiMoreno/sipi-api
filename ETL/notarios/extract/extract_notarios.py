# extraer_notarios.py
"""
Extrae TODOS los notarios por provincia (sin filtrar por estado)
"""
import requests
import pandas as pd
import time
import json
import os
from typing import List, Dict

BASE_URL = "https://guianotarial.notariado.org"
ENDPOINT = "/guianotarial/rest/buscar/notarios"
CHECKPOINT_FILE = 'checkpoint_notarios.json'

PROVINCIAS = {
    '01': 'Álava', '02': 'Albacete', '03': 'Alicante', '04': 'Almería',
    '05': 'Ávila', '06': 'Badajoz', '07': 'Baleares', '08': 'Barcelona',
    '09': 'Burgos', '10': 'Cáceres', '11': 'Cádiz', '12': 'Castellón',
    '13': 'Ciudad Real', '14': 'Córdoba', '15': 'La Coruña', '16': 'Cuenca',
    '17': 'Gerona', '18': 'Granada', '19': 'Guadalajara', '20': 'Guipúzcoa',
    '21': 'Huelva', '22': 'Huesca', '23': 'Jaén', '24': 'León',
    '25': 'Lérida', '26': 'La Rioja', '27': 'Lugo', '28': 'Madrid',
    '29': 'Málaga', '30': 'Murcia', '31': 'Navarra', '32': 'Orense',
    '33': 'Asturias', '34': 'Palencia', '35': 'Las Palmas', '36': 'Pontevedra',
    '37': 'Salamanca', '38': 'Santa Cruz de Tenerife', '39': 'Cantabria',
    '40': 'Segovia', '41': 'Sevilla', '42': 'Soria', '43': 'Tarragona',
    '44': 'Teruel', '45': 'Toledo', '46': 'Valencia', '47': 'Valladolid',
    '48': 'Vizcaya', '49': 'Zamora', '50': 'Zaragoza', '51': 'Ceuta',
    '52': 'Melilla'
}

# Estados posibles de notarios (para información)
ESTADOS_NOTARIO = {
    'AC': 'Activo',
    'JU': 'Jubilado',
    'EX': 'Excedencia',
    'CE': 'Cesado',
    'FA': 'Fallecido'
}


def buscar_notarios_con_retry(codigoProvincia='', max_reintentos=5):
    """Busca TODOS los notarios (sin filtrar por estado)"""
    
    url = f"{BASE_URL}{ENDPOINT}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://guianotarial.notariado.org',
        'Referer': 'https://guianotarial.notariado.org/guianotarial/',
    }
    
    payload = {
        "nombre": "",
        "apellidos": "",
        "direccion": "",
        "codigoPostal": "",
        "codigoProvincia": codigoProvincia,
        "municipio": "",
        "codigoSituacionNotario": "",  
        "idiomaExtranjero": ""
    }
    
    for intento in range(max_reintentos):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                espera = 2 ** intento * 5
                print(f"\n⚠️  429 Too Many Requests - Esperando {espera}s...")
                time.sleep(espera)
                
                if intento == max_reintentos - 1:
                    print(f"❌ Agotados {max_reintentos} reintentos")
                    return []
            else:
                print(f"❌ HTTP Error {response.status_code}: {e}")
                return []
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    return []


def cargar_checkpoint():
    """Carga checkpoint si existe"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        notarios_dict = {n['codigo_notaria']: n for n in data['notarios']}
        provincias_procesadas = set(data['provincias_procesadas'])
        
        print(f"📦 Checkpoint cargado:")
        print(f"   - {len(notarios_dict)} notarios")
        print(f"   - {len(provincias_procesadas)} provincias procesadas")
        
        return notarios_dict, provincias_procesadas
    
    return {}, set()


def guardar_checkpoint(notarios_dict, provincias_procesadas):
    """Guarda checkpoint"""
    data = {
        'notarios': list(notarios_dict.values()),
        'provincias_procesadas': list(provincias_procesadas),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extraer_por_provincias(delay_base=3):
    """Extrae TODOS los notarios (activos, jubilados, etc.)"""
    
    notarios_dict, provincias_procesadas = cargar_checkpoint()
    
    total = len(PROVINCIAS)
    procesadas = len(provincias_procesadas)
    
    # Estadísticas por estado
    stats_estado = {estado: 0 for estado in ESTADOS_NOTARIO.keys()}
    stats_estado['OTROS'] = 0
    
    print(f"\n🚀 Extrayendo TODOS los notarios (sin filtrar por estado)")
    print(f"   Delay: {delay_base}s")
    print(f"   Pendientes: {total - procesadas}/{total}")
    print("="*70)
    
    for codigo, nombre in PROVINCIAS.items():
        if codigo in provincias_procesadas:
            print(f"[✓] {codigo} - {nombre:25s} → Ya procesada (skip)")
            continue
        
        print(f"[{procesadas+1:2d}/{total}] {codigo} - {nombre:25s} ", end="", flush=True)
        
        notarios = buscar_notarios_con_retry(codigoProvincia=codigo)
        
        nuevos = 0
        for notario in notarios:
            cod_notaria = notario.get('codigoNotaria')
            if cod_notaria and cod_notaria not in notarios_dict:
                notarios_dict[cod_notaria] = notario
                nuevos += 1
                
                # Contar por estado
                estado = notario.get('estado', 'OTROS')
                if estado in stats_estado:
                    stats_estado[estado] += 1
                else:
                    stats_estado['OTROS'] += 1
        
        print(f"→ {len(notarios):4d} notarios | {nuevos:3d} nuevos | Total: {len(notarios_dict):5d}")
        
        provincias_procesadas.add(codigo)
        procesadas += 1
        
        if procesadas % 5 == 0:
            guardar_checkpoint(notarios_dict, provincias_procesadas)
            print(f"💾 Checkpoint guardado ({procesadas}/{total})")
        
        if procesadas < total:
            print(f"   ⏳ Esperando {delay_base}s...", end="\r")
            time.sleep(delay_base)
    
    guardar_checkpoint(notarios_dict, provincias_procesadas)
    print(f"\n✅ Checkpoint final guardado")
    
    # Mostrar estadísticas por estado
    print(f"\n📊 NOTARIOS POR ESTADO:")
    for estado, count in sorted(stats_estado.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            descripcion = ESTADOS_NOTARIO.get(estado, estado)
            print(f"   {estado} ({descripcion}): {count}")
    
    return list(notarios_dict.values())


def generar_csv(notarios, filename='notarios_espana.csv'):
    """Genera CSV ordenado (SIN idiomas ni código últimas voluntades)"""
    
    print("\n📊 Generando CSV...")
    
    df = pd.DataFrame(notarios)
    
    # Renombrar columnas (OMITIR idiomas y código RUV)
    df = df.rename(columns={
        'correoElectronicoPersonal': 'email_personal',
        'correoElectronicoCorporativo': 'email_corporativo',
        'correoElectronicoNotaria': 'email_notaria',
        'codigoNotaria': 'codigo_notaria',
    })
    
    # Ordenar
    df = df.sort_values(
        by=['provincia', 'municipio', 'apellidos_nombre'],
        ascending=[True, True, True]
    )
    
    # Columnas finales (SIN idiomas ni código RUV)
    columnas = [
        'provincia',
        'municipio',
        'apellidos_nombre',
        'direccion',
        'telefono',
        'fax',
        'email_personal',
        'email_corporativo',
        'email_notaria',
        'estado',
        'codigo_notaria',
    ]
    
    df = df[columnas]
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    return df


def main():
    print("="*70)
    print("EXTRACTOR DE NOTARIOS - CGN")
    print("Extrae TODOS los notarios (activos, jubilados, excedencia, etc.)")
    print("="*70)
    print()
    
    print("⚙️  CONFIGURACIÓN:")
    print("   Por defecto: 3 segundos entre peticiones")
    
    try:
        delay_input = input("   ¿Cambiar delay? (Enter=3s, o número): ")
        delay = int(delay_input) if delay_input.strip() else 3
    except:
        delay = 3
    
    print(f"\n✅ Usando delay de {delay} segundos")
    print("💡 Checkpoints cada 5 provincias")
    print("💡 Se extraen TODOS los estados (AC, JU, EX, etc.)\n")
    
    input("Presiona ENTER para comenzar...")
    
    inicio = time.time()
    
    try:
        notarios = extraer_por_provincias(delay_base=delay)
        tiempo = time.time() - inicio
        
        if not notarios:
            print("\n❌ No se extrajeron notarios")
            return
        
        print("\n" + "="*70)
        print("✅ EXTRACCIÓN COMPLETADA")
        print("="*70)
        print(f"   Total notarios: {len(notarios)}")
        print(f"   Tiempo: {tiempo/60:.1f} minutos")
        print("="*70)
        
        df = generar_csv(notarios)
        
        print("\n📈 ESTADÍSTICAS:")
        print(f"   Notarios: {len(df)}")
        print(f"   Provincias: {df['provincia'].nunique()}")
        print(f"   Municipios: {df['municipio'].nunique()}")
        
        # Estadísticas por estado
        if 'estado' in df.columns:
            print("\n📊 Por estado:")
            for estado, count in df['estado'].value_counts().items():
                descripcion = ESTADOS_NOTARIO.get(estado, estado)
                print(f"   {estado} ({descripcion}): {count}")
        
        print("\n🏆 Top 10 provincias:")
        for i, (prov, count) in enumerate(df['provincia'].value_counts().head(10).items(), 1):
            print(f"   {i:2d}. {prov:25s} {count:4d} notarios")
        
        print(f"\n✅ Archivo: notarios_espana.csv")
        
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            print(f"🧹 Checkpoint eliminado")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  INTERRUMPIDO")
        print(f"💾 Progreso en: {CHECKPOINT_FILE}")
        
        notarios_dict, _ = cargar_checkpoint()
        if notarios_dict:
            df = generar_csv(list(notarios_dict.values()), 'notarios_parcial.csv')
            print(f"✅ Parcial guardado: notarios_parcial.csv")


if __name__ == '__main__':
    main()