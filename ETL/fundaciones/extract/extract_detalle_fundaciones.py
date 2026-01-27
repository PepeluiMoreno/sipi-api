"""
EXTRACT_DETALLE_FUNDACIONES.py - Versión simplificada con mejor progreso
"""

import pandas as pd
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from multiprocessing import Process, Queue, Manager
import os

from playwright.sync_api import sync_playwright


def worker_extractor(worker_id: int, enlaces_asignados: List[Dict], resultado_queue: Queue):
    """Worker que procesa un grupo de enlaces"""
    try:
        # Inicializar Playwright en este proceso
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(15000)
        
        resultados = []
        total = len(enlaces_asignados)
        procesadas = 0
        ultimo_reporte = 0
        
        # Informar inicio
        resultado_queue.put(('inicio', worker_id, total))
        
        for idx, enlace in enumerate(enlaces_asignados):
            try:
                # Extraer detalle
                if enlace.get('enlace_detalle'):
                    page.goto(enlace['enlace_detalle'], wait_until="domcontentloaded", timeout=10000)
                    time.sleep(0.5)
                    
                    datos = enlace.copy()
                    
                    # Extraer campos básicos
                    campos = {}
                    mapeo = {
                        'NIF': 'nif', 'Nº de registro': 'numero_registro',
                        'Fecha de extinción': 'fecha_extincion', 'Fecha de constitución': 'fecha_constitucion',
                        'Fecha de inscripción': 'fecha_inscripcion', 'Domicilio': 'domicilio',
                        'Localidad': 'localidad', 'Código postal': 'codigo_postal',
                        'Provincia': 'provincia_detalle', 'Teléfono': 'telefono',
                        'Fax': 'fax', 'Correo electrónico': 'email', 'Web': 'web'
                    }
                    
                    elementos_li = page.query_selector_all("//div[contains(@class, 'detalleFundacion')]//li")
                    for li in elementos_li:
                        texto = li.inner_text().strip()
                        if ':' in texto:
                            etiqueta, valor = texto.split(':', 1)
                            etiqueta = etiqueta.strip()
                            if etiqueta in mapeo:
                                campos[mapeo[etiqueta]] = valor.strip()
                    
                    datos.update(campos)
                    datos['fecha_extraccion'] = datetime.now().isoformat()
                    resultados.append(datos)
                
                procesadas += 1
                
                # Reportar progreso con mayor frecuencia (cada 5 fundaciones)
                # O cada 2 segundos si hay menos de 5 procesadas
                ahora = time.time()
                if (procesadas % 5 == 0) or (ahora - ultimo_reporte > 2 and procesadas > ultimo_reporte):
                    porcentaje = int((procesadas / total) * 100)
                    resultado_queue.put(('progreso', worker_id, procesadas, total, porcentaje))
                    ultimo_reporte = ahora
                
                time.sleep(0.3)
                
            except Exception as e:
                # Continuar con siguiente si falla una
                continue
        
        # Reporte final
        porcentaje = int((procesadas / total) * 100)
        resultado_queue.put(('progreso', worker_id, procesadas, total, porcentaje))
        
        # Guardar resultados temporales
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_temp = f"detalles_worker_{worker_id}_{timestamp}.csv"
        
        if resultados:
            df = pd.DataFrame(resultados)
            df.to_csv(csv_temp, index=False, encoding='utf-8-sig')
            resultado_queue.put(('completado', worker_id, csv_temp, procesadas, total))
        else:
            resultado_queue.put(('fallo', worker_id, "", procesadas, total))
        
        # Cerrar recursos
        page.close()
        context.close()
        browser.close()
        playwright.stop()
        
    except Exception as e:
        resultado_queue.put(('error', worker_id, str(e)))


class ProcesadorDetalles:
    
    def __init__(self, num_workers=5):
        self.num_workers = num_workers
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_final = f"fundaciones_completas_{self.timestamp}.csv"
    
    def encontrar_csv_mas_reciente(self):
        archivos = list(Path(".").glob("enlaces_fundaciones_*.csv"))
        if not archivos:
            return None
        archivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return str(archivos[0])
    
    def mostrar_progreso(self, estado_workers: dict):
        """Muestra el progreso de todos los workers"""
        lineas = []
        for worker_id in sorted(estado_workers.keys()):
            estado = estado_workers[worker_id]
            if estado.get('completado'):
                procesadas = estado.get('procesadas', 0)
                total = estado.get('total', 0)
                lineas.append(f"W{worker_id}: ✅ ({procesadas}/{total})")
            elif estado.get('fallo'):
                procesadas = estado.get('procesadas', 0)
                total = estado.get('total', 0)
                lineas.append(f"W{worker_id}: ❌ ({procesadas}/{total})")
            elif 'procesadas' in estado:
                procesadas = estado.get('procesadas', 0)
                total = estado.get('total', 0)
                porcentaje = estado.get('porcentaje', 0)
                lineas.append(f"W{worker_id}: {porcentaje}% ({procesadas}/{total})")
            else:
                lineas.append(f"W{worker_id}: 0%")
        
        return " | ".join(lineas)
    
    def formato_tiempo(self, segundos: float) -> str:
        """Convierte segundos a formato minutos:segundos"""
        minutos = int(segundos // 60)
        segs = int(segundos % 60)
        return f"{minutos}:{segs:02d}"
    
    def procesar(self) -> str:
        # Encontrar archivo
        archivo_enlaces = self.encontrar_csv_mas_reciente()
        if not archivo_enlaces:
            print("No se encontró archivo de enlaces")
            return ""
        
        print(f"Usando archivo: {archivo_enlaces}")
        
        # Leer enlaces
        df_enlaces = pd.read_csv(archivo_enlaces, encoding='utf-8-sig')
        total_enlaces = len(df_enlaces)
        
        if total_enlaces == 0:
            print("Archivo vacío")
            return ""
        
        print(f"{total_enlaces} fundaciones para procesar")
        print(f"{self.num_workers} workers")
        
        # Dividir enlaces
        enlaces_por_worker = total_enlaces // self.num_workers
        enlaces_lista = df_enlaces.to_dict('records')
        
        grupos = []
        inicio = 0
        
        # Mostrar reparto de fundaciones
        reparto_info = []
        for i in range(self.num_workers):
            fin = inicio + enlaces_por_worker + (1 if i < total_enlaces % self.num_workers else 0)
            grupo = enlaces_lista[inicio:fin]
            if grupo:
                grupos.append(grupo)
                reparto_info.append(f"Worker {i+1}: {len(grupo)} fundaciones")
            inicio = fin
        
        print("\nReparto:")
        for info in reparto_info:
            print(f"  {info}")
        
        # Iniciar workers
        print("\nIniciando workers...")
        manager = Manager()
        resultado_queue = manager.Queue()
        procesos = []
        
        for i, grupo in enumerate(grupos):
            proceso = Process(
                target=worker_extractor,
                args=(i+1, grupo, resultado_queue)
            )
            proceso.start()
            procesos.append(proceso)
            time.sleep(0.3)
        
        print(f"\n{len(procesos)} workers en ejecución")
        
        # Estado de workers
        estado_workers = {}
        csv_temporales = []
        tiempo_inicio = time.time()
        ultima_actualizacion = tiempo_inicio
        
        # Variables para control de actualización
        actualizaciones_por_segundo = 2  # Actualizar 2 veces por segundo
        intervalo_actualizacion = 1.0 / actualizaciones_por_segundo
        
        while len(csv_temporales) < len(procesos):
            # Revisar mensajes de workers frecuentemente
            mensajes_procesados = 0
            while not resultado_queue.empty() and mensajes_procesados < 20:  # Límite por iteración
                try:
                    tipo, worker_id, *datos = resultado_queue.get_nowait()
                    
                    if tipo == 'inicio':
                        total = datos[0]
                        estado_workers[worker_id] = {'total': total, 'procesadas': 0}
                    
                    elif tipo == 'progreso':
                        procesadas, total, porcentaje = datos
                        estado_workers[worker_id] = {
                            'procesadas': procesadas,
                            'total': total,
                            'porcentaje': porcentaje
                        }
                    
                    elif tipo == 'completado':
                        csv_path, procesadas, total = datos
                        csv_temporales.append(csv_path)
                        estado_workers[worker_id] = {'completado': True, 'procesadas': procesadas, 'total': total}
                        tiempo_trans = time.time() - tiempo_inicio
                        print(f"\n✓ Worker {worker_id} completado: {procesadas}/{total} registros ({self.formato_tiempo(tiempo_trans)})")
                    
                    elif tipo == 'fallo':
                        _, procesadas, total = datos
                        estado_workers[worker_id] = {'fallo': True, 'procesadas': procesadas, 'total': total}
                        print(f"\n✗ Worker {worker_id} falló: {procesadas}/{total} registros")
                    
                    elif tipo == 'error':
                        error_msg = datos[0]
                        estado_workers[worker_id] = {'error': True}
                        print(f"\n⚠ Worker {worker_id} error: {error_msg[:80]}")
                        
                    mensajes_procesados += 1
                except:
                    break
            
            # Mostrar progreso actualizado con mayor frecuencia
            ahora = time.time()
            if ahora - ultima_actualizacion >= intervalo_actualizacion:
                progreso_texto = self.mostrar_progreso(estado_workers)
                tiempo_trans = ahora - tiempo_inicio
                completados = sum(1 for w in estado_workers.values() if w.get('completado') or w.get('fallo'))
                
                # Calcular totales
                total_procesadas = sum(w.get('procesadas', 0) for w in estado_workers.values())
                total_asignadas = sum(w.get('total', 0) for w in estado_workers.values())
                
                if total_asignadas > 0:
                    porcentaje_total = int((total_procesadas / total_asignadas) * 100)
                    info_total = f"Total: {total_procesadas}/{total_asignadas} ({porcentaje_total}%)"
                else:
                    info_total = "Total: 0/0 (0%)"
                
                print(f"\r{progreso_texto} | {info_total} | Tiempo: {self.formato_tiempo(tiempo_trans)}", end="", flush=True)
                ultima_actualizacion = ahora
            
            time.sleep(0.05)  # Sleep más corto para mayor responsividad
            
            # Timeout
            if (ahora - tiempo_inicio) > 7200:  # 2 horas
                print("\n\n⚠ Timeout de 2 horas alcanzado")
                break
        
        print()  # Nueva línea
        
        # Esperar procesos
        for proceso in procesos:
            proceso.join(timeout=300)
        
        # Combinar resultados
        if csv_temporales:
            print(f"\nCombinando {len(csv_temporales)} archivos...")
            dataframes = []
            
            for csv_path in csv_temporales:
                if Path(csv_path).exists():
                    try:
                        df = pd.read_csv(csv_path, encoding='utf-8-sig')
                        dataframes.append(df)
                        print(f"  Worker {csv_path.split('_')[2]}: {len(df)} registros")
                    except Exception as e:
                        print(f"  Error leyendo {csv_path}: {e}")
            
            if dataframes:
                df_final = pd.concat(dataframes, ignore_index=True)
                
                # Eliminar duplicados
                if 'codigo_registro' in df_final.columns:
                    antes = len(df_final)
                    df_final = df_final.drop_duplicates(subset=['codigo_registro'], keep='first')
                    despues = len(df_final)
                    if antes != despues:
                        print(f"  Eliminados {antes - despues} duplicados")
                
                df_final.to_csv(self.output_final, index=False, encoding='utf-8-sig')
                
                # Limpiar temporales
                for csv_path in csv_temporales:
                    try:
                        Path(csv_path).unlink()
                    except:
                        pass
                
                tiempo_total = time.time() - tiempo_inicio
                print(f"\n✅ Proceso completado")
                print(f"📄 Archivo: {self.output_final}")
                print(f"📊 Registros: {len(df_final)}")
                print(f"⏱️  Tiempo total: {self.formato_tiempo(tiempo_total)}")
                
                if 'nif' in df_final.columns:
                    print(f"🔢 Con NIF: {df_final['nif'].notna().sum()}")
                
                return self.output_final
        
        return ""


if __name__ == "__main__":
    procesador = ProcesadorDetalles(num_workers=5)
    archivo_final = procesador.procesar()
    
    if archivo_final:
        print(f"\n🎉 Extracción completada: {archivo_final}")
    else:
        print("\n💥 Extracción falló")