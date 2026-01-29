#!/usr/bin/env python3
"""
load_geografia.py - Versión adaptada a los modelos SQLAlchemy actualizados

Carga datos geográficos transformados a la base de datos.
Lee los CSV de ../transform/ y carga a la base de datos.
Genera log en load/geografia_load.log
"""

import sys
from pathlib import Path
from datetime import datetime
import asyncio
import uuid
from typing import Dict, Set, Tuple, Optional
import pandas as pd
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import logging

# Importar desde sipi-core
from sipi_core.db.sessions.async_session import db_manager
from sipi_core.db.models.geografia import ComunidadAutonoma, Provincia, Municipio


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
    Campos deben ser strings o convertibles a string.
    """
    contenido = '|'.join(
        str(campo) if campo is not None else 'NULL' 
        for campo in campos
    )
    return hashlib.md5(contenido.encode('utf-8')).hexdigest()


def convertir_estado_activo(activo_csv: bool) -> Tuple[bool, Optional[datetime]]:
    """
    Convierte estado 'activo' del CSV a 'deleted' del modelo.
    
    CSV: activo=True -> activo
    CSV: activo=False -> inactivo
    
    Modelo: deleted=False -> no eliminado (activo)
    Modelo: deleted=True -> eliminado (inactivo)
    
    Lógica: deleted = not activo
    """
    deleted = not activo_csv
    deleted_at = datetime.utcnow() if deleted else None
    return deleted, deleted_at


async def obtener_mapeo_codigo_a_id(
    session: AsyncSession, 
    modelo
) -> Dict[str, str]:
    """
    Obtiene mapeo de código INE -> ID UUID para un modelo.
    """
    result = await session.execute(
        select(modelo.codigo_ine, modelo.id)
    )
    return {str(row[0]): str(row[1]) for row in result.all()}


async def cargar_comunidades_autonomas(
    session: AsyncSession, 
    df_ccaa: pd.DataFrame
) -> Tuple[Dict[str, str], Dict]:
    """
    Carga y sincroniza comunidades autónomas.
    
    CSV -> Modelo:
    - codigo_ine: igual
    - nombre_oficial: igual
    - nombre_alternativo: igual
    - nombre_cooficial: igual
    - activo -> deleted (lógica invertida)
    """
    logger.info("=== CARGA DE COMUNIDADES AUTÓNOMAS ===")
    total_csv = len(df_ccaa)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Obtener mapeo actual de código INE -> ID
    ccaa_mapeo = await obtener_mapeo_codigo_a_id(session, ComunidadAutonoma)
    logger.info(f"Registros en BD: {len(ccaa_mapeo)}")
    
    # Preparar estadísticas
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'eliminadas': 0,
        'reactivadas': 0,
        'sin_cambios': 0,
        'errores': 0
    }
    
    # Cache para IDs generados/obtenidos
    ccaa_cache = {}  # codigo_ine -> id
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_ccaa.itertuples(), 1):
        codigo_ine = str(row.codigo_ine).strip()
        
        try:
            # Convertir estado activo -> deleted
            deleted, deleted_at = convertir_estado_activo(row.activo)
            
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre_oficial,
                row.nombre_alternativo if hasattr(row, 'nombre_alternativo') else '',
                row.nombre_cooficial if hasattr(row, 'nombre_cooficial') else '',
                deleted,
                str(deleted_at) if deleted_at else 'NULL'
            )
            
            if codigo_ine in ccaa_mapeo:
                # REGISTRO EXISTENTE: Verificar si necesita actualización
                ccaa_id = ccaa_mapeo[codigo_ine]
                
                # Obtener registro completo de BD
                result = await session.execute(
                    select(ComunidadAutonoma).where(ComunidadAutonoma.id == ccaa_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Generar hash de BD
                    hash_bd = generar_hash_registro(
                        existing.nombre_oficial,
                        existing.nombre_alternativo or '',
                        existing.nombre_cooficial or '',
                        existing.deleted,
                        str(existing.deleted_at) if existing.deleted_at else 'NULL'
                    )
                    
                    if hash_csv != hash_bd:
                        # Hay cambios, actualizar
                        stmt = (
                            update(ComunidadAutonoma)
                            .where(ComunidadAutonoma.id == ccaa_id)
                            .values(
                                nombre_oficial=row.nombre_oficial,
                                nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                                nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                                deleted=deleted,
                                deleted_at=deleted_at,
                                updated_at=datetime.utcnow()
                            )
                        )
                        await session.execute(stmt)
                        
                        # Contabilizar tipo de cambio
                        if existing.deleted and not deleted:
                            stats['reactivadas'] += 1
                            logger.debug(f"CCAA reactivada: {codigo_ine} - {row.nombre_oficial}")
                        elif not existing.deleted and deleted:
                            stats['eliminadas'] += 1
                            logger.debug(f"CCAA eliminada: {codigo_ine} - {row.nombre_oficial}")
                        else:
                            stats['actualizadas'] += 1
                            logger.debug(f"CCAA actualizada: {codigo_ine} - {row.nombre_oficial}")
                    else:
                        # Sin cambios
                        stats['sin_cambios'] += 1
                    
                    ccaa_cache[codigo_ine] = ccaa_id
                    
                else:
                    # Registro en mapeo pero no encontrado (raro)
                    stats['errores'] += 1
                    logger.warning(f"CCAA en mapeo pero no encontrada en BD: {codigo_ine}")
                    
            else:
                # NUEVO REGISTRO: Insertar
                new_ccaa = ComunidadAutonoma(
                    id=str(uuid.uuid4()),
                    codigo_ine=codigo_ine,
                    nombre_oficial=row.nombre_oficial,
                    nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                    nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                    deleted=deleted,
                    deleted_at=deleted_at,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_ccaa)
                ccaa_cache[codigo_ine] = new_ccaa.id
                stats['nuevas'] += 1
                logger.debug(f"CCAA nueva: {codigo_ine} - {row.nombre_oficial}")
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando CCAA {codigo_ine}: {e}", exc_info=True)
        
        # Log progreso
        if idx % 5 == 0 or idx == total_csv:
            logger.info(f"Procesadas {idx}/{total_csv} CCAA")
    
    # Commit cambios
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN CCAA:")
    logger.info(f"  Nuevas: {stats['nuevas']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Reactivadas: {stats['reactivadas']}")
    logger.info(f"  Eliminadas (soft-delete): {stats['eliminadas']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Total en cache: {len(ccaa_cache)}")
    logger.info("=" * 50)
    
    return ccaa_cache, stats


async def cargar_provincias(
    session: AsyncSession, 
    df_provincias: pd.DataFrame, 
    ccaa_cache: Dict[str, str]
) -> Tuple[Dict[str, str], Dict]:
    """
    Carga y sincroniza provincias.
    
    CSV -> Modelo:
    - codigo_ine: igual
    - nombre_oficial: igual
    - nombre_alternativo: igual
    - nombre_cooficial: igual
    - comunidad_autonoma_codigo -> comunidad_autonoma_id (código INE -> UUID)
    - activo -> deleted (lógica invertida)
    """
    logger.info("=== CARGA DE PROVINCIAS ===")
    total_csv = len(df_provincias)
    logger.info(f"Registros en CSV: {total_csv}")
    
    # Obtener mapeo actual de código INE -> ID
    prov_mapeo = await obtener_mapeo_codigo_a_id(session, Provincia)
    logger.info(f"Registros en BD: {len(prov_mapeo)}")
    
    # Preparar estadísticas
    stats = {
        'nuevas': 0,
        'actualizadas': 0,
        'eliminadas': 0,
        'reactivadas': 0,
        'sin_cambios': 0,
        'errores': 0,
        'referencias_invalidas': 0
    }
    
    # Cache para IDs
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
            # Convertir estado activo -> deleted
            deleted, deleted_at = convertir_estado_activo(row.activo)
            
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre_oficial,
                row.nombre_alternativo if hasattr(row, 'nombre_alternativo') else '',
                row.nombre_cooficial if hasattr(row, 'nombre_cooficial') else '',
                ccaa_id,
                deleted,
                str(deleted_at) if deleted_at else 'NULL'
            )
            
            if codigo_ine in prov_mapeo:
                # REGISTRO EXISTENTE
                prov_id = prov_mapeo[codigo_ine]
                
                # Obtener registro completo
                result = await session.execute(
                    select(Provincia).where(Provincia.id == prov_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Generar hash de BD
                    hash_bd = generar_hash_registro(
                        existing.nombre_oficial,
                        existing.nombre_alternativo or '',
                        existing.nombre_cooficial or '',
                        existing.comunidad_autonoma_id,
                        existing.deleted,
                        str(existing.deleted_at) if existing.deleted_at else 'NULL'
                    )
                    
                    if hash_csv != hash_bd:
                        # Hay cambios, actualizar
                        stmt = (
                            update(Provincia)
                            .where(Provincia.id == prov_id)
                            .values(
                                nombre_oficial=row.nombre_oficial,
                                nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                                nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                                comunidad_autonoma_id=ccaa_id,
                                deleted=deleted,
                                deleted_at=deleted_at,
                                updated_at=datetime.utcnow()
                            )
                        )
                        await session.execute(stmt)
                        
                        # Contabilizar tipo de cambio
                        if existing.deleted and not deleted:
                            stats['reactivadas'] += 1
                            logger.debug(f"Provincia reactivada: {codigo_ine} - {row.nombre_oficial}")
                        elif not existing.deleted and deleted:
                            stats['eliminadas'] += 1
                            logger.debug(f"Provincia eliminada: {codigo_ine} - {row.nombre_oficial}")
                        else:
                            stats['actualizadas'] += 1
                            logger.debug(f"Provincia actualizada: {codigo_ine} - {row.nombre_oficial}")
                    else:
                        # Sin cambios
                        stats['sin_cambios'] += 1
                    
                    prov_cache[codigo_ine] = prov_id
                    
                else:
                    stats['errores'] += 1
                    logger.warning(f"Provincia en mapeo pero no encontrada en BD: {codigo_ine}")
                    
            else:
                # NUEVO REGISTRO
                new_prov = Provincia(
                    id=str(uuid.uuid4()),
                    codigo_ine=codigo_ine,
                    nombre_oficial=row.nombre_oficial,
                    nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                    nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                    comunidad_autonoma_id=ccaa_id,
                    deleted=deleted,
                    deleted_at=deleted_at,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_prov)
                prov_cache[codigo_ine] = new_prov.id
                stats['nuevas'] += 1
                logger.debug(f"Provincia nueva: {codigo_ine} - {row.nombre_oficial}")
                
        except Exception as e:
            stats['errores'] += 1
            logger.error(f"Error procesando provincia {codigo_ine}: {e}", exc_info=True)
        
        # Log progreso
        if idx % 10 == 0 or idx == total_csv:
            logger.info(f"Procesadas {idx}/{total_csv} provincias")
    
    # Commit cambios
    await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN PROVINCIAS:")
    logger.info(f"  Nuevas: {stats['nuevas']}")
    logger.info(f"  Actualizadas: {stats['actualizadas']}")
    logger.info(f"  Reactivadas: {stats['reactivadas']}")
    logger.info(f"  Eliminadas (soft-delete): {stats['eliminadas']}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Referencias inválidas: {stats['referencias_invalidas']}")
    logger.info(f"  Total en cache: {len(prov_cache)}")
    logger.info("=" * 50)
    
    return prov_cache, stats


async def cargar_municipios(
    session: AsyncSession, 
    df_municipios: pd.DataFrame, 
    prov_cache: Dict[str, str]
) -> Dict:
    """
    Carga y sincroniza municipios.
    
    CSV -> Modelo:
    - codigo_ine: primeros 5 dígitos del código INE
    - codigo_ine_7: código completo de 7 dígitos (opcional)
    - nombre_oficial: igual
    - nombre_alternativo: igual
    - nombre_cooficial: igual
    - provincia_codigo -> provincia_id (código INE -> UUID)
    - activo -> deleted (lógica invertida)
    """
    logger.info("=== CARGA DE MUNICIPIOS ===")
    total_csv = len(df_municipios)
    logger.info(f"Registros en CSV: {total_csv:,}")
    
    # Obtener mapeo actual de código INE -> ID
    result = await session.execute(
        select(Municipio.codigo_ine, Municipio.id, Municipio.deleted)
    )
    muni_mapeo = {str(row[0]): {'id': row[1], 'deleted': row[2]} for row in result.all()}
    logger.info(f"Registros en BD: {len(muni_mapeo):,}")
    
    # Preparar estadísticas
    stats = {
        'nuevos': 0,
        'actualizados': 0,
        'eliminados': 0,
        'reactivados': 0,
        'sin_cambios': 0,
        'errores': 0,
        'referencias_invalidas': 0
    }
    
    batch_size = 500
    processed = 0
    
    # Procesar cada registro del CSV
    for idx, row in enumerate(df_municipios.itertuples(), 1):
        codigo_ine = str(row.codigo_ine).strip()  # Ya son 5 dígitos del transform
        codigo_prov = str(row.provincia_codigo).strip()
        
        # Validar referencia a provincia
        if codigo_prov not in prov_cache:
            stats['referencias_invalidas'] += 1
            if stats['referencias_invalidas'] <= 5:
                logger.warning(f"Provincia {codigo_prov} no encontrada para municipio {codigo_ine}")
            continue
        
        provincia_id = prov_cache[codigo_prov]
        
        try:
            # Convertir estado activo -> deleted
            deleted, deleted_at = convertir_estado_activo(row.activo)
            
            # Obtener código INE completo de 7 dígitos si existe
            codigo_ine_7 = None
            if hasattr(row, 'codigo_ine_completo'):
                codigo_ine_7 = str(row.codigo_ine_completo).strip()
                if len(codigo_ine_7) != 7:
                    codigo_ine_7 = None  # No es válido
            
            # Generar hash del registro CSV
            hash_csv = generar_hash_registro(
                row.nombre_oficial,
                row.nombre_alternativo if hasattr(row, 'nombre_alternativo') else '',
                row.nombre_cooficial if hasattr(row, 'nombre_cooficial') else '',
                provincia_id,
                deleted,
                str(deleted_at) if deleted_at else 'NULL',
                codigo_ine_7 or ''
            )
            
            if codigo_ine in muni_mapeo:
                # REGISTRO EXISTENTE
                muni_id = muni_mapeo[codigo_ine]['id']
                
                # Obtener registro completo
                result = await session.execute(
                    select(Municipio).where(Municipio.id == muni_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Generar hash de BD
                    hash_bd = generar_hash_registro(
                        existing.nombre_oficial,
                        existing.nombre_alternativo or '',
                        existing.nombre_cooficial or '',
                        existing.provincia_id,
                        existing.deleted,
                        str(existing.deleted_at) if existing.deleted_at else 'NULL',
                        existing.codigo_ine_7 or ''
                    )
                    
                    if hash_csv != hash_bd:
                        # Hay cambios, actualizar
                        stmt = (
                            update(Municipio)
                            .where(Municipio.id == muni_id)
                            .values(
                                nombre_oficial=row.nombre_oficial,
                                nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                                nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                                codigo_ine_7=codigo_ine_7,
                                provincia_id=provincia_id,
                                deleted=deleted,
                                deleted_at=deleted_at,
                                updated_at=datetime.utcnow()
                            )
                        )
                        await session.execute(stmt)
                        
                        # Contabilizar tipo de cambio
                        if existing.deleted and not deleted:
                            stats['reactivados'] += 1
                        elif not existing.deleted and deleted:
                            stats['eliminados'] += 1
                        else:
                            stats['actualizados'] += 1
                    else:
                        # Sin cambios
                        stats['sin_cambios'] += 1
                        
                else:
                    stats['errores'] += 1
                    
            else:
                # NUEVO REGISTRO
                new_muni = Municipio(
                    id=str(uuid.uuid4()),
                    codigo_ine=codigo_ine,
                    codigo_ine_7=codigo_ine_7,
                    nombre_oficial=row.nombre_oficial,
                    nombre_alternativo=getattr(row, 'nombre_alternativo', None),
                    nombre_cooficial=getattr(row, 'nombre_cooficial', None),
                    provincia_id=provincia_id,
                    deleted=deleted,
                    deleted_at=deleted_at,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_muni)
                stats['nuevos'] += 1
                
            processed += 1
                
        except Exception as e:
            stats['errores'] += 1
            if stats['errores'] <= 10:
                logger.error(f"Error procesando municipio {codigo_ine}: {e}", exc_info=True)
        
        # Commit y log progreso por lotes
        if idx % batch_size == 0:
            await session.commit()
            porcentaje = (idx / total_csv) * 100
            logger.info(f"Procesados {idx:,}/{total_csv:,} ({porcentaje:.1f}%)")
            logger.info(f"  - Nuevos: {stats['nuevos']:,}, Actualizados: {stats['actualizados']:,}, Eliminados: {stats['eliminados']:,}")
    
    # Commit final
    await session.commit()
    
    # IDENTIFICAR REGISTROS ELIMINADOS (en BD pero no en CSV)
    if muni_mapeo:
        codigos_csv = set(str(row.codigo_ine).strip() for row in df_municipios.itertuples())
        codigos_solo_bd = set(muni_mapeo.keys()) - codigos_csv
        
        if codigos_solo_bd:
            logger.info(f"Marcando como eliminados {len(codigos_solo_bd):,} municipios no presentes en CSV...")
            
            # Marcar como eliminados en lotes
            codigos_lista = list(codigos_solo_bd)
            for i in range(0, len(codigos_lista), 1000):
                batch = codigos_lista[i:i + 1000]
                
                # Solo marcar si no están ya eliminados
                stmt = (
                    update(Municipio)
                    .where(
                        and_(
                            Municipio.codigo_ine.in_(batch),
                            Municipio.deleted == False  # Solo los no eliminados
                        )
                    )
                    .values(
                        deleted=True,
                        deleted_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                )
                result = await session.execute(stmt)
                eliminados_batch = result.rowcount
                stats['eliminados'] += eliminados_batch
                
                if i % 5000 == 0:
                    logger.info(f"  Marcados como eliminados {i:,}/{len(codigos_lista):,}")
            
            await session.commit()
    
    # Reporte final
    logger.info("=" * 50)
    logger.info("RESUMEN MUNICIPIOS:")
    logger.info(f"  Nuevos: {stats['nuevos']:,}")
    logger.info(f"  Actualizados: {stats['actualizados']:,}")
    logger.info(f"  Reactivados: {stats['reactivados']:,}")
    logger.info(f"  Eliminados (soft-delete): {stats['eliminados']:,}")
    logger.info(f"  Sin cambios: {stats['sin_cambios']:,}")
    logger.info(f"  Errores: {stats['errores']}")
    logger.info(f"  Referencias inválidas: {stats['referencias_invalidas']}")
    logger.info(f"  Total procesados: {processed:,}")
    logger.info("=" * 50)
    
    return stats


async def verificar_integridad_referencial(
    session: AsyncSession, 
    ccaa_cache: Dict[str, str], 
    prov_cache: Dict[str, str]
) -> Dict:
    """
    Verifica la integridad referencial después de la carga.
    """
    logger.info("=== VERIFICACIÓN DE INTEGRIDAD REFERENCIAL ===")
    
    stats = {
        'ccaa_sin_provincias': 0,
        'provincias_sin_municipios': 0,
        'municipios_huérfanos': 0
    }
    
    # 1. Verificar CCAA sin provincias activas
    for codigo_ccaa, ccaa_id in ccaa_cache.items():
        result = await session.execute(
            select(Provincia)
            .where(
                and_(
                    Provincia.comunidad_autonoma_id == ccaa_id,
                    Provincia.deleted == False
                )
            )
        )
        provincias_activas = result.scalars().all()
        
        if not provincias_activas:
            stats['ccaa_sin_provincias'] += 1
            logger.warning(f"CCAA {codigo_ccaa} no tiene provincias activas")
    
    # 2. Verificar provincias sin municipios activos
    for codigo_prov, prov_id in prov_cache.items():
        result = await session.execute(
            select(Municipio)
            .where(
                and_(
                    Municipio.provincia_id == prov_id,
                    Municipio.deleted == False
                )
            )
        )
        municipios_activos = result.scalars().all()
        
        if not municipios_activos:
            stats['provincias_sin_municipios'] += 1
            logger.warning(f"Provincia {codigo_prov} no tiene municipios activos")
    
    # 3. Verificar municipios huérfanos (provincia eliminada o inexistente)
    # Solo verificar municipios activos
    result = await session.execute(
        select(Municipio)
        .where(
            and_(
                Municipio.deleted == False,
                Municipio.provincia_id.not_in(list(prov_cache.values()))
            )
        )
    )
    municipios_huérfanos = result.scalars().all()
    stats['municipios_huérfanos'] = len(municipios_huérfanos)
    
    if municipios_huérfanos:
        logger.warning(f"Encontrados {len(municipios_huérfanos)} municipios activos huérfanos")
        for muni in municipios_huérfanos[:10]:
            logger.warning(f"  - {muni.codigo_ine}: {muni.nombre_oficial}")
        if len(municipios_huérfanos) > 10:
            logger.warning(f"  ... y {len(municipios_huérfanos) - 10} más")
    
    logger.info("=" * 50)
    logger.info("RESUMEN INTEGRIDAD REFERENCIAL:")
    logger.info(f"  CCAA sin provincias activas: {stats['ccaa_sin_provincias']}")
    logger.info(f"  Provincias sin municipios activos: {stats['provincias_sin_municipios']}")
    logger.info(f"  Municipios activos huérfanos: {stats['municipios_huérfanos']}")
    logger.info("=" * 50)
    
    return stats


async def verificar_conteos_finales(session: AsyncSession):
    """Verificar conteos finales en la base de datos"""
    logger.info("=== VERIFICACIÓN DE CONTEO FINAL ===")
    
    # Contar activos vs totales
    result = await session.execute(select(ComunidadAutonoma))
    todas_ccaa = result.scalars().all()
    
    result = await session.execute(
        select(ComunidadAutonoma).where(ComunidadAutonoma.deleted == False)
    )
    activas_ccaa = result.scalars().all()
    
    result = await session.execute(select(Provincia))
    todas_prov = result.scalars().all()
    
    result = await session.execute(
        select(Provincia).where(Provincia.deleted == False)
    )
    activas_prov = result.scalars().all()
    
    result = await session.execute(select(Municipio))
    todos_muni = result.scalars().all()
    
    result = await session.execute(
        select(Municipio).where(Municipio.deleted == False)
    )
    activos_muni = result.scalars().all()
    
    safe_print(f"\n" + "=" * 80)
    safe_print("RESUMEN FINAL EN BASE DE DATOS:")
    safe_print("=" * 80)
    safe_print("COMUNIDADES AUTÓNOMAS:")
    safe_print(f"  Total: {len(todas_ccaa)} (Activas: {len(activas_ccaa)}, Eliminadas: {len(todas_ccaa) - len(activas_ccaa)})")
    safe_print("\nPROVINCIAS:")
    safe_print(f"  Total: {len(todas_prov)} (Activas: {len(activas_prov)}, Eliminadas: {len(todas_prov) - len(activas_prov)})")
    safe_print("\nMUNICIPIOS:")
    safe_print(f"  Total: {len(todos_muni):,} (Activos: {len(activos_muni):,}, Eliminados: {len(todos_muni) - len(activos_muni):,})")
    safe_print("=" * 80)
    
    logger.info("RESUMEN FINAL EN BASE DE DATOS:")
    logger.info(f"CCAA: Total={len(todas_ccaa)}, Activas={len(activas_ccaa)}")
    logger.info(f"Provincias: Total={len(todas_prov)}, Activas={len(activas_prov)}")
    logger.info(f"Municipios: Total={len(todos_muni):,}, Activos={len(activos_muni):,}")


async def cargar_datos(
    session: AsyncSession,
    df_ccaa: pd.DataFrame, 
    df_provincias: pd.DataFrame, 
    df_municipios: pd.DataFrame
) -> bool:
    """
    Ejecuta la carga de datos geográficos.
    
    Args:
        session: Sesión de base de datos
        df_ccaa: DataFrame de comunidades autónomas
        df_provincias: DataFrame de provincias
        df_municipios: DataFrame de municipios
    
    Returns:
        bool: True si la carga fue exitosa, False si hubo error
    """
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
        # Iniciar transacción
        await session.begin()
        
        # 1. Cargar Comunidades Autónomas
        ccaa_cache, stats_ccaa = await cargar_comunidades_autonomas(session, df_ccaa)
        
        # 2. Cargar Provincias
        prov_cache, stats_prov = await cargar_provincias(session, df_provincias, ccaa_cache)
        
        # 3. Cargar Municipios
        stats_muni = await cargar_municipios(session, df_municipios, prov_cache)
        
        # 4. Verificar integridad referencial
        stats_integridad = await verificar_integridad_referencial(session, ccaa_cache, prov_cache)
        
        # 5. Commit transacción
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
        safe_print(f"CCAA: +{stats_ccaa['nuevas']} nuevas, ↑{stats_ccaa['actualizadas']} actualizadas, ↻{stats_ccaa['reactivadas']} reactivadas, ✗{stats_ccaa['eliminadas']} eliminadas")
        safe_print(f"Provincias: +{stats_prov['nuevas']} nuevas, ↑{stats_prov['actualizadas']} actualizadas, ↻{stats_prov['reactivadas']} reactivadas, ✗{stats_prov['eliminadas']} eliminadas")
        safe_print(f"Municipios: +{stats_muni['nuevos']:,} nuevos, ↑{stats_muni['actualizados']:,} actualizados, ↻{stats_muni['reactivados']:,} reactivados, ✗{stats_muni['eliminados']:,} eliminados")
        
        return True
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error en la transacción: {e}", exc_info=True)
        safe_print(f"\nERROR EN LA CARGA: {e}")
        return False


def cargar_desde_csv():
    """Carga datos desde archivos CSV"""
    safe_print("=" * 80)
    safe_print("CARGA DE DATOS GEOGRÁFICOS DESDE CSV")
    safe_print("=" * 80)        
    loop = asyncio.get_event_loop()
    async def main():
        async with AsyncSessionLocal() as session:
            # Cargar DataFrames desde CSV
            df_ccaa = pd.read_csv('data/geografia/comunidades_autonomas.csv', dtype={'codigo_ine': str, 'activo': bool})
            df_provincias = pd.read_csv('data/geografia/provincias.csv', dtype={'codigo_ine': str, 'comunidad_autonoma_codigo': str, 'activo': bool})
            df_municipios = pd.read_csv('data/geografia/municipios.csv', dtype={'codigo_ine': str, 'provincia_codigo': str, 'activo': bool})
            
            # Ejecutar carga de datos
            resultado = await cargar_datos(session, df_ccaa, df_provincias, df_municipios)
            if resultado:
                safe_print("Carga de datos completada con éxito.")
            else:
                safe_print("La carga de datos falló.")  
    loop.run_until_complete(main()) 
 