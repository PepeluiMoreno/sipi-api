# app/graphql/config/spanish.py
"""Configuración de particularización al español"""

# Palabras con plural invariante (no cambian)
PLURALES_INVARIABLES = {
    'crisis',
    'tesis',
    'sintesis',
    'analisis',
    'diocesis',
    'parentesis',
    'hipotesis',
    'enfasis',
}

# Excepciones específicas (solo si las reglas lingüísticas fallan)
# Formato: 'singular': 'plural'
PLURALES_EXCEPCIONES = {
    # Añadir aquí solo casos especiales que las reglas no cubran
    # Ejemplo:
    # 'caracter': 'caracteres',
}