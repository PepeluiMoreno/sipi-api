import pandas as pd
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

sys.path.append('..')
from common.ine_constants import NOMBRES_PROVINCIAS

from playwright.sync_api import sync_playwright


class ColectorEnlaces:
    
    def __init__(self, headless=True):
        self.headless = headless
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archivo_enlaces = f"enlaces_fundaciones_{self.timestamp}.csv"
        self.provincias = NOMBRES_PROVINCIAS
    
    def iniciar_navegador(self):
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.set_default_timeout(8000)
            return True
        except:
            return False
    
    def cerrar_navegador(self):
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except:
            pass
    
    def buscar_enlaces_provincia(self, codigo_ine: str, nombre_provincia: str) -> List[Dict]:
        enlaces = []
        try:
            self.page.goto(
                "https://fundosbuscador.mjusticia.gob.es/fundosbuscador/cargaBuscador.action?lang=es_es",
                wait_until="domcontentloaded",
                timeout=5000
            )
            time.sleep(0.5)
            
            codigo_web = codigo_ine.lstrip('0')
            
            try:
                self.page.select_option("select[name='filtro.provincia']", codigo_web)
            except:
                self.page.select_option("#provincias", codigo_web)
            
            time.sleep(0.5)
            
            try:
                self.page.click("input[type='submit'][value*='Buscar']")
            except:
                self.page.evaluate("document.querySelector('form').submit()")
            
            time.sleep(1.5)
            
            tabla = self.page.query_selector(".tabla_datos")
            if tabla:
                filas = tabla.query_selector_all("tbody tr")
                
                for fila in filas:
                    try:
                        celdas = fila.query_selector_all("td")
                        if len(celdas) >= 3:
                            enlace_elem = celdas[0].query_selector("a")
                            nombre = enlace_elem.inner_text().strip() if enlace_elem else ""
                            href = enlace_elem.get_attribute("href") if enlace_elem else ""
                            
                            if href and href.startswith("/"):
                                href = "https://fundosbuscador.mjusticia.gob.es" + href
                            
                            codigo_registro = None
                            if href:
                                match = re.search(r'idFundacion=(\d+)', href)
                                if match:
                                    codigo_registro = match.group(1)
                            
                            enlaces.append({
                                'codigo_ine_provincia': codigo_ine,
                                'nombre_provincia': nombre_provincia,
                                'nombre_fundacion': nombre,
                                'enlace_detalle': href,
                                'codigo_registro': codigo_registro,
                                'timestamp': datetime.now().isoformat()
                            })
                    except:
                        continue
                
                print(f"[{codigo_ine}] {nombre_provincia}: {len(enlaces)}")
            
            return enlaces
            
        except Exception:
            print(f"[{codigo_ine}] {nombre_provincia}: Error")
            return []
    
    def ejecutar(self) -> str:
        inicio = time.time()
        todos_enlaces = []
        total_provincias = len(self.provincias)
        
        try:
            if not self.iniciar_navegador():
                return ""
            
            print(f"\nColector iniciado - {total_provincias} provincias")
            
            for i, (codigo_ine, nombre) in enumerate(self.provincias.items(), 1):
                print(f"[{i:2d}/52] ", end="")
                enlaces = self.buscar_enlaces_provincia(codigo_ine, nombre)
                todos_enlaces.extend(enlaces)
                
                if i < total_provincias:
                    time.sleep(0.3)
            
            if todos_enlaces:
                df = pd.DataFrame(todos_enlaces)
                df.to_csv(self.archivo_enlaces, index=False, encoding='utf-8-sig')
                
                tiempo_total = time.time() - inicio
                
                print(f"\nColector completado")
                print(f"Tiempo: {tiempo_total/60:.1f} minutos")
                print(f"Total: {len(todos_enlaces)} fundaciones")
                print(f"Archivo: {self.archivo_enlaces}")
                
                top10 = df['nombre_provincia'].value_counts().head(10)
                for provincia, count in top10.items():
                    print(f"{provincia}: {count}")
                
                return self.archivo_enlaces
            else:
                print("No se encontraron fundaciones")
                return ""
                
        except Exception as e:
            print(f"Error: {e}")
            return ""
        finally:
            self.cerrar_navegador()


if __name__ == "__main__":
    colector = ColectorEnlaces(headless=True)
    archivo = colector.ejecutar()
    
    if archivo:
        print(f"\nProceso completado: {archivo}")
    else:
        print("\nProceso falló")