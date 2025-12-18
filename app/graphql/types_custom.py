import strawberry
from typing import Optional

@strawberry.type
class MatchSuggestion:
    """Sugerencia de vínculo entre un anuncio y un inmueble del censo"""
    inmueble_id: strawberry.ID
    nombre: str
    municipio_nombre: Optional[str] = None
    provincia_nombre: Optional[str] = None
    match_score: float
    distancia_m: Optional[float] = None
