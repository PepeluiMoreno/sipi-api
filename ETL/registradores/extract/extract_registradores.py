#!/usr/bin/env python3
"""
extract_registradores_definitivo.py
Extracción definitiva con slugs exactos y manejo correcto de Ceuta/Melilla.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import sys

class RegistrosExtractorDefinitivo:
    def __init__(self):
        self.base_url = "https://www.registradores.org"
        self.registros = []
        self.estadisticas = {
            'provincias_procesadas': 0,
            'provincias_exito': 0,
            'provincias_error': 0,
            'registros_totales': 0,
            'inicio': datetime.now(),
            'provincias_falladas': []
        }
        
        # Diccionario exacto de slugs
        self.slugs_provincias = {
            # Excepciones idiomáticas
            'araba--alava': 'Álava',
            'gipuzkoa': 'Guipúzcoa',
            'a-coruna': 'A Coruña', 
            'bizkaia': 'Bizkaia',
            'illes-balears': 'Illes Balears',
            'lleida': 'Lleida',
            'ourense': 'Ourense',
            'girona': 'Girona',
            
            # Ceuta y Melilla (slugs especiales pero tratamiento igual)
            'ceuta/ceuta/registro-de-la-propiedad-de-ceuta-y-merc-y-bm': 'Ceuta',
            'melilla/melilla/registro-de-la-propiedad-de-melilla-y-merc-y-bm': 'Melilla',
            
            # Resto de provincias
            'albacete': 'Albacete',
            'alicante': 'Alicante',
            'almeria': 'Almería',
            'avila': 'Ávila',
            'badajoz': 'Badajoz',
            'barcelona': 'Barcelona',
            'burgos': 'Burgos',
            'caceres': 'Cáceres',
            'cadiz': 'Cádiz',
            'castellon': 'Castellón',
            'ciudad-real': 'Ciudad Real',
            'cordoba': 'Córdoba',
            'cuenca': 'Cuenca',
            'granada': 'Granada',
            'guadalajara': 'Guadalajara',
            'huelva': 'Huelva',
            'huesca': 'Huesca',
            'jaen': 'Jaén',
            'leon': 'León',
            'la-rioja': 'La Rioja',
            'lugo': 'Lugo',
            'madrid': 'Madrid',
            'malaga': 'Málaga',
            'murcia': 'Murcia',
            'navarra': 'Navarra',
            'asturias': 'Asturias',
            'palencia': 'Palencia',
            'las-palmas': 'Las Palmas',
            'pontevedra': 'Pontevedra',
            'salamanca': 'Salamanca',
            'santa-cruz-de-tenerife': 'Santa Cruz de Tenerife',
            'cantabria': 'Cantabria',
            'segovia': 'Segovia',
            'sevilla': 'Sevilla',
            'soria': 'Soria',
            'tarragona': 'Tarragona',
            'teruel': 'Teruel',
            'toledo': 'Toledo',
            'valencia': 'Valencia',
            'valladolid': 'Valladolid',
            'zamora': 'Zamora',
            'zaragoza': 'Zaragoza',
        }
        
        self.semaphore = asyncio.Semaphore(20)
    
    async def fetch_url(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Obtiene HTML de una URL"""
        async with self.semaphore:
            try:
                async with session.get(url, timeout=10, ssl=False) as response:
                    if response.status == 200:
                        return await response.text()
                    return None
            except Exception:
                return None
    
    async def procesar_provincia(self, session: aiohttp.ClientSession, slug: str, nombre: str):
        """Procesa una provincia completa"""
        self.estadisticas['provincias_procesadas'] += 1
        
        url_provincia = f"{self.base_url}/directorio/-/registros/propiedad/{slug}"
        
        html = await self.fetch_url(session, url_provincia)
        
        if not html:
            self.estadisticas['provincias_error'] += 1
            self.estadisticas['provincias_falladas'].append(nombre)
            print(f"No ha sido posible extraer los registradores de la provincia de {nombre}")
            return
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # DETECTAR tipo de página
        lista = soup.find('ul', class_='listado-registros')
        
        if lista:
            # PÁGINA DE LISTADO (provincia normal)
            items = lista.find_all('li')
            num_registros = len(items)
            
            print(f"Procesando la provincia de {nombre}: {num_registros} registros de la propiedad encontrados.")
            
            enlaces = []
            for li in items:
                enlace = li.find('a', href=True)
                if enlace:
                    href = enlace['href']
                    if href.startswith('/'):
                        href = self.base_url + href
                    enlaces.append({
                        'url': href,
                        'nombre': enlace.get_text(strip=True),
                        'provincia': nombre,
                        'slug': slug
                    })
        else:
            # PÁGINA INDIVIDUAL (Ceuta/Melilla o error)
            # Verificar si es una página de registro válida
            cont_derecha = soup.find('div', class_='contDerecha')
            if cont_derecha:
                # Es página individual válida (Ceuta/Melilla)
                print(f"Procesando la provincia de {nombre}: 1 registro de la propiedad encontrado.")
                
                # Extraer nombre de la página
                nombre_registro = nombre
                title = soup.find('title')
                if title:
                    nombre_registro = title.get_text(strip=True)
                
                enlaces = [{
                    'url': url_provincia,
                    'nombre': nombre_registro,
                    'provincia': nombre,
                    'slug': slug
                }]
            else:
                # No es página válida
                self.estadisticas['provincias_error'] += 1
                self.estadisticas['provincias_falladas'].append(nombre)
                print(f"No ha sido posible extraer los registradores de la provincia de {nombre}")
                return
        
        print(f"Extrayendo detalles de cada registro...")
        tareas = [self.extraer_detalles_registro(session, enlace) for enlace in enlaces]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        registros_exitosos = [r for r in resultados if isinstance(r, dict)]
        self.registros.extend(registros_exitosos)
        self.estadisticas['registros_totales'] += len(registros_exitosos)
        self.estadisticas['provincias_exito'] += 1
    
    async def extraer_detalles_registro(self, session: aiohttp.ClientSession, enlace: Dict) -> Optional[Dict]:
        """Extrae detalles de un registro individual - TRATAMIENTO IGUAL PARA TODOS"""
        try:
            html = await self.fetch_url(session, enlace['url'])
            if not html:
                return None
            
            print(f"Extrayendo detalles del {enlace['nombre']}")
            
            datos = {
                'nombre': enlace['nombre'],
                'url': enlace['url'],
                'provincia': enlace['provincia'],
                'slug_provincia': enlace['slug'],
                'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'direccion': '',
                'telefono': '',
                'email': '',
                'horario': '',
                'registrador': ''
            }
            
            soup = BeautifulSoup(html, 'html.parser')
            cont_derecha = soup.find('div', class_='contDerecha')
            
            if cont_derecha:
                # Dirección (MISMO para todos)
                datos_decanato = cont_derecha.find('div', class_='datosDecanato')
                if datos_decanato:
                    for subtitulo in datos_decanato.find_all('div', class_='subtit-decanato'):
                        if 'dirección' in subtitulo.get_text(strip=True).lower():
                            siguiente = subtitulo.find_next('div', class_='texto-decanato')
                            if siguiente:
                                datos['direccion'] = siguiente.get_text(strip=True)
                
                # Contacto (MISMO para todos)
                contacto_decanato = cont_derecha.find('div', class_='contactoDecanato')
                if contacto_decanato:
                    tlf_tag = contacto_decanato.find('span', class_='tlf')
                    if tlf_tag:
                        datos['telefono'] = tlf_tag.get_text(strip=True)
                    
                    email_tag = contacto_decanato.find('a', class_='email')
                    if email_tag:
                        datos['email'] = email_tag.get_text(strip=True)
                    
                    for texto in contacto_decanato.find_all(string=True):
                        if 'datos del registrador' in texto.lower():
                            siguiente_tlf = texto.find_next('span', class_='tlf')
                            if siguiente_tlf:
                                datos['registrador'] = siguiente_tlf.get_text(strip=True)
                
                # Horario (MISMO para todos)
                if datos_decanato:
                    for subtitulo in datos_decanato.find_all('div', class_='subtit-decanato'):
                        if 'horario' in subtitulo.get_text(strip=True).lower():
                            textos_horario = []
                            siguiente = subtitulo
                            while True:
                                siguiente = siguiente.find_next_sibling('div', class_='texto-decanato')
                                if not siguiente or 'subtit-decanato' in siguiente.get('class', []):
                                    break
                                textos_horario.append(siguiente.get_text(strip=True))
                            if textos_horario:
                                datos['horario'] = ' | '.join(textos_horario)
            
            return datos
            
        except Exception:
            return None
    
    async def ejecutar_extraccion(self):
        """Ejecuta extracción para todas las provincias"""
        print("Iniciando extracción de registros de propiedad...\n")
        
        connector = aiohttp.TCPConnector(limit=30, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = []
            for slug, nombre in self.slugs_provincias.items():
                tarea = self.procesar_provincia(session, slug, nombre)
                tareas.append(tarea)
            
            await asyncio.gather(*tareas)
    
    def guardar_resultados(self):
        """Guarda resultados en CSV"""
        if not self.registros:
            print("\nNo se extrajeron registros.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_csv = Path(__file__).parent / f"registros_propiedad_{timestamp}.csv"
        
        df = pd.DataFrame(self.registros)
        
        columnas_orden = [
            'nombre', 'provincia', 'slug_provincia',
            'direccion', 'telefono', 'email', 
            'horario', 'registrador', 'url', 'fecha_extraccion'
        ]
        columnas_existentes = [c for c in columnas_orden if c in df.columns]
        
        df[columnas_existentes].to_csv(ruta_csv, index=False, encoding='utf-8-sig')
        
        print(f"\nResultados guardados en: {ruta_csv}")
        print(f"Registros guardados: {len(df)}")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas finales"""
        duracion = datetime.now() - self.estadisticas['inicio']
        
        print("\n" + "="*50)
        print("ESTADÍSTICAS FINALES")
        print("="*50)
        print(f"Total provincias: {len(self.slugs_provincias)}")
        print(f"Provincias procesadas: {self.estadisticas['provincias_procesadas']}")
        print(f"Provincias con éxito: {self.estadisticas['provincias_exito']}")
        print(f"Provincias con error: {self.estadisticas['provincias_error']}")
        print(f"Total registros extraídos: {self.estadisticas['registros_totales']}")
        print(f"Duración total: {duracion.total_seconds():.0f} segundos")
        
        if self.estadisticas['provincias_falladas']:
            print(f"\nProvincias que fallaron:")
            for provincia in sorted(self.estadisticas['provincias_falladas']):
                print(f"  • {provincia}")
        
        print("="*50)

async def main():
    extractor = RegistrosExtractorDefinitivo()
    
    try:
        await extractor.ejecutar_extraccion()
        extractor.guardar_resultados()
        extractor.mostrar_estadisticas()
    except KeyboardInterrupt:
        print("\n\nExtracción interrumpida por el usuario")
        if extractor.registros:
            extractor.guardar_resultados()
    except Exception as e:
        print(f"\nError durante la extracción: {e}")

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())