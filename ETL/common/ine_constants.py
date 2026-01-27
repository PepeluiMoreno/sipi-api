# ETL/common/ine_constants.py
"""
Constantes oficiales del INE para mapeo geográfico.
Fuente: https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm

Centraliza los diccionarios de mapeo usados por todos los scripts ETL.
"""

# Comunidades Autónomas: codigo_ine (2 dígitos) -> nombre oficial
CCAA_OFICIAL = {
    '01': 'Andalucía',
    '02': 'Aragón',
    '03': 'Asturias, Principado de',
    '04': 'Balears, Illes',
    '05': 'Canarias',
    '06': 'Cantabria',
    '07': 'Castilla y León',
    '08': 'Castilla-La Mancha',
    '09': 'Cataluña',
    '10': 'Comunitat Valenciana',
    '11': 'Extremadura',
    '12': 'Galicia',
    '13': 'Madrid, Comunidad de',
    '14': 'Murcia, Región de',
    '15': 'Navarra, Comunidad Foral de',
    '16': 'País Vasco',
    '17': 'Rioja, La',
    '18': 'Ceuta',
    '19': 'Melilla',
}

# Mapeo provincia (2 dígitos) -> comunidad autónoma (2 dígitos)
PROVINCIA_A_CCAA = {
    # Andalucía (01)
    '04': '01', '11': '01', '14': '01', '18': '01',
    '21': '01', '23': '01', '29': '01', '41': '01',
    # Aragón (02)
    '22': '02', '44': '02', '50': '02',
    # Asturias (03)
    '33': '03',
    # Baleares (04)
    '07': '04',
    # Canarias (05)
    '35': '05', '38': '05',
    # Cantabria (06)
    '39': '06',
    # Castilla y León (07)
    '05': '07', '09': '07', '24': '07', '34': '07',
    '37': '07', '40': '07', '42': '07', '47': '07', '49': '07',
    # Castilla-La Mancha (08)
    '02': '08', '13': '08', '16': '08', '19': '08', '45': '08',
    # Cataluña (09)
    '08': '09', '17': '09', '25': '09', '43': '09',
    # Comunitat Valenciana (10)
    '03': '10', '12': '10', '46': '10',
    # Extremadura (11)
    '06': '11', '10': '11',
    # Galicia (12)
    '15': '12', '27': '12', '32': '12', '36': '12',
    # Madrid (13)
    '28': '13',
    # Murcia (14)
    '30': '14',
    # Navarra (15)
    '31': '15',
    # País Vasco (16)
    '01': '16', '20': '16', '48': '16',
    # La Rioja (17)
    '26': '17',
    # Ceuta (18)
    '51': '18',
    # Melilla (19)
    '52': '19',
}

# Nombres oficiales de provincias: codigo_ine (2 dígitos) -> nombre
NOMBRES_PROVINCIAS = {
    '01': 'Araba/Álava',
    '02': 'Albacete',
    '03': 'Alicante/Alacant',
    '04': 'Almería',
    '05': 'Ávila',
    '06': 'Badajoz',
    '07': 'Balears, Illes',
    '08': 'Barcelona',
    '09': 'Burgos',
    '10': 'Cáceres',
    '11': 'Cádiz',
    '12': 'Castellón/Castelló',
    '13': 'Ciudad Real',
    '14': 'Córdoba',
    '15': 'Coruña, A',
    '16': 'Cuenca',
    '17': 'Girona',
    '18': 'Granada',
    '19': 'Guadalajara',
    '20': 'Gipuzkoa',
    '21': 'Huelva',
    '22': 'Huesca',
    '23': 'Jaén',
    '24': 'León',
    '25': 'Lleida',
    '26': 'Rioja, La',
    '27': 'Lugo',
    '28': 'Madrid',
    '29': 'Málaga',
    '30': 'Murcia',
    '31': 'Navarra',
    '32': 'Ourense',
    '33': 'Asturias',
    '34': 'Palencia',
    '35': 'Palmas, Las',
    '36': 'Pontevedra',
    '37': 'Salamanca',
    '38': 'Santa Cruz de Tenerife',
    '39': 'Cantabria',
    '40': 'Segovia',
    '41': 'Sevilla',
    '42': 'Soria',
    '43': 'Tarragona',
    '44': 'Teruel',
    '45': 'Toledo',
    '46': 'Valencia/València',
    '47': 'Valladolid',
    '48': 'Bizkaia',
    '49': 'Zamora',
    '50': 'Zaragoza',
    '51': 'Ceuta',
    '52': 'Melilla',
}

# Alias de provincias para búsqueda por nombre
# Formato: nombre_normalizado -> codigo_ine
ALIAS_PROVINCIAS = {
    # País Vasco (nombres bilingües)
    'ALAVA': '01',
    'ARABA': '01',
    'ARABA/ALAVA': '01',
    'ARABA ALAVA': '01',
    'GUIPUZCOA': '20',
    'GIPUZKOA': '20',
    'VIZCAYA': '48',
    'BIZKAIA': '48',
    # Galicia
    'ORENSE': '32',
    'OURENSE': '32',
    'LA CORUNA': '15',
    'A CORUNA': '15',
    'CORUNA': '15',
    'CORUNA A': '15',
    # Cataluña
    'GERONA': '17',
    'GIRONA': '17',
    'LERIDA': '25',
    'LLEIDA': '25',
    # Valencia
    'ALICANTE': '03',
    'ALACANT': '03',
    'ALICANTE/ALACANT': '03',
    'CASTELLON': '12',
    'CASTELLO': '12',
    'CASTELLON/CASTELLO': '12',
    'VALENCIA': '46',
    'VALENCIA/VALENCIA': '46',
    # Baleares
    'BALEARES': '07',
    'BALEARS': '07',
    'ILLES BALEARS': '07',
    'ISLAS BALEARES': '07',
    # Canarias
    'LAS PALMAS': '35',
    'PALMAS LAS': '35',
    'SANTA CRUZ DE TENERIFE': '38',
    'TENERIFE': '38',
    # La Rioja
    'LA RIOJA': '26',
    'RIOJA': '26',
    'RIOJA LA': '26',
    # Asturias
    'ASTURIAS': '33',
    'OVIEDO': '33',
    # Cantabria
    'CANTABRIA': '39',
    'SANTANDER': '39',
    # Navarra
    'NAVARRA': '31',
    'PAMPLONA': '31',
    # Madrid
    'MADRID': '28',
    # Murcia
    'MURCIA': '30',
    # Ceuta y Melilla
    'CEUTA': '51',
    'MELILLA': '52',
}

# Alias de municipios especiales (casos conocidos de discrepancia)
# Formato: (nombre_normalizado, codigo_provincia) -> codigo_municipio_completo
ALIAS_MUNICIPIOS = {
    # Ejemplos de municipios con nombres alternativos conocidos
    ('VITORIA', '01'): '01059',
    ('VITORIA-GASTEIZ', '01'): '01059',
    ('GASTEIZ', '01'): '01059',
    ('SAN SEBASTIAN', '20'): '20069',
    ('DONOSTIA', '20'): '20069',
    ('DONOSTIA-SAN SEBASTIAN', '20'): '20069',
    ('BILBAO', '48'): '48020',
    ('BILBO', '48'): '48020',
}
