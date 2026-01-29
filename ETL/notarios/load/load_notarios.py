#!/usr/bin/env python3
"""
load_notarios.py

Carga datos de notarías y titulares transformados a la base de datos.
Lee los CSV de ../transform/ y carga a las tablas notarias y notarias_titulares.
Usa el mismo patrón que load_geografia.py.
"""

import sys
from pathlib import Path
from datetime import datetime
import asyncio
import uuid
from typing import Dict, Tuple
import pandas as pd
from sqlalchemy import select, update, and_
import hashlib
import logging

# Importar desde sipi-core
from sipi_core.db.sessions.async_session import db_manager
from sipi_core.models.actores import Notaria, NotariaTitular


def setup_logging():
    """Configura logging específico para carga de notarías"""
    script_dir = Path(__file__).parent
    log_file = script_dir / 'notarias_load.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def generar_hash_registro(*campos) -> str:
    """Genera hash MD5 para detectar cambios en registros"""
    contenido = '|'.join(str(campo) for campo in campos if campo is not None)
    return hashlib.md5(contenido.encode('utf-8')).hexdigest()


def generar_nombre_notaria(codigo_notaria: str, direccion: str) -> str:
    """Genera un nombre para la notaría usando el patrón sugerido"""
    # Limpiar la dirección para el nombre
    if direccion:
        # Tomar los primeros 60 caracteres de la dirección
        # Remover caracteres problemáticos si los hay
        direccion_limpia = direccion[:60].strip()
        if len(direccion) > 60:
            direccion_limpia += "..."
        nombre = f"Notaría {codigo_notaria} - {direccion_limpia}"
    else:
        nombre = f"Notaría {codigo_notaria}"
    
    # Asegurar que no exceda 255 caracteres (límite de la columna)
    return nombre[:255]


async def cargar_notarias(session, df_notarias: pd.DataFrame) -> Tuple[Dict[str, str], Dict]:
    """
    Carga y sincroniza notarías con las transformaciones necesarias:
    1. codigo_notaria -> codigo_oficial
    2. Generar nombre: "Notaría 150026001 - Rua das Palmeiras..."
    3. Ignorar campos que no están en el modelo (INE codes, etc.)
    """
    logger.info("=== CARGA DE NOTARÍAS ===")
    total_csv = len(df_notarias)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Obtener todos los registros actuales de BD
    result = await session.execute(select(Notaria))
    # Mapear por codigo_oficial para búsqueda
    notarias_by_codigo = {notaria.codigo_oficial: notaria for notaria in result.scalars() if notaria.codigo_oficial}
    logger.info(f"Registros en BD: {len(notarias_by_codigo)}")
    
    # Preparar estadísticas
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'sin_cambios': 0,
        'errores': 0,
        'sin_codigo': 0,
        'sin_municipio': 0
    }
    
    id_cache = {}  # id_csv -> id_bd (para referencia en titulares)
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_notarias.itertuples(), 1):
        id_csv = str(row.id).strip() if hasattr(row, 'id') else ''
        codigo_notaria = str(row.codigo_notaria).strip() if hasattr(row, 'codigo_notaria') else ''
        municipio_id = str(row.municipio_id).strip() if hasattr(row, 'municipio_id') else ''
        
        if not codigo_notaria:
            stats['sin_codigo'] += 1
            logger.warning(f"Fila {idx}: Sin código de notaría, omitiendo")
            continue
        
        if not municipio_id:
            stats['sin_municipio'] += 1
            logger.warning(f"Notaría {codigo_notaria}: Sin municipio_id, omitiendo")
            continue
        
        try:
            # TRANSFORMACIÓN: Generar nombre como sugeriste
            direccion = getattr(row, 'direccion', '') if hasattr(row, 'direccion') else ''
            nombre = generar_nombre_notaria(codigo_notaria, direccion)
            
            # TRANSFORMACIÓN: codigo_notaria -> codigo_oficial
            codigo_oficial = codigo_notaria
            
            # Limpiar valores para campos opcionales (convertir '' a None)
            codigo_postal = getattr(row, 'codigo_postal', None)
            if codigo_postal == '':
                codigo_postal = None
            
            telefono = getattr(row, 'telefono', None)
            if telefono == '':
                telefono = None
            
            fax = getattr(row, 'fax', None)
            if fax == '':
                fax = None
            
            email = getattr(row, 'email', None)
            if email == '':
                email = None
            
            # Verificar si la notaría ya existe (por codigo_oficial)
            notaria_existente = notarias_by_codigo.get(codigo_oficial)
            
            if notaria_existente:
                # REGISTRO EXISTENTE
                existing = notaria_existente
                
                # Generar hash para comparación (solo campos del modelo)
                hash_csv = generar_hash_registro(
                    nombre,
                    codigo_oficial,
                    direccion,
                    codigo_postal,
                    telefono,
                    fax,
                    email,
                    municipio_id
                )
                
                # Hash de BD
                hash_bd = generar_hash_registro(
                    existing.nombre,
                    existing.codigo_oficial,
                    existing.direccion,
                    existing.codigo_postal,
                    existing.telefono,
                    existing.fax,
                    existing.email,
                    str(existing.municipio_id) if existing.municipio_id else ''
                )
                
                if hash_csv != hash_bd:
                    # Actualizar con valores transformados
                    update_values = {
                        'nombre': nombre,
                        'codigo_oficial': codigo_oficial,
                        'direccion': direccion,
                        'codigo_postal': codigo_postal,
                        'telefono': telefono,
                        'fax': fax,
                        'email': email,
                        'municipio_id': municipio_id,
                        'audit_modificado_en': datetime.utcnow(),
                        'audit_modificado_por': 'load_notarios.py'
                    }
                    
                    stmt = (
                        update(Notaria)
                        .where(Notaria.id == existing.id)
                        .values(**update_values)
                    )
                    await session.execute(stmt)
                    stats['actualizadas'] += 1
                    logger.debug(f"Notaría actualizada: {codigo_notaria}")
                else:
                    stats['sin_cambios'] += 1
                
                id_cache[id_csv] = str(existing.id)
                
            else:
                # NUEVO REGISTRO
                # Usar id_csv si es UUID válido
                try:
                    uuid.UUID(id_csv)
                    new_id = id_csv
                except (ValueError, AttributeError):
                    new_id = str(uuid.uuid4())
                
                new_notaria = Notaria(
                    id=new_id,
                    nombre=nombre,
                    codigo_oficial=codigo_oficial,
                    direccion=direccion,
                    codigo_postal=codigo_postal,
                    telefono=telefono,
                    fax=fax,
                    email=email,
                    municipio_id=municipio_id,
                    # Campos de auditoría
                    audit_creado_en=datetime.utcnow(),
                    audit_creado_por='load_notarios.py',
                    audit_modificado_en=datetime.utcnow(),
                    audit_modificado_por='load_notarios.py'
                )
                session.add(new_notaria)
                id_cache[id_csv] = new_id
                stats['nuevas'] += 1
                logger.debug(f"Notaría nueva: {codigo_notaria}")
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando notaría {codigo_notaria}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Log progreso
        if idx % 100 == 0:
            logger.info(f"Procesadas {idx}/{total_csv} notarías")
    
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN NOTARÍAS:")
    logger.info(f"  Nuevas: {stats['nuevas']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Sin código: {stats['sin_codigo']}")
    logger.info(f"  Sin municipio: {stats['sin_municipio']}")
    logger.info(f"  IDs en cache: {len(id_cache)}")
    logger.info("=" * 50)
    
    return id_cache, stats


async def cargar_titulares(session, df_titulares: pd.DataFrame, id_cache: Dict[str, str]) -> Dict:
    """
    Carga titulares de notarías.
    Solo incluye campos que existen en el modelo NotariaTitular.
    Ignora: codigo_ultimas_voluntades, idiomas_extranjeros, estado
    """
    logger.info("=== CARGA DE TITULARES ===")
    total_csv = len(df_titulares)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Preparar estadísticas
    stats = {
        'nuevos': 0,
        'actualizados': 0,
        'sin_cambios': 0,
        'errores': 0,
        'referencias_invalidas': 0,
        'sin_notaria': 0
    }
    
    batch_size = 500
    processed = 0
    
    # Crear un mapeo de titulares existentes
    result = await session.execute(select(NotariaTitular))
    titulares_existencia = {}
    for titular in result.scalars():
        # Usar notaria_id + apellidos_nombre como clave (puede haber duplicados históricos)
        key = f"{titular.notaria_id}_{titular.apellidos_nombre}"
        titulares_existencia[key] = titular
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_titulares.itertuples(), 1):
        notaria_id_csv = str(row.notaria_id).strip() if hasattr(row, 'notaria_id') else ''
        apellidos_nombre = str(row.apellidos_nombre).strip() if hasattr(row, 'apellidos_nombre') else ''
        
        if not notaria_id_csv:
            stats['sin_notaria'] += 1
            continue
        
        if notaria_id_csv not in id_cache:
            stats['referencias_invalidas'] += 1
            if stats['referencias_invalidas'] <= 5:
                logger.warning(f"Notaría ID {notaria_id_csv} no encontrada en BD para titular {apellidos_nombre}")
            continue
        
        notaria_id_bd = id_cache[notaria_id_csv]
        
        try:
            # Parsear fechas
            fecha_inicio = None
            if hasattr(row, 'fecha_inicio') and pd.notna(row.fecha_inicio):
                fecha_inicio = pd.to_datetime(row.fecha_inicio).date()
            else:
                fecha_inicio = datetime.utcnow().date()
            
            fecha_fin = None
            if hasattr(row, 'fecha_fin') and pd.notna(row.fecha_fin):
                fecha_fin = pd.to_datetime(row.fecha_fin).date()
            
            # Generar clave para este titular
            key = f"{notaria_id_bd}_{apellidos_nombre}"
            
            # Campos a considerar (solo los que están en el modelo)
            email_personal = getattr(row, 'email_personal', '')
            if email_personal == '':
                email_personal = None
            
            email_corporativo = getattr(row, 'email_corporativo', '')
            if email_corporativo == '':
                email_corporativo = None
            
            # Generar hash SOLO de los campos del modelo
            hash_csv = generar_hash_registro(
                apellidos_nombre,
                email_personal,
                email_corporativo,
                str(fecha_inicio),
                str(fecha_fin) if fecha_fin else ''
            )
            
            if key in titulares_existencia:
                # REGISTRO EXISTENTE
                existing = titulares_existencia[key]
                
                # Hash de BD
                hash_bd = generar_hash_registro(
                    existing.apellidos_nombre,
                    existing.email_personal,
                    existing.email_corporativo,
                    str(existing.fecha_inicio),
                    str(existing.fecha_fin) if existing.fecha_fin else ''
                )
                
                if hash_csv != hash_bd:
                    # Actualizar solo campos del modelo
                    update_values = {}
                    
                    if email_personal != existing.email_personal:
                        update_values['email_personal'] = email_personal
                    if email_corporativo != existing.email_corporativo:
                        update_values['email_corporativo'] = email_corporativo
                    if fecha_fin != existing.fecha_fin:
                        update_values['fecha_fin'] = fecha_fin
                    
                    if update_values:
                        update_values.update({
                            'audit_modificado_en': datetime.utcnow(),
                            'audit_modificado_por': 'load_notarios.py'
                        })
                        
                        stmt = (
                            update(NotariaTitular)
                            .where(NotariaTitular.id == existing.id)
                            .values(**update_values)
                        )
                        await session.execute(stmt)
                        stats['actualizados'] += 1
                        logger.debug(f"Titular actualizado: {apellidos_nombre}")
                else:
                    stats['sin_cambios'] += 1
                    
            else:
                # NUEVO REGISTRO
                new_id = str(uuid.uuid4())
                new_titular = NotariaTitular(
                    id=new_id,
                    apellidos_nombre=apellidos_nombre,
                    email_personal=email_personal,
                    email_corporativo=email_corporativo,
                    # NOTA: No incluir codigo_ultimas_voluntades, idiomas_extranjeros, estado
                    notaria_id=notaria_id_bd,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    # Campos de auditoría
                    audit_creado_en=datetime.utcnow(),
                    audit_creado_por='load_notarios.py',
                    audit_modificado_en=datetime.utcnow(),
                    audit_modificado_por='load_notarios.py'
                )
                session.add(new_titular)
                stats['nuevos'] += 1
                logger.debug(f"Titular nuevo: {apellidos_nombre}")
            
            processed += 1
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando titular {apellidos_nombre}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Commit y log progreso por lotes
        if idx % batch_size == 0:
            await session.commit()
            porcentaje = (idx / total_csv) * 100
            logger.info(f"Procesados {idx}/{total_csv} ({porcentaje:.1f}%) titulares")
    
    # Commit final
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN TITULARES:")
    logger.info(f"  Nuevos: {stats['nuevos']}")
    logger.info(f"  Actualizados: {stats['actualizados']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Referencias inválidas: {stats['referencias_invalidas']}")
    logger.info(f"  Sin notaría: {stats['sin_notaria']}")
    logger.info(f"  Total procesados: {processed}")
    logger.info("=" * 50)
    
    return stats


async def verificar_integridad_referencial(session, id_cache: Dict[str, str]) -> Dict:
    """
    Verifica la integridad referencial después de la carga.
    """
    logger.info("=== VERIFICACIÓN DE INTEGRIDAD REFERENCIAL ===")
    
    stats = {
        'notarias_sin_titulares': 0,
        'titulares_sin_notaria': 0
    }
    
    # IDs de notarías en BD
    notaria_ids_bd = list(id_cache.values())
    
    # 1. Verificar notarías sin titulares
    for notaria_id in notaria_ids_bd:
        result = await session.execute(
            select(NotariaTitular).where(NotariaTitular.notaria_id == notaria_id)
        )
        titulares = result.scalars().all()
        
        if not titulares:
            stats['notarias_sin_titulares'] += 1
            logger.warning(f"Notaría ID {notaria_id} no tiene titulares")
    
    # 2. Verificar titulares sin notaría válida
    result = await session.execute(
        select(NotariaTitular).where(
            NotariaTitular.notaria_id.not_in(notaria_ids_bd)
        )
    )
    titulares_sin_notaria = result.scalars().all()
    stats['titulares_sin_notaria'] = len(titulares_sin_notaria)
    
    if titulares_sin_notaria:
        logger.warning(f"Encontrados {len(titulares_sin_notaria)} titulares sin notaría válida")
        for titular in titulares_sin_notaria[:5]:
            logger.warning(f"  - {titular.apellidos_nombre} (Notaría ID: {titular.notaria_id})")
    
    logger.info("=" * 50)
    logger.info("RESUMEN INTEGRIDAD REFERENCIAL:")
    logger.info(f"  Notarías sin titulares: {stats['notarias_sin_titulares']}")
    logger.info(f"  Titulares sin notaría válida: {stats['titulares_sin_notaria']}")
    logger.info("=" * 50)
    
    return stats


async def verificar_conteos_finales(session):
    """Verificar conteos finales en la base de datos"""
    logger.info("=== VERIFICACIÓN DE CONTEO FINAL ===")
    
    # Contar notarías
    result = await session.execute(select(Notaria))
    todas_notarias = result.scalars().all()
    
    # Contar titulares
    result = await session.execute(select(NotariaTitular))
    todos_titulares = result.scalars().all()
    
    # Imprimir resumen
    print("\n" + "=" * 80)
    print("RESUMEN FINAL EN BASE DE DATOS:")
    print("=" * 80)
    print(f"Notarías: {len(todas_notarias)} registros")
    print(f"Titulares: {len(todos_titulares)} registros")
    print("=" * 80)
    
    logger.info("RESUMEN FINAL EN BASE DE DATOS:")
    logger.info(f"Notarías: {len(todas_notarias)} registros")
    logger.info(f"Titulares: {len(todos_titulares)} registros")


async def cargar_datos(df_notarias: pd.DataFrame, df_titulares: pd.DataFrame):
    """Ejecuta la carga de datos de notarías"""
    logger.info("=" * 80)
    logger.info("INICIANDO CARGA DE DATOS DE NOTARÍAS")
    logger.info("=" * 80)
    logger.info(f"Datos a cargar:")
    logger.info(f"  - Notarías: {len(df_notarias)} registros")
    logger.info(f"  - Titulares: {len(df_titulares)} registros")
    
    try:
        async with db_manager.session() as session:
            # Iniciar transacción global
            await session.begin()
            
            try:
                # 1. Cargar Notarías
                id_cache, stats_notarias = await cargar_notarias(session, df_notarias)
                
                # 2. Cargar Titulares
                stats_titulares = await cargar_titulares(session, df_titulares, id_cache)
                
                # 3. Verificar integridad referencial
                stats_integridad = await verificar_integridad_referencial(session, id_cache)
                
                # 4. Commit transacción global
                await session.commit()
                
                # 5. Verificar conteos finales
                await verificar_conteos_finales(session)
                
                # 6. Reporte consolidado
                logger.info("=" * 80)
                logger.info("CARGA COMPLETADA EXITOSAMENTE")
                logger.info("=" * 80)
                
                print("\n" + "=" * 80)
                print("CARGA COMPLETADA EXITOSAMENTE")
                print("=" * 80)
                
                # Reporte detallado
                print("\nRESUMEN DE CAMBIOS:")
                print(f"Notarías: +{stats_notarias['nuevas']} nuevas, ↑{stats_notarias['actualizadas']} actualizadas")
                print(f"Titulares: +{stats_titulares['nuevos']} nuevos, ↑{stats_titulares['actualizados']} actualizados")
                
                if stats_notarias['errores'] > 0 or stats_titulares['errores'] > 0:
                    print(f"\n⚠️ Errores encontrados: Notarías={stats_notarias['errores']}, Titulares={stats_titulares['errores']}")
                
                if stats_integridad['notarias_sin_titulares'] > 0:
                    print(f"\n⚠️ ADVERTENCIA: {stats_integridad['notarias_sin_titulares']} notarías sin titulares")
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error en la transacción: {e}", exc_info=True)
                raise
                
    except Exception as e:
        logger.error(f"Error en la carga: {e}", exc_info=True)
        return False
    finally:
        await db_manager.close()


def cargar_desde_csv():
    """Carga datos desde archivos CSV transformados"""
    print("=" * 80)
    print("CARGA DE NOTARÍAS Y TITULARES")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO CARGA DESDE CSV")
    logger.info("=" * 80)
    
    # Configurar rutas - buscar CSV en ../transform/
    script_dir = Path(__file__).parent
    transform_dir = script_dir.parent / 'transform'
    
    # Buscar archivos más recientes
    archivos_notarias = list(transform_dir.glob("notarias_transformado_*.csv"))
    archivos_titulares = list(transform_dir.glob("notarias_titulares_transformado_*.csv"))
    
    if not archivos_notarias or not archivos_titulares:
        print(f"ERROR: No se encuentran los archivos CSV en {transform_dir}")
        print("\nEjecuta primero transform_notarios.py desde la carpeta transform/")
        sys.exit(1)
    
    # Ordenar por fecha (más reciente primero)
    archivos_notarias.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    archivos_titulares.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    notarias_csv = archivos_notarias[0]
    titulares_csv = archivos_titulares[0]
    
    print(f"✓ Notarías: {notarias_csv.name}")
    print(f"✓ Titulares: {titulares_csv.name}")
    
    # Cargar DataFrames
    try:
        df_notarias = pd.read_csv(notarias_csv)
        df_titulares = pd.read_csv(titulares_csv)
        
        print(f"  - Notarías: {len(df_notarias)} registros")
        print(f"  - Titulares: {len(df_titulares)} registros")
        
        # Validar columnas requeridas
        if 'codigo_notaria' not in df_notarias.columns:
            print("ERROR: CSV de notarías no tiene columna 'codigo_notaria'")
            sys.exit(1)
        
        if 'notaria_id' not in df_titulares.columns:
            print("ERROR: CSV de titulares no tiene columna 'notaria_id'")
            sys.exit(1)
        
    except Exception as e:
        print(f"ERROR leyendo archivos CSV: {e}")
        sys.exit(1)
    
    # Ejecutar carga
    async def run_carga():
        return await cargar_datos(df_notarias, df_titulares)
    
    try:
        resultado = asyncio.run(run_carga())
    except KeyboardInterrupt:
        print("\nINTERRUMPIDO: Proceso cancelado por el usuario")
        sys.exit(1)
    
    if resultado:
        print("\n" + "=" * 80)
        print("CARGA COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        logger.info("CARGA COMPLETADA EXITOSAMENTE")
    else:
        print("\nERROR EN LA CARGA - Ver notarias_load.log para detalles")
        logger.error("ERROR EN LA CARGA")
        sys.exit(1)


if __name__ == '__main__':
    cargar_desde_csv()