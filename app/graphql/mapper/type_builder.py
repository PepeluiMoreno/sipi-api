# app/graphql/mapper/type_builder.py
"""Builds Strawberry types from field definitions"""
from typing import Type, Dict
import strawberry
import keyword

class TypeBuilder:
    """Construye tipos Strawberry desde definiciones de campos"""
    
    # Palabras reservadas de Python que debemos evitar
    PYTHON_KEYWORDS = set(keyword.kwlist) | {
        'type', 'id', 'input', 'object', 'list', 'dict', 'set', 
        'str', 'int', 'float', 'bool', 'bytes'
    }
    
    @staticmethod
    def sanitize_field_name(name: str) -> str:
        """
        Sanitiza nombres de campos que son palabras reservadas.
        
        Args:
            name: Nombre original del campo
            
        Returns:
            Nombre sanitizado (añade _ al final si es palabra reservada)
            
        Example:
            >>> sanitize_field_name("return")
            "return_"
            >>> sanitize_field_name("type")
            "type_"
            >>> sanitize_field_name("nombre")
            "nombre"
        """
        if name in TypeBuilder.PYTHON_KEYWORDS:
            return f"{name}_"
        return name
    
    @staticmethod
    def build_type(type_name: str, fields: Dict[str, Type]) -> Type:
        """Construye un tipo Strawberry"""
        # ✅ Sanitizar nombres de campos
        sanitized_fields = {
            TypeBuilder.sanitize_field_name(key): value 
            for key, value in fields.items()
        }
        
        # Crear clase dinámica con anotaciones
        dynamic_class = type(type_name, (), {"__annotations__": sanitized_fields})
        
        # Decorar con @strawberry.type
        strawberry_type = strawberry.type(dynamic_class)
        
        return strawberry_type
    
    @staticmethod
    def build_input_type(type_name: str, fields: Dict[str, Type]) -> Type:
        """Construye un InputType Strawberry"""
        # ✅ Sanitizar nombres de campos
        sanitized_fields = {
            TypeBuilder.sanitize_field_name(key): value 
            for key, value in fields.items()
        }
        
        # Crear clase dinámica
        dynamic_class = type(type_name, (), {"__annotations__": sanitized_fields})
        
        # Decorar con @strawberry.input
        input_type = strawberry.input(dynamic_class)
        
        return input_type