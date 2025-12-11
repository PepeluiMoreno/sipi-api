"""
app/graphql/custom_fields.py
Funciones helper para detectar y manejar campos geometry/geography en modelos SQLAlchemy
"""
from typing import Any, List, Tuple, Optional
import strawberry
from geoalchemy2.shape import to_shape

# ============================================================
# TIPO PARA COORDENADAS
# ============================================================

@strawberry.type
class Coordinates:
    """Coordenadas geográficas simples"""
    lat: float
    lon: float


def resolve_coordinates(geom) -> Optional[Coordinates]:
    """
    Resuelve un campo geometry/geography a Coordinates
    """
    if not geom:
        return None
    try:
        point = to_shape(geom)
        return Coordinates(lat=point.y, lon=point.x)
    except Exception as e:
        print(f"⚠️  Error convirtiendo coordenadas: {e}")
        return None


# ============================================================
# DETECCIÓN DE CAMPOS GEOMETRY
# ============================================================

def detect_custom_fields(model: Any) -> bool:
    """
    Detecta si un modelo tiene columnas geometry/geography
    """
    if not hasattr(model, "__table__"):
        return False
    
    for col in model.__table__.columns:
        col_type_str = str(col.type).lower()
        if 'geometry' in col_type_str or 'geography' in col_type_str:
            return True
    return False


def get_excluded_field_names_for_model(model: Any) -> List[str]:
    """
    Retorna lista de nombres de campos geometry/geography que deben excluirse
    """
    excluded = []
    if not hasattr(model, "__table__"):
        return excluded
    
    for col in model.__table__.columns:
        col_type_str = str(col.type).lower()
        if 'geometry' in col_type_str or 'geography' in col_type_str:
            excluded.append(col.name)
    
    return excluded


# ============================================================
# CREACIÓN DE TIPOS CON CAMPOS PERSONALIZADOS
# ============================================================

def create_type_with_custom_fields(mapper_instance, model: Any, name: str) -> Tuple[Any, List[str]]:
    """
    Crea un tipo Strawberry para el modelo, excluyendo campos geometry automáticamente
    
    Returns:
        (tipo_creado, lista_de_campos_excluidos)
    """
    excluded_fields = get_excluded_field_names_for_model(model)
    
    if excluded_fields:
        # Usar mapper con exclude
        tipo = mapper_instance.type(model, name=name, exclude=excluded_fields)
    else:
        # Mapper normal sin exclude
        tipo = mapper_instance.type(model, name=name)
    
    return tipo, excluded_fields


def attach_field_resolvers_to_type(strawberry_type: Any, model: Any):
    """
    Intenta adjuntar resolvers personalizados para campos geometry
    (Placeholder - implementar si necesitas exponer coordenadas como campos resueltos)
    """
    # Por ahora, simplemente excluimos los campos geometry
    # Si en el futuro quieres exponerlos, añade resolvers personalizados aquí
    pass