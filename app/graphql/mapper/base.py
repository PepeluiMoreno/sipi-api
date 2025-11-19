# app/graphql/mapper/base.py
"""Main SQLAlchemy to Strawberry mapper with library integration"""
from typing import Type

try:
    from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper
    HAS_LIBRARY = True
except ImportError:
    HAS_LIBRARY = False

from .cache import TypeCache
from .property_extractor import PropertyExtractor
from .type_builder import TypeBuilder

class SQLAlchemyMapper:
    """
    Mapper que combina:
    - strawberry-sqlalchemy-mapper: columnas + relaciones
    - Código custom: propiedades calculadas
    """
    
    def __init__(self):
        self.cache = TypeCache()
        self.property_extractor = PropertyExtractor()
        self.type_builder = TypeBuilder()
        
        if HAS_LIBRARY:
            try:
                self.base_mapper = StrawberrySQLAlchemyMapper()
                print("✅ Usando strawberry-sqlalchemy-mapper como base")
            except Exception as e:
                print(f"⚠️  Error al inicializar librería: {e}")
                self.base_mapper = None
        else:
            print("⚠️  strawberry-sqlalchemy-mapper NO instalado")
            self.base_mapper = None
    
    def type(self, model: Type) -> Type:
        """Convierte un modelo SQLAlchemy a tipo Strawberry"""
        model_name = model.__name__
        
        if self.cache.has_type(model_name):
            return self.cache.get_type(model_name)
        
        fields = {}
        
        # 1. Obtener campos base de la librería
        if self.base_mapper:
            try:
                base_type = self.base_mapper.type(model)
                if hasattr(base_type, '__annotations__'):
                    fields = base_type.__annotations__.copy()
            except Exception as e:
                print(f"  ⚠️  Librería falló para {model_name}: {e}")
                fields = self._fallback_map_columns(model)
        else:
            fields = self._fallback_map_columns(model)
        
        # 2. Añadir propiedades calculadas
        try:
            properties = self.property_extractor.extract(model)
            if properties:
                fields.update(properties)
        except Exception as e:
            print(f"  ⚠️  Error extrayendo propiedades de {model_name}: {e}")
        
        # 3. Construir tipo
        strawberry_type = self.type_builder.build_type(model_name, fields)
        self.cache.set_type(model_name, strawberry_type)
        
        return strawberry_type
    
    def input_type(self, model: Type, prefix: str = "", optional: bool = False) -> Type:
        """Crea InputType para crear/actualizar"""
        if self.base_mapper:
            try:
                return self.base_mapper.input_type(model, prefix, optional)
            except:
                pass
        
        fields = self._fallback_map_columns(model, for_input=True, prefix=prefix, optional=optional)
        type_name = f"{model.__name__}{prefix}Input"
        return self.type_builder.build_input_type(type_name, fields)
    
    def _fallback_map_columns(self, model: Type, for_input: bool = False, prefix: str = "", optional: bool = False):
        """Mapeo básico de columnas como fallback"""
        from sqlalchemy.inspection import inspect
        from sqlalchemy.dialects.postgresql import JSONB
        from strawberry.scalars import JSON
        from typing import Optional as Opt
        from datetime import datetime, date
        from decimal import Decimal
        import strawberry
        import uuid
        import enum
        
        mapper = inspect(model)
        fields = {}
        
        for attr in mapper.attrs:
            if hasattr(attr, 'columns'):
                column = attr.columns[0]
                
                if for_input and column.primary_key and prefix.lower() == "create":
                    continue
                
                if isinstance(column.type, JSONB):
                    field_type = JSON
                    if column.nullable or optional:
                        field_type = Opt[JSON]
                    fields[attr.key] = field_type
                    continue
                
                try:
                    python_type = column.type.python_type
                    
                    if isinstance(python_type, type) and issubclass(python_type, enum.Enum):
                        field_type = python_type
                    elif python_type == uuid.UUID:
                        field_type = strawberry.ID
                    elif python_type == Decimal:
                        field_type = float
                    elif python_type == dict:
                        field_type = JSON
                    else:
                        field_type = python_type
                    
                    if column.nullable or optional:
                        field_type = Opt[field_type]
                    
                    fields[attr.key] = field_type
                except:
                    fields[attr.key] = Opt[str]
        
        return fields