from typing import List, Tuple
from sqlalchemy import select, func, and_, or_, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.inmuebles import Inmueble
from app.db.models.discovery import InmuebleRaw

async def sugerir_candidatos_censo(
    db: AsyncSession, 
    inmueble_raw_id: int, 
    limit: int = 5,
    min_score: float = 0.2
) -> List[Tuple[Inmueble, float]]:
    """
    Busca candidatos en el censo para un anuncio dado.
    Combina similitud de texto y proximidad geográfica.
    """
    # 1. Obtener datos del anuncio
    res = await db.execute(select(InmuebleRaw).where(InmuebleRaw.id == inmueble_raw_id))
    ad = res.scalar_one_or_none()
    
    if not ad:
        return []

    # 2. Query de Matching
    # Usamos similitud de trigramas (necesita pg_trgm)
    # y distancia PostGIS
    
    # Similitud de texto
    sim_score = func.similarity(Inmueble.nombre, ad.titulo)
    
    # Distancia geográfica (si el anuncio tiene geom)
    dist_score = cast(0, Float)
    if ad.geom is not None:
        # Puntos cercanos puntúan más. Una distancia de 0m -> 1.0, 5000m -> 0.0 (simplificado)
        dist_m = func.ST_Distance(Inmueble.coordenadas, ad.geom)
        # Factor invertido: 1 / (1 + dist/500)
        dist_score = 1.0 / (1.0 + dist_m / 500.0)

    # Score combinado (50% texto, 50% geografía si existe)
    total_score = (sim_score + dist_score) / 2.0 if ad.geom is not None else sim_score

    stmt = (
        select(Inmueble, total_score.label("match_score"))
        .where(
            or_(
                sim_score > min_score,
                and_(ad.geom is not None, func.ST_DWithin(Inmueble.coordenadas, ad.geom, 5000))
            )
        )
        .order_by(total_score.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return result.all()
