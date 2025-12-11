"""app/graphql/coordinates.py - Tipos y resolvers para coordenadas geográficas"""
import strawberry
from typing import Optional
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape


@strawberry.type
class Coordinates:
    """
    Coordenadas geográficas (latitud/longitud)
    Compatible con el formato usado en 8base y GeoJSON
    """
    latitude: float
    longitude: float
    
    @strawberry.field
    def as_array(self) -> list[float]:
        """Retorna coordenadas como array [lat, lon]"""
        return [self.latitude, self.longitude]


def resolve_coordinates(geometry_value) -> Optional[Coordinates]:
    """
    Convierte un POINT de PostGIS a tipo Coordinates
    
    Args:
        geometry_value: Valor del campo Geometry(POINT, 4326) de GeoAlchemy2
        
    Returns:
        Objeto Coordinates con latitude/longitude o None si no hay valor
        
    Example:
        >>> point = WKBElement(...)  # POINT(-73.985910 40.748981)
        >>> coords = resolve_coordinates(point)
        >>> coords.latitude
        40.748981
        >>> coords.longitude
        -73.985910
    """
    if geometry_value is None:
        return None
    
    try:
        # Convertir WKBElement (formato binario de PostGIS) a Shapely Point
        shape = to_shape(geometry_value)
        
        # En PostGIS/GeoJSON: X = longitude, Y = latitude
        return Coordinates(
            latitude=shape.y,
            longitude=shape.x
        )
    except Exception as e:
        print(f"⚠️  Error convirtiendo coordenadas: {e}")
        return None


@strawberry.input
class CoordinatesInput:
    """
    Input para crear/actualizar coordenadas
    Compatible con el formato GeoJSON 
    """
    latitude: float
    longitude: float
    
    def to_wkt(self) -> str:
        """Convierte a formato WKT para PostGIS"""
        return f"POINT({self.longitude} {self.latitude})"
    
    def to_geojson(self) -> dict:
        """Convierte a formato GeoJSON"""
        return {
            "type": "Point",
            "coordinates": [self.longitude, self.latitude]
        }