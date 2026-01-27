#!/usr/bin/env python3
"""
load_geografia.py

Carga datos geográficos transformados a la base de datos.
Lee los CSV de ../transform/ y carga a la base de datos.
Genera log en load/geografia_load.log
"""

import sys
from pathlib import Path
from datetime import datetime
import asyncio
import uuid
from typing import Dict, Set, Tuple
import pandas as pd
from sqlalchemy import select, update, and_
import hashlib
import logging

# Importar desde sipi-core (asume que está instalado)
from sipi.db.sessions.async_session import db_manager
from sipi.db.models.geografia import ComunidadAutonoma, Provincia, Municipio


def setup_logging():
    """Configura logging específico para carga"""
    script_dir = Path(__file__).parent
    log_file = script_dir / 'geografia_load.log'
    
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


def safe_print(message):
    """Imprime mensajes de forma segura en Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)


def generar_hash_registro(*campos) -> str:
    """
    Genera hash MD5 para detectar cambios en registros.
    Campos deben ser strings.
    """
    contenido = '|'.join(str(campo) for campo in campos if campo is not None)
    return hashlib.md5(contenido.encode('utf-8')).hexdigest()


async def cargar_comunidades_autonomas(session, df_ccaa: pd.DataFrame) -> Tuple[Dict[str, str], Dict]:
    """
    Carga y sincroniza comunidades autónomas.
    Retorna: (mapeo codigo_ine->id, estadísticas)
    """
    logger.info("=== CARGA DE COMUNIDADES AUTÓNOMAS ===")
    total_csv = len(df_ccaa)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Obtener todos los registros actuales de BD
    result = await session.execute(select(ComunidadAutonoma))
    ccaa_bd = {str(ccaa.codigo_ine): ccaa for ccaa in result.scalars()}
    logger.info(f"Registros en BD: {len(ccaa_bd)}")
    
    # Preparar estadísticas
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'desactivadas': 0,
        'sin_cambios': 0,
        'errores': 0
    }
    
    ccaa_cache = {}  # codigo_ine -> id
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_ccaa.itertuples(), 1):
        codigo_ine = str(row.codigo_ine).strip()
        
        try:
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre,
                row.nombre_oficial,
                row.activo
            )
            
            if codigo_ine in ccaa_bd:
                # REGISTRO EXISTENTE: Verificar si necesita actualización
                existing = ccaa_bd[codigo_ine]
                hash_bd = generar_hash_registro(
                    existing.nombre,
                    existing.nombre_oficial,
                    existing.activo
                )
                
                if hash_csv != hash_bd:
                    # Hay cambios, actualizar
                    stmt = (
                        update(ComunidadAutonoma)
                        .where(ComunidadAutonoma.id == existing.id)
                        .values(
                            nombre=row.nombre,
                            nombre_oficial=row.nombre_oficial,
                            activo=row.activo,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await session.execute(stmt)
                    stats['actualizadas'] += 1
                    logger.debug(f"CCAA actualizada: {codigo_ine} - {row.nombre}")
                else:
                    # Sin cambios
                    stats['sin_cambios'] += 1
                
                ccaa_cache[codigo_ine] = str(existing.id)
                
            else:
                # NUEVO REGISTRO: Insertar
                new_id = str(uuid.uuid4())
                new_ccaa = ComunidadAutonoma(
                    id=new_id,
                    codigo_ine=codigo_ine,
                    nombre=row.nombre,
                    nombre_oficial=row.nombre_oficial,
                    activo=row.activo,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_ccaa)
                ccaa_cache[codigo_ine] = new_id
                stats['nuevas'] += 1
                logger.debug(f"CCAA nueva: {codigo_ine} - {row.nombre}")
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando CCAA {codigo_ine}: {e}")
        
        # Log progreso
        if idx % 5 == 0:
            logger.info(f"Procesadas {idx}/{total_csv} CCAA")
    
    # IDENTIFICAR REGISTROS ELIMINADOS (en BD pero no en CSV)
    codigos_csv = set(str(row.codigo_ine).strip() for row in df_ccaa.itertuples())
    codigos_solo_bd = set(ccaa_bd.keys()) - codigos_csv
    
    for codigo_ine in codigos_solo_bd:
        try:
            existing = ccaa_bd[codigo_ine]
            if existing.activo:  # Solo desactivar si está activo
                stmt = (
                    update(ComunidadAutonoma)
                    .where(ComunidadAutonoma.id == existing.id)
                    .values(activo=False, updated_at=datetime.utcnow())
                )
                await session.execute(stmt)
                stats['desactivadas'] += 1
                logger.info(f"CCAA desactivada (no en CSV): {codigo_ine} - {existing.nombre}")
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error desactivando CCAA {codigo_ine}: {e}")
    
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN CCAA:")
    logger.info(f"  Nuevas: {stats['nuevas']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Desactivadas: {stats['desactivadas']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Total en cache: {len(ccaa_cache)}")
    logger.info("=" * 50)
    
    return ccaa_cache, stats


async def cargar_provincias(session, df_provincias: pd.DataFrame, 
                           ccaa_cache: Dict[str, str]) -> Tuple[Dict[str, str], Dict]:
    """
    Carga y sincroniza provincias.
    Retorna: (mapeo codigo_ine->id, estadísticas)
    """
    logger.info("=== CARGA DE PROVINCIAS ===")
    total_csv = len(df_provincias)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Obtener todos los registros actuales de BD
    result = await session.execute(select(Provincia))
    prov_bd = {str(prov.codigo_ine): prov for prov in result.scalars()}
    logger.info(f"Registros en BD: {len(prov_bd)}")
    
    # Preparar estadísticas
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'desactivadas': 0,
        'sin_cambios': 0,
        'errores': 0,
        'referencias_invalidas': 0
    }
    
    prov_cache = {}  # codigo_ine -> id
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_provincias.itertuples(), 1):
        codigo_ine = str(row.codigo_ine).strip()
        codigo_ccaa = str(row.comunidad_autonoma_codigo).strip()
        
        # Validar referencia a CCAA
        if codigo_ccaa not in ccaa_cache:
            stats['referencias_invalidas'] += 1
            logger.warning(f"CCAA {codigo_ccaa} no encontrada para provincia {codigo_ine}")
            continue
        
        ccaa_id = ccaa_cache[codigo_ccaa]
        
        try:
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre,
                row.nombre_oficial,
                row.activo,
                ccaa_id
            )
            
            if codigo_ine in prov_bd:
                # REGISTRO EXISTENTE
                existing = prov_bd[codigo_ine]
                hash_bd = generar_hash_registro(
                    existing.nombre,
                    existing.nombre_oficial,
                    existing.activo,
                    str(existing.comunidad_autonoma_id)
                )
                
                if hash_csv != hash_bd:
                    # Hay cambios, actualizar
                    stmt = (
                        update(Provincia)
                        .where(Provincia.id == existing.id)
                        .values(
                            nombre=row.nombre,
                            nombre_oficial=row.nombre_oficial,
                            comunidad_autonoma_id=ccaa_id,
                            activo=row.activo,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await session.execute(stmt)
                    stats['actualizadas'] += 1
                    logger.debug(f"Provincia actualizada: {codigo_ine} - {row.nombre}")
                else:
                    # Sin cambios
                    stats['sin_cambios'] += 1
                
                prov_cache[codigo_ine] = str(existing.id)
                
            else:
                # NUEVO REGISTRO
                new_id = str(uuid.uuid4())
                new_prov = Provincia(
                    id=new_id,
                    codigo_ine=codigo_ine,
                    nombre=row.nombre,
                    nombre_oficial=row.nombre_oficial,
                    comunidad_autonoma_id=ccaa_id,
                    activo=row.activo,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_prov)
                prov_cache[codigo_ine] = new_id
                stats['nuevas'] += 1
                logger.debug(f"Provincia nueva: {codigo_ine} - {row.nombre}")
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando provincia {codigo_ine}: {e}")
        
        # Log progreso
        if idx % 10 == 0:
            logger.info(f"Procesadas {idx}/{total_csv} provincias")
    
    # IDENTIFICAR REGISTROS ELIMINADOS
    codigos_csv = set(str(row.codigo_ine).strip() for row in df_provincias.itertuples())
    codigos_solo_bd = set(prov_bd.keys()) - codigos_csv
    
    for codigo_ine in codigos_solo_bd:
        try:
            existing = prov_bd[codigo_ine]
            if existing.activo:  # Solo desactivar si está activo
                stmt = (
                    update(Provincia)
                    .where(Provincia.id == existing.id)
                    .values(activo=False, updated_at=datetime.utcnow())
                )
                await session.execute(stmt)
                stats['desactivadas'] += 1
                logger.info(f"Provincia desactivada (no en CSV): {codigo_ine} - {existing.nombre}")
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error desactivando provincia {codigo_ine}: {e}")
    
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN PROVINCIAS:")
    logger.info(f"  Nuevas: {stats['nuevas']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Desactivadas: {stats['desactivadas']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Referencias inválidas: {stats['referencias_invalidas']}")
    logger.info(f"  Total en cache: {len(prov_cache)}")
    logger.info("=" * 50)
    
    return prov_cache, stats


async def cargar_municipios(session, df_municipios: pd.DataFrame, 
                           prov_cache: Dict[str, str],
                           ccaa_cache: Dict[str, str]) -> Dict:
    """
    Carga y sincroniza municipios.
    Retorna: estadísticas
    """
    logger.info("=== CARGA DE MUNICIPIOS ===")
    total_csv = len(df_municipios)
    logger.info(f"Registros en CSV: {total_csv:,}")
    
    # Obtener todos los códigos INE de municipios en BD
    result = await session.execute(
        select(Municipio.codigo_ine, Municipio.id, Municipio.activo)
    )
    muni_bd = {str(row[0]): {'id': row[1], 'activo': row[2]} for row in result.all()}
    logger.info(f"Registros en BD: {len(muni_bd):,}")
    
    # Preparar estadísticas
    stats = {
        'nuevos': 0,
        'actualizados': 0,
        'desactivados': 0,
        'sin_cambios': 0,
        'errores': 0,
        'referencias_invalidas': 0
    }
    
    batch_size = 500
    processed = 0
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_municipios.itertuples(), 1):
        codigo_ine = str(row.codigo_ine).strip()
        codigo_prov = str(row.provincia_codigo).strip()
        
        # Validar referencia a provincia
        if codigo_prov not in prov_cache:
            stats['referencias_invalidas'] += 1
            if stats['referencias_invalidas'] <= 5:  # Log solo primeros 5
                logger.warning(f"Provincia {codigo_prov} no encontrada para municipio {codigo_ine}")
            continue
        
        provincia_id = prov_cache[codigo_prov]
        
        # Obtener CCAA ID desde la provincia
        try:
            result = await session.execute(
                select(Provincia.comunidad_autonoma_id).where(Provincia.id == provincia_id)
            )
            comunidad_autonoma_id = result.scalar_one()
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error obteniendo CCAA para provincia {codigo_prov}: {e}")
            continue
        
        try:
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre,
                row.nombre_oficial,
                row.activo,
                provincia_id,
                str(comunidad_autonoma_id)
            )
            
            if codigo_ine in muni_bd:
                # REGISTRO EXISTENTE: Obtener datos completos
                result = await session.execute(
                    select(Municipio).where(Municipio.codigo_ine == codigo_ine)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    hash_bd = generar_hash_registro(
                        existing.nombre,
                        existing.nombre_oficial,
                        existing.activo,
                        str(existing.provincia_id),
                        str(existing.comunidad_autonoma_id)
                    )
                    
                    if hash_csv != hash_bd:
                        # Hay cambios, actualizar
                        stmt = (
                            update(Municipio)
                            .where(Municipio.id == existing.id)
                            .values(
                                nombre=row.nombre,
                                nombre_oficial=row.nombre_oficial,
                                provincia_id=provincia_id,
                                comunidad_autonoma_id=comunidad_autonoma_id,
                                activo=row.activo,
                                updated_at=datetime.utcnow()
                            )
                        )
                        await session.execute(stmt)
                        stats['actualizados'] += 1
                    else:
                        # Sin cambios
                        stats['sin_cambios'] += 1
                        
                    # Si estaba desactivado y ahora está activo en CSV
                    if not existing.activo and row.activo:
                        stmt = (
                            update(Municipio)
                            .where(Municipio.id == existing.id)
                            .values(activo=True, updated_at=datetime.utcnow())
                        )
                        await session.execute(stmt)
                        
                else:
                    # Registro en cache pero no encontrado (raro)
                    stats['errores'] += 1
                    
            else:
                # NUEVO REGISTRO
                new_muni = Municipio(
                    id=str(uuid.uuid4()),
                    codigo_ine=codigo_ine,
                    nombre=row.nombre,
                    nombre_oficial=row.nombre_oficial,
                    provincia_id=provincia_id,
                    comunidad_autonoma_id=comunidad_autonoma_id,
                    activo=row.activo,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_muni)
                stats['nuevos'] += 1
                
            processed += 1
                
        except Exception as e:
            stats['errores'] += 1
            if stats['errores'] <= 10:  # Log solo primeros 10 errores
                logger.error(f"Error procesando municipio {codigo_ine}: {e}")
        
        # Commit y log progreso por lotes
        if idx % batch_size == 0:
            await session.commit()
            porcentaje = (idx / total_csv) * 100
            logger.info(f"Procesados {idx:,}/{total_csv:,} ({porcentaje:.1f}%)")
            logger.info(f"  - Nuevos: {stats['nuevos']:,}, Actualizados: {stats['actualizados']:,}")
    
    # Commit final
    await session.commit()
    
    # IDENTIFICAR REGISTROS ELIMINADOS (lote para eficiencia)
    if muni_bd:
        codigos_csv = set(str(row.codigo_ine).strip() for row in df_municipios.itertuples())
        codigos_solo_bd = set(muni_bd.keys()) - codigos_csv
        
        if codigos_solo_bd:
            logger.info(f"Desactivando {len(codigos_solo_bd):,} municipios no presentes en CSV...")
            
            # Desactivar en lotes
            codigos_lista = list(codigos_solo_bd)
            for i in range(0, len(codigos_lista), 1000):
                batch = codigos_lista[i:i + 1000]
                stmt = (
                    update(Municipio)
                    .where(
                        and_(
                            Municipio.codigo_ine.in_(batch),
                            Municipio.activo == True
                        )
                    )
                    .values(activo=False, updated_at=datetime.utcnow())
                )
                result = await session.execute(stmt)
                stats['desactivados'] += result.rowcount
                
                if i % 5000 == 0:
                    logger.info(f"  Desactivados {i:,}/{len(codigos_lista):,}")
            
            await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN MUNICIPIOS:")
    logger.info(f"  Nuevos: {stats['nuevos']:,}")
    logger.info(f"  Actualizados: {stats['actualizados']:,}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']:,}")
    logger.info(f"  Desactivados: {stats['desactivados']:,}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Referencias inválidas: {stats['referencias_invalidas']}")
    logger.info(f"  Total procesados: {processed:,}")
    logger.info("=" * 50)
    
    return stats


async def verificar_integridad_referencial(session, ccaa_cache: Dict[str, str], 
                                          prov_cache: Dict[str, str]) -> Dict:
    """
    Verifica la integridad referencial después de la carga.
    """
    logger.info("=== VERIFICACIÓN DE INTEGRIDAD REFERENCIAL ===")
    
    stats = {
        'ccaa_sin_provincias': 0,
        'provincias_sin_municipios': 0,
        'municipios_huérfanos': 0
    }
    
    # 1. Verificar CCAA sin provincias
    for codigo_ccaa, ccaa_id in ccaa_cache.items():
        result = await session.execute(
            select(Provincia).where(Provincia.comunidad_autonoma_id == ccaa_id)
        )
        provincias = result.scalars().all()
        
        if not provincias:
            stats['ccaa_sin_provincias'] += 1
            logger.warning(f"CCAA {codigo_ccaa} no tiene provincias asignadas")
    
    # 2. Verificar provincias sin municipios
    for codigo_prov, prov_id in prov_cache.items():
        result = await session.execute(
            select(Municipio).where(Municipio.provincia_id == prov_id)
        )
        municipios = result.scalars().all()
        
        if not municipios:
            stats['provincias_sin_municipios'] += 1
            logger.warning(f"Provincia {codigo_prov} no tiene municipios")
    
    # 3. Verificar municipios huérfanos (sin provincia válida)
    result = await session.execute(
        select(Municipio).where(Municipio.provincia_id.not_in(list(prov_cache.values())))
    )
    municipios_huérfanos = result.scalars().all()
    stats['municipios_huérfanos'] = len(municipios_huérfanos)
    
    if municipios_huérfanos:
        logger.warning(f"Encontrados {len(municipios_huérfanos)} municipios huérfanos")
        for muni in municipios_huérfanos[:10]:  # Mostrar solo primeros 10
            logger.warning(f"  - {muni.codigo_ine}: {muni.nombre}")
        if len(municipios_huérfanos) > 10:
            logger.warning(f"  ... y {len(municipios_huérfanos) - 10} más")
    
    logger.info("=" * 50)
    logger.info("RESUMEN INTEGRIDAD REFERENCIAL:")
    logger.info(f"  CCAA sin provincias: {stats['ccaa_sin_provincias']}")
    logger.info(f"  Provincias sin municipios: {stats['provincias_sin_municipios']}")
    logger.info(f"  Municipios huérfanos: {stats['municipios_huérfanos']}")
    logger.info("=" * 50)
    
    return stats


async def verificar_conteos_finales(session):
    """Verificar conteos finales en la base de datos"""
    logger.info("=== VERIFICACIÓN DE CONTEO FINAL ===")
    
    # Contar activos vs totales
    result = await session.execute(
        select(ComunidadAutonoma)
    )
    todas_ccaa = result.scalars().all()
    
    result = await session.execute(
        select(ComunidadAutonoma).where(ComunidadAutonoma.activo == True)
    )
    activas_ccaa = result.scalars().all()
    
    result = await session.execute(
        select(Provincia)
    )
    todas_prov = result.scalars().all()
    
    result = await session.execute(
        select(Provincia).where(Provincia.activo == True)
    )
    activas_prov = result.scalars().all()
    
    result = await session.execute(
        select(Municipio)
    )
    todos_muni = result.scalars().all()
    
    result = await session.execute(
        select(Municipio).where(Municipio.activo == True)
    )
    activos_muni = result.scalars().all()
    
    safe_print(f"\n" + "=" * 80)
    safe_print("RESUMEN FINAL EN BASE DE DATOS:")
    safe_print("=" * 80)
    safe_print("COMUNIDADES AUTÓNOMAS:")
    safe_print(f"  Total: {len(todas_ccaa)} (Activas: {len(activas_ccaa)}, Inactivas: {len(todas_ccaa) - len(activas_ccaa)})")
    safe_print("\nPROVINCIAS:")
    safe_print(f"  Total: {len(todas_prov)} (Activas: {len(activas_prov)}, Inactivas: {len(todas_prov) - len(activas_prov)})")
    safe_print("\nMUNICIPIOS:")
    safe_print(f"  Total: {len(todos_muni):,} (Activos: {len(activos_muni):,}, Inactivos: {len(todos_muni) - len(activos_muni):,})")
    safe_print("=" * 80)
    
    logger.info("RESUMEN FINAL EN BASE DE DATOS:")
    logger.info(f"CCAA: Total={len(todas_ccaa)}, Activas={len(activas_ccaa)}")
    logger.info(f"Provincias: Total={len(todas_prov)}, Activas={len(activas_prov)}")
    logger.info(f"Municipios: Total={len(todos_muni):,}, Activos={len(activos_muni):,}")


async def cargar_datos(df_ccaa: pd.DataFrame, df_provincias: pd.DataFrame, 
                      df_municipios: pd.DataFrame):
    """Ejecuta la carga de datos geográficos"""
    safe_print("\n" + "=" * 80)
    safe_print("CARGA DE DATOS GEOGRÁFICOS")
    safe_print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO CARGA DE DATOS GEOGRÁFICOS")
    logger.info("=" * 80)
    logger.info(f"Datos a cargar:")
    logger.info(f"  - CCAA: {len(df_ccaa)} registros")
    logger.info(f"  - Provincias: {len(df_provincias)} registros")
    logger.info(f"  - Municipios: {len(df_municipios):,} registros")
    
    try:
        async with db_manager.session() as session:
            # Iniciar transacción global
            await session.begin()
            
            try:
                # 1. Cargar Comunidades Autónomas
                ccaa_cache, stats_ccaa = await cargar_comunidades_autonomas(session, df_ccaa)
                
                # 2. Cargar Provincias
                prov_cache, stats_prov = await cargar_provincias(session, df_provincias, ccaa_cache)
                
                # 3. Cargar Municipios
                stats_muni = await cargar_municipios(session, df_municipios, prov_cache, ccaa_cache)
                
                # 4. Verificar integridad referencial
                stats_integridad = await verificar_integridad_referencial(session, ccaa_cache, prov_cache)
                
                # 5. Commit transacción global
                await session.commit()
                
                # 6. Verificar conteos finales
                await verificar_conteos_finales(session)
                
                # 7. Reporte consolidado
                logger.info("=" * 80)
                logger.info("CARGA COMPLETADA EXITOSAMENTE")
                logger.info("=" * 80)
                
                safe_print("\n" + "=" * 80)
                safe_print("CARGA COMPLETADA EXITOSAMENTE")
                safe_print("=" * 80)
                
                # Reporte detallado en pantalla
                safe_print("\nRESUMEN DE CAMBIOS:")
                safe_print(f"CCAA: +{stats_ccaa['nuevas']} nuevas, ↑{stats_ccaa['actualizadas']} actualizadas, ↓{stats_ccaa['desactivadas']} desactivadas")
                safe_print(f"Provincias: +{stats_prov['nuevas']} nuevas, ↑{stats_prov['actualizadas']} actualizadas, ↓{stats_prov['desactivadas']} desactivadas")
                safe_print(f"Municipios: +{stats_muni['nuevos']:,} nuevos, ↑{stats_muni['actualizados']:,} actualizados, ↓{stats_muni['desactivados']:,} desactivados")
                
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
    """Carga datos desde archivos CSV"""
    safe_print("=" * 80)
    safe_print("CARGA DE GEOGRAFÍA DE ESPAÑA")
    safe_print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO CARGA DESDE CSV")
    logger.info("=" * 80)
    
    # Configurar rutas - buscar CSV en ../transform/
    script_dir = Path(__file__).parent
    transform_dir = script_dir.parent / 'transform'
    
    logger.info(f"Script ejecutado desde: {script_dir}")
    logger.info(f"Buscando archivos CSV en: {transform_dir}")
    
    # Cargar DataFrames desde CSV
    archivos_csv = []
    try:
        df_ccaa = pd.read_csv(transform_dir / 'comunidades_autonomas.csv')
        archivos_csv.append(('comunidades_autonomas.csv', len(df_ccaa)))
        safe_print(f"✓ Comunidades Autónomas: {len(df_ccaa)} registros")
        logger.info(f"Archivo cargado: comunidades_autonomas.csv - {len(df_ccaa)} registros")
        
        df_provincias = pd.read_csv(transform_dir / 'provincias.csv')
        archivos_csv.append(('provincias.csv', len(df_provincias)))
        safe_print(f"✓ Provincias: {len(df_provincias)} registros")
        logger.info(f"Archivo cargado: provincias.csv - {len(df_provincias)} registros")
        
        df_municipios = pd.read_csv(transform_dir / 'municipios.csv')
        archivos_csv.append(('municipios.csv', len(df_municipios)))
        safe_print(f"✓ Municipios: {len(df_municipios):,} registros")
        logger.info(f"Archivo cargado: municipios.csv - {len(df_municipios):,} registros")
        
        # Validar que exista columna codigo_ine
        for nombre, df in [('CCAA', df_ccaa), ('Provincias', df_provincias), ('Municipios', df_municipios)]:
            if 'codigo_ine' not in df.columns:
                logger.error(f"Archivo de {nombre} no tiene columna 'codigo_ine'")
                safe_print(f"ERROR: Archivo de {nombre} no tiene columna 'codigo_ine'")
                sys.exit(1)
        
        # Registrar archivos cargados en log
        logger.info("=" * 50)
        logger.info("ARCHIVOS CSV CARGADOS")
        logger.info("=" * 50)
        for archivo, registros in archivos_csv:
            logger.info(f"{archivo}: {registros:,} registros")
        logger.info(f"Total registros a procesar: {len(df_ccaa) + len(df_provincias) + len(df_municipios):,}")
        logger.info("=" * 50)
        
    except FileNotFoundError as e:
        safe_print(f"ERROR: No se encuentran los archivos CSV en {transform_dir}")
        logger.error(f"No se encuentran los archivos CSV en {transform_dir}")
        logger.error("Archivos requeridos:")
        logger.error("  - comunidades_autonomas.csv")
        logger.error("  - provincias.csv")
        logger.error("  - municipios.csv")
        logger.error("\nEjecuta primero transform_geografia.py desde la carpeta transform/")
        sys.exit(1)
    
    # Ejecutar carga
    async def run_carga():
        return await cargar_datos(df_ccaa, df_provincias, df_municipios)
    
    try:
        resultado = asyncio.run(run_carga())
    except KeyboardInterrupt:
        safe_print("\nINTERRUMPIDO: Proceso cancelado por el usuario")
        logger.warning("Proceso interrumpido por el usuario")
        sys.exit(1)
    
    if resultado:
        safe_print("\n" + "=" * 80)
        safe_print("CARGA COMPLETADA EXITOSAMENTE")
        safe_print("=" * 80)
        logger.info("CARGA COMPLETADA EXITOSAMENTE")
    else:
        safe_print("\nERROR EN LA CARGA")
        logger.error("ERROR EN LA CARGA")
        sys.exit(1)


if __name__ == '__main__':
    cargar_desde_csv()