from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
import glob

class ScraperEntidadesReligiosas:
    def __init__(self, headless=False):
        self.download_dir = os.getcwd()
        self.headless = headless
        
        # Mapeo código web -> (nombre, codigo_ine)
        # Los códigos INE son los oficiales del Instituto Nacional de Estadística
        self.provincias = {
            'P01': ('ÁLAVA', '01'), 'P02': ('ALBACETE', '02'), 'P03': ('ALICANTE', '03'), 'P04': ('ALMERÍA', '04'),
            'P05': ('ÁVILA', '05'), 'P06': ('BADAJOZ', '06'), 'P07': ('BALEARES', '07'), 'P08': ('BARCELONA', '08'),
            'P09': ('BURGOS', '09'), 'P10': ('CÁCERES', '10'), 'P11': ('CÁDIZ', '11'), 'P12': ('CASTELLON', '12'),
            'P13': ('CIUDAD REAL', '13'), 'P14': ('CÓRDOBA', '14'), 'P15': ('LA CORUÑA', '15'), 'P16': ('CUENCA', '16'),
            'P17': ('GERONA', '17'), 'P18': ('GRANADA', '18'), 'P19': ('GUADALAJARA', '19'), 'P20': ('GUIPUZCOA', '20'),
            'P21': ('HUELVA', '21'), 'P22': ('HUESCA', '22'), 'P23': ('JAÉN', '23'), 'P24': ('LEON', '24'),
            'P25': ('LÉRIDA', '25'), 'P26': ('LA RIOJA', '26'), 'P27': ('LUGO', '27'), 'P28': ('MADRID', '28'),
            'P29': ('MÁLAGA', '29'), 'P30': ('MURCIA', '30'), 'P31': ('NAVARRA', '31'), 'P32': ('ORENSE', '32'),
            'P33': ('ASTURIAS', '33'), 'P34': ('PALENCIA', '34'), 'P35': ('LAS PALMAS', '35'), 'P36': ('PONTEVEDRA', '36'),
            'P37': ('SALAMANCA', '37'), 'P38': ('S.C. TENERIFE', '38'), 'P39': ('CANTABRIA', '39'), 'P40': ('SEGOVIA', '40'),
            'P41': ('SEVILLA', '41'), 'P42': ('SORIA', '42'), 'P43': ('TARRAGONA', '43'), 'P44': ('TERUEL', '44'),
            'P45': ('TOLEDO', '45'), 'P46': ('VALENCIA', '46'), 'P47': ('VALLADOLID', '47'), 'P48': ('VIZCAYA', '48'),
            'P49': ('ZAMORA', '49'), 'P50': ('ZARAGOZA', '50'), 'P51': ('CEUTA', '51'), 'P52': ('MELILLA', '52')
        }
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)
    
    def procesar_provincia(self, codigo_provincia, datos_provincia, confesion='CAT'):
        """Procesa una provincia

        Args:
            codigo_provincia: Código web (P01, P02, etc.)
            datos_provincia: Tupla (nombre_provincia, codigo_ine)
            confesion: Código de confesión religiosa
        """
        nombre_provincia, codigo_ine = datos_provincia
        try:
            self.driver.get("https://maper.mjusticia.gob.es/Maper/buscarRER.action")
            self.wait.until(EC.presence_of_element_located((By.ID, "formBusqRER")))

            # Mismo código para todas las provincias
            script = f"""
            var select = document.getElementById('selectConfesiones');
            if (!select) return 'ERROR: Select confesión no encontrado';

            for (var i = 0; i < select.options.length; i++) {{
                select.options[i].selected = (select.options[i].value === '{confesion}');
            }}

            var event = new Event('change', {{ bubbles: true }});
            select.dispatchEvent(event);

            var selectProv = document.getElementById('formBusqRER_filtro_codigosProvincia');
            if (!selectProv) return 'ERROR: Select provincia no encontrado';

            for (var i = 0; i < selectProv.options.length; i++) {{
                selectProv.options[i].selected = false;
            }}

            for (var i = 0; i < selectProv.options.length; i++) {{
                if (selectProv.options[i].value === '{codigo_provincia}') {{
                    selectProv.options[i].selected = true;
                    break;
                }}
            }}

            var event2 = new Event('change', {{ bubbles: true }});
            selectProv.dispatchEvent(event2);

            return 'OK_SELECCIONADO';
            """

            resultado = self.driver.execute_script(script)
            if resultado != 'OK_SELECCIONADO':
                print(f"✗ {nombre_provincia} (error JS)")
                return None

            time.sleep(1)

            # Submit
            self.driver.execute_script("""
                document.getElementById('formBusqRER').submit();
            """)

            # Esperar tabla (reemplaza time.sleep(10))
            try:
                tabla = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "tabla_datos"))
                )
                filas = tabla.find_elements(By.CSS_SELECTOR, "tbody tr")
                if len(filas) == 0:
                    print(f"- {nombre_provincia} (sin resultados)")
                    return None
            except:
                print(f"✗ {nombre_provincia} (sin tabla)")
                return None

            # Buscar botón
            boton = None
            try:
                boton = self.driver.find_element(By.ID, "submitExcel")
            except:
                try:
                    boton = self.driver.find_element(By.XPATH, "//a[contains(@href, 'listadoInformeEntidades')]")
                except:
                    print(f"✗ {nombre_provincia} (sin botón)")
                    return None
            
            # Descargar
            archivos_antes = set(f for f in os.listdir(self.download_dir) if f.endswith(('.xls', '.xlsx')))

            self.driver.execute_script("arguments[0].click();", boton)

            # Loop de descarga optimizado (pausas más cortas)
            for _ in range(60):
                time.sleep(0.5)
                archivos_nuevos = set(f for f in os.listdir(self.download_dir) if f.endswith(('.xls', '.xlsx'))) - archivos_antes
                excel = [f for f in archivos_nuevos if not f.endswith('.crdownload')]
                
                if excel:
                    archivo = excel[0]
                    nuevo_nombre = f"entidades_{codigo_ine}_{nombre_provincia.replace(' ', '_')}.xls"
                    ruta_nueva = os.path.join(self.download_dir, nuevo_nombre)
                    
                    # ELIMINAR SI YA EXISTE
                    if os.path.exists(ruta_nueva):
                        os.remove(ruta_nueva)
                    
                    os.rename(os.path.join(self.download_dir, archivo), ruta_nueva)
                    
                    print(f"✓ {nombre_provincia}")
                    return nuevo_nombre
            
            print(f"✗ {nombre_provincia} (timeout descarga)")
            return None
            
        except Exception as e:
            print(f"✗ {nombre_provincia} (excepción: {e})")
            return None
    
    def combinar_excels(self, archivos):
        """Combina archivos y añade codigo_ine_provincia"""
        print(f"\n{'='*60}")
        print(f"Combinando {len(archivos)} archivos...")

        dfs = []
        for archivo in archivos:
            try:
                df = pd.read_excel(os.path.join(self.download_dir, archivo))
                # Extraer codigo_ine del nombre de archivo: entidades_{codigo_ine}_{nombre}.xls
                partes = archivo.replace('.xls', '').split('_')
                if len(partes) >= 2:
                    codigo_ine = partes[1]  # El segundo elemento es el codigo_ine
                    df['codigo_ine_provincia'] = codigo_ine
                dfs.append(df)
            except Exception as e:
                print(f"  ✗ {archivo}: {e}")
        
        if not dfs:
            return None
        
        df_completo = pd.concat(dfs, ignore_index=True)
        df_completo = df_completo.drop_duplicates()
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_filename = f"entidades_catolicas_completo_{timestamp}.csv"
        df_completo.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ CSV: {csv_filename}")
        print(f"✓ Registros: {len(df_completo)}")
        
        return csv_filename
    
    def _inicializar_sesion(self, confesion='CAT'):
        """Carga inicial para sincronizar la página antes del bucle"""
        print("Inicializando sesión...")
        self.driver.get("https://maper.mjusticia.gob.es/Maper/buscarRER.action")
        self.wait.until(EC.presence_of_element_located((By.ID, "formBusqRER")))

        # Interacción dummy: seleccionar confesión para que el JS se inicialice
        self.driver.execute_script(f"""
            var select = document.getElementById('selectConfesiones');
            if (select) {{
                for (var i = 0; i < select.options.length; i++) {{
                    select.options[i].selected = (select.options[i].value === '{confesion}');
                }}
                select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        time.sleep(1)
        print("Sesión inicializada\n")

    def ejecutar(self, confesion='CAT'):
        """Ejecuta"""
        print(f"Extrayendo entidades católicas\n")

        archivos = []
        inicio = time.time()

        try:
            self._inicializar_sesion(confesion)

            for i, (codigo, datos) in enumerate(self.provincias.items(), 1):
                nombre, codigo_ine = datos
                print(f"[{i}/{len(self.provincias)}] ", end="")
                archivo = self.procesar_provincia(codigo, datos, confesion)
                if archivo:
                    archivos.append(archivo)
            
            tiempo = time.time() - inicio
            
            print(f"\n{'='*60}")
            print(f"Tiempo: {tiempo/60:.1f}min")
            print(f"Archivos: {len(archivos)}")
            
            if archivos:
                self.combinar_excels(archivos)
        
        finally:
            self.driver.quit()

if __name__ == "__main__":
    scraper = ScraperEntidadesReligiosas(headless=True)
    scraper.ejecutar()