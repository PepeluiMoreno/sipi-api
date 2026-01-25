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
    # Casos simples
    'el': 'los',
    'la': 'las',
    'un': 'unos',

    # Modelos Compuestos (CamelCase preservation)
    'agenciainmobiliaria': 'AgenciasInmobiliarias',
    'colegioprofesional': 'ColegiosProfesionales',
    'registropropiedad': 'RegistrosPropiedad',
    'comunidadautonoma': 'ComunidadesAutonomas',

    # Versiones lowercase para queries
    'ComunidadAutonoma': 'ComunidadesAutonomas',
    'AgenciaInmobiliaria': 'AgenciasInmobiliarias',
    'ColegioProfesional': 'ColegiosProfesionales',
    'RegistroPropiedad': 'RegistrosPropiedad',

    # Titulares (sufijo simple es correcto habitualmente, pero por si acaso)
    'administraciontitular': 'AdministracionTitulares',
    'diocesistitular': 'DiocesisTitulares',
    'registropropiedadtitular': 'RegistroPropiedadTitulares',
    'notariatitular': 'NotariaTitulares',
}


def pluralize(word: str) -> str:
    """
    Pluraliza una palabra en español según reglas, PRESERVANDO mayúsculas/minúsculas.
    """
    if not word:
        return word

    # 1. Excepciones específicas - buscar primero con casing original
    if word in PLURALES_EXCEPCIONES:
        return PLURALES_EXCEPCIONES[word]

    # Luego buscar con lowercase
    word_lower = word.lower()
    if word_lower in PLURALES_EXCEPCIONES:
        return PLURALES_EXCEPCIONES[word_lower]
    
    # 2. Invariables
    if word_lower in PLURALES_INVARIABLES:
        return word
    
    # Algunos invariables tienen sufijos específicos
    if any(word_lower.endswith(inv) for inv in PLURALES_INVARIABLES):
        return word
    
    # 3. Terminadas en -ción o -sión
    if word_lower.endswith('cion') or word_lower.endswith('sion'):
        return word + 'es'
    
    # 4. Terminadas en -z
    if word_lower.endswith('z'):
        return word[:-1] + 'ces'
    
    # 5. Terminadas en vocal átona (a, e, o) + consonante
    # Cuidado con esta regla general. 'hotel' -> 'hoteles'. 'motor' -> 'motores'.
    # Pero 'AgenciaInmobiliaria' termina en 'a'.
    
    # Regla específica: termina en vocal (a, e, i, o, u) -> 's'
    # EXCEPT: 'í', 'ú' tónicas -> 'es' (tabú -> tabúes)
    
    # Mejor enfoque simplificado y seguro:
    
    # Termina en vocal no acentuada (a, e, o) -> s
    if word_lower[-1] in 'aeio':
        return word + 's'
        
    # Termina en u -> s (espiritu -> espiritus, tribu -> tribus)
    # Excepción í, ú tónicas -> es (pero aquí simplificamos, u -> s suele ser safer para código)
    if word_lower[-1] == 'u':
        return word + 's'

    # Termina en í tónica -> es (jabalí -> jabalíes). 
    # En código solemos usar ASCII, pero soportamos utf-8.
    if word_lower.endswith('í') or word_lower.endswith('ú'):
        return word + 'es'
        
    # Termina en consonante (d, j, l, n, r, y) o s/x aguda -> es
    # Pero si termina en s y NO es aguda (crisis), es invariable. Ya lo cubrimos en invariables.
    
    # Regla general para consonantes (no z, que ya vimos):
    if word_lower[-1] not in 'aeiou':
        # Si termina en s, asumimos invariable si no es palabra de una sílaba, 
        # pero 'tecnicos' (plural) no debería pasar por aquí si la entrada es singular.
        # Si la entrada es 'tecnico' -> 'tecnicos'.
        if word_lower.endswith('s') and not word_lower.endswith('ss'): # ss (bypass?)
             # Asumimos que si termina en s es invariable o ya plural
             return word
             
        return word + 'es'
    
    return word + 's'