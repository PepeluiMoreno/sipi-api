"""
app/graphql/mapper.py
Instancia única del mapper para evitar dependencias circulares
"""
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

# Instancia única del mapper que se usa en toda la aplicación
mapper = StrawberrySQLAlchemyMapper()