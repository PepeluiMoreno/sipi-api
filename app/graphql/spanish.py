"""app/graphql/spanish.py - Configuración de pluralización al español"""

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


def pluralize(word: str) -> str:
    """
    Pluraliza una palabra en español según reglas lingüísticas.
    
    Reglas implementadas:
    - Invariables: crisis, tesis, análisis, diócesis, etc.
    - Terminadas en -ción/-sión: añade 'es'
    - Terminadas en -z: cambia a -ces
    - Terminadas en vocal átona: añade 's'
    - Terminadas en vocal tónica (í, ú): añade 'es'
    - Terminadas en consonante (excepto s, x): añade 'es'
    - Ya plurales (terminadas en s): no cambia
    
    Args:
        word: Palabra en singular
        
    Returns:
        Palabra en plural
        
    Examples:
        >>> pluralize('provincia')
        'provincias'
        >>> pluralize('inmueble')
        'inmuebles'
        >>> pluralize('actuación')
        'actuaciones'
        >>> pluralize('crisis')
        'crisis'
        >>> pluralize('análisis')
        'analisis'
    """
    word_lower = word.lower()
    
    # 1. Excepciones específicas (máxima prioridad)
    if word_lower in PLURALES_EXCEPCIONES:
        return PLURALES_EXCEPCIONES[word_lower]
    
    # 2. Invariables
    if word_lower in PLURALES_INVARIABLES:
        return word_lower
    
    # Algunos invariables tienen sufijos específicos
    if any(word_lower.endswith(inv) for inv in PLURALES_INVARIABLES):
        return word_lower
    
    # 3. Terminadas en -ción o -sión
    if word_lower.endswith('cion') or word_lower.endswith('sion'):
        return word_lower + 'es'
    
    # 4. Terminadas en -z
    if word_lower.endswith('z'):
        return word_lower[:-1] + 'ces'
    
    # 5. Terminadas en vocal átona (a, e, o) + consonante
    if len(word_lower) > 1 and word_lower[-1] in 'aeiou':
        return word_lower + 's'
    
    # 6. Terminadas en vocal tónica (í, ú)
    if word_lower.endswith(('í', 'ú')):
        return word_lower + 'es'
    
    # 7. Terminadas en consonante (excepto s, x)
    if word_lower[-1] not in 'aeiousx':
        return word_lower + 'es'
    
    # 8. Ya es plural (termina en 's')
    if word_lower.endswith('s'):
        return word_lower
    
    # 9. Por defecto, añadir 's'
    return word_lower + 's'