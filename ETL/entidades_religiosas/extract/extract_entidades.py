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
        
        self.provincias = {
            'P01': 'ÁLAVA', 'P02': 'ALBACETE', 'P03': 'ALICANTE', 'P04': 'ALMERÍA',
            'P05': 'ÁVILA', 'P06': 'BADAJOZ', 'P07': 'BALEARES', 'P08': 'BARCELONA',
            'P09': 'BURGOS', 'P10': 'CÁCERES', 'P11': 'CÁDIZ', 'P12': 'CASTELLON',
            'P13': 'CIUDAD REAL', 'P14': 'CÓRDOBA', 'P15': 'LA CORUÑA', 'P16': 'CUENCA',
            'P17': 'GERONA', 'P18': 'GRANADA', 'P19': 'GUADALAJARA', 'P20': 'GUIPUZCOA',
            'P21': 'HUELVA', 'P22': 'HUESCA', 'P23': 'JAÉN', 'P24': 'LEON',
            'P25': 'LÉRIDA', 'P26': 'LA RIOJA', 'P27': 'LUGO', 'P28': 'MADRID',
            'P29': 'MÁLAGA', 'P30': 'MURCIA', 'P31': 'NAVARRA', 'P32': 'ORENSE',
            'P33': 'ASTURIAS', 'P34': 'PALENCIA', 'P35': 'LAS PALMAS', 'P36': 'PONTEVEDRA',
            'P37': 'SALAMANCA', 'P38': 'S.C. TENERIFE', 'P39': 'CANTABRIA', 'P40': 'SEGOVIA',
            'P41': 'SEVILLA', 'P42': 'SORIA', 'P43': 'TARRAGONA', 'P44': 'TERUEL',
            'P45': 'TOLEDO', 'P46': 'VALENCIA', 'P47': 'VALLADOLID', 'P48': 'VIZCAYA',
            'P49': 'ZAMORA', 'P50': 'ZARAGOZA', 'P51': 'CEUTA', 'P52': 'MELILLA'
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
    
    def procesar_provincia(self, codigo_provincia, nombre_provincia, confesion='CAT'):
        """Procesa una provincia"""
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
                    nuevo_nombre = f"entidades_{codigo_provincia}_{nombre_provincia.replace(' ', '_')}.xls"
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
        """Combina archivos"""
        print(f"\n{'='*60}")
        print(f"Combinando {len(archivos)} archivos...")
        
        dfs = []
        for archivo in archivos:
            try:
                df = pd.read_excel(os.path.join(self.download_dir, archivo))
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

            for i, (codigo, nombre) in enumerate(self.provincias.items(), 1):
                print(f"[{i}/{len(self.provincias)}] ", end="")
                archivo = self.procesar_provincia(codigo, nombre, confesion)
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