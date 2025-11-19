# app/graphql/mapper/property_extractor.py
"""Extracts calculated properties from SQLAlchemy models"""
from typing import Type, Dict

from .type_inference import TypeInferencer

class PropertyExtractor:
    """Extrae propiedades calculadas (@property) de modelos"""
    
    def __init__(self):
        self.inferencer = TypeInferencer()
        self.ignored_properties = {'metadata', 'registry'}
    
    def extract(self, model: Type) -> Dict[str, Type]:
        """Extrae propiedades mapeables del modelo"""
        properties = {}
        
        for attr_name in dir(model):
            if attr_name.startswith('_'):
                continue
            
            if attr_name in self.ignored_properties:
                continue
            
            try:
                attr = getattr(model, attr_name)
                
                if isinstance(attr, property):
                    ret_type = self.inferencer.infer_from_property(attr)
                    
                    if ret_type is not None:
                        properties[attr_name] = ret_type
                    
            except Exception:
                continue
        
        return properties