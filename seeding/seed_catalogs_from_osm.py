"""
Script para poblar catálogos SIPI desde casuística OSM

Ejecutar ANTES de la primera sincronización de inmuebles.
Analiza datos de OSM y crea los valores necesarios en las tablas de catálogo.
"""
import asyncio
from typing import Set, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.sessions.sync_session import SessionLocal
from app.db.models.tipologias import (
    TipoInmueble,
    TipoEstadoConservacion,
    TipoDocumento
)


class CatalogSeeder:
    """Poblador de catálogos desde casuística OSM"""
    
    def __init__(self, db: Session):
        self.db = db
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.user_agent = "SIPI-Catalog-Seeder/1.0"
    
    async def seed_all(self, sample_size: int = 1000):
        """
        Poblar todos los catálogos necesarios
        
        Args:
            sample_size: Número de elementos OSM a analizar para extraer valores
        """
        print("🌱 Iniciando población de catálogos desde OSM...")
        print(f"📊 Analizando {sample_size} elementos de muestra\n")
        
        # 1. Obtener muestra de datos OSM
        osm_data = await self._fetch_osm_sample(sample_size)
        elements = osm_data.get("elements", [])
        
        if not elements:
            print("❌ No se pudieron obtener datos de OSM")
            return
        
        print(f"✅ Obtenidos {len(elements)} elementos de OSM\n")
        
        # 2. Analizar y extraer valores únicos
        valores = self._analyze_osm_data(elements)
        
        # 3. Poblar cada catálogo
        await self._seed_tipos_inmueble(valores["tipos"])
        await self._seed_estados_conservacion(valores["estados"])
        await self._seed_tipos_documento(valores["documentos"])
        
        self.db.commit()
        print("\n✨ Población de catálogos completada")
    
    async def _fetch_osm_sample(self, n: int) -> dict:
        """Obtiene muestra de elementos OSM para análisis"""
        import httpx
        
        # Query que obtiene muestra representativa de España
        query = f"""
        [out:json][timeout:60];
        area["ISO3166-1"="ES"]->.es;
        (
          node["amenity"="place_of_worship"]["religion"="christian"](area.es);
          way["amenity"="place_of_worship"]["religion"="christian"](area.es);
          node["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"](area.es);
          way["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"](area.es);
        );
        out tags {n};
        """
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.overpass_url,
                data={"data": query},
                headers={"User-Agent": self.user_agent}
            )
            response.raise_for_status()
            return response.json()
    
    def _analyze_osm_data(self, elements: List[dict]) -> Dict[str, Set[str]]:
        """Analiza elementos OSM y extrae valores únicos para catálogos"""
        valores = {
            "tipos": set(),
            "estados": set(),
            "documentos": set(),
            "materiales": set(),
            "estilos": set()
        }
        
        for element in elements:
            tags = element.get("tags", {})
            
            # Tipos de inmueble
            if building := tags.get("building"):
                valores["tipos"].add(building)
            if pow_type := tags.get("place_of_worship"):
                valores["tipos"].add(pow_type)
            if amenity := tags.get("amenity"):
                if amenity == "place_of_worship":
                    valores["tipos"].add("place_of_worship")
            
            # Estados (inferir desde tags)
            if tags.get("ruins") == "yes" or tags.get("building") == "ruins":
                valores["estados"].add("ruins")
            if tags.get("disused") == "yes":
                valores["estados"].add("disused")
            if tags.get("building:condition"):
                valores["estados"].add(tags.get("building:condition"))
            
            # Tipos de documento (desde tags de multimedia)
            if tags.get("image"):
                valores["documentos"].add("image")
            if tags.get("wikimedia_commons"):
                valores["documentos"].add("wikimedia")
            if any(k.startswith("image:") for k in tags.keys()):
                valores["documentos"].add("additional_images")
            
            # Materiales (para futura referencia)
            if material := tags.get("material"):
                valores["materiales"].add(material)
            if building_material := tags.get("building:material"):
                valores["materiales"].add(building_material)
            
            # Estilos arquitectónicos
            if style := tags.get("architecture:style"):
                valores["estilos"].add(style)
        
        # Reportar hallazgos
        print("📈 Valores únicos encontrados:")
        print(f"  - Tipos de inmueble: {len(valores['tipos'])}")
        print(f"  - Estados: {len(valores['estados'])}")
        print(f"  - Tipos documento: {len(valores['documentos'])}")
        print(f"  - Materiales: {len(valores['materiales'])}")
        print(f"  - Estilos: {len(valores['estilos'])}\n")
        
        return valores
    
    async def _seed_tipos_inmueble(self, tipos_osm: Set[str]):
        """Poblar tabla tipos_inmueble"""
        print("🏛️  Poblando tipos_inmueble...")
        
        # Mapeo de valores OSM a nombres en español
        mapeo = {
            "cathedral": ("Catedral", "Edificio religioso principal de una diócesis"),
            "basilica": ("Basílica", "Iglesia con privilegios especiales"),
            "church": ("Iglesia", "Templo cristiano"),
            "chapel": ("Capilla", "Templo pequeño o dependiente"),
            "monastery": ("Monasterio", "Conjunto religioso de monjes"),
            "convent": ("Convento", "Conjunto religioso de monjas o frailes"),
            "hermitage": ("Ermita", "Santuario o capilla aislada"),
            "wayside_shrine": ("Humilladero", "Pequeño santuario al borde del camino"),
            "cross": ("Cruz", "Cruz monumental o crucero"),
            "wayside_cross": ("Crucero", "Cruz al borde del camino"),
            "lourdes_grotto": ("Gruta", "Gruta de Lourdes u otra advocación"),
            "bell_tower": ("Campanario", "Torre de campanas"),
            "place_of_worship": ("Lugar de culto", "Lugar de culto genérico")
        }
        
        created = 0
        for tipo_osm in tipos_osm:
            if tipo_osm in mapeo:
                nombre, descripcion = mapeo[tipo_osm]
                
                # Verificar si ya existe
                existing = self.db.query(TipoInmueble).filter(
                    func.lower(TipoInmueble.nombre) == nombre.lower()
                ).first()
                
                if not existing:
                    tipo = TipoInmueble(
                        nombre=nombre,
                        descripcion=descripcion
                    )
                    self.db.add(tipo)
                    created += 1
                    print(f"  ✅ Creado: {nombre}")
        
        self.db.flush()
        print(f"  📊 Total creados: {created}\n")
    
    async def _seed_estados_conservacion(self, estados_osm: Set[str]):
        """Poblar tabla estados_conservacion"""
        print("🏗️  Poblando estados_conservacion...")
        
        # Estados estándar + los encontrados en OSM
        estados_standard = [
            ("Excelente", "Estado de conservación excelente"),
            ("Bueno", "Estado de conservación bueno"),
            ("Regular", "Estado de conservación regular"),
            ("Malo", "Estado de conservación malo"),
            ("Ruina", "En estado de ruina"),
            ("Desconocido", "Estado de conservación desconocido")
        ]
        
        # Mapeo de valores OSM
        mapeo_osm = {
            "ruins": ("Ruina", "En estado de ruina (desde OSM)"),
            "good": ("Bueno", "Buen estado (desde OSM)"),
            "poor": ("Malo", "Mal estado (desde OSM)"),
            "disused": ("Desuso", "Edificio en desuso")
        }
        
        created = 0
        
        # Crear estados estándar
        for nombre, descripcion in estados_standard:
            existing = self.db.query(TipoEstadoConservacion).filter(
                func.lower(TipoEstadoConservacion.nombre) == nombre.lower()
            ).first()
            
            if not existing:
                estado = TipoEstadoConservacion(
                    nombre=nombre,
                    descripcion=descripcion
                )
                self.db.add(estado)
                created += 1
                print(f"  ✅ Creado: {nombre}")
        
        # Crear estados desde OSM si no existen ya
        for estado_osm in estados_osm:
            if estado_osm in mapeo_osm:
                nombre, descripcion = mapeo_osm[estado_osm]
                
                existing = self.db.query(TipoEstadoConservacion).filter(
                    func.lower(TipoEstadoConservacion.nombre) == nombre.lower()
                ).first()
                
                if not existing:
                    estado = TipoEstadoConservacion(
                        nombre=nombre,
                        descripcion=descripcion
                    )
                    self.db.add(estado)
                    created += 1
                    print(f"  ✅ Creado: {nombre} (desde OSM)")
        
        self.db.flush()
        print(f"  📊 Total creados: {created}\n")
    
    async def _seed_tipos_documento(self, tipos_osm: Set[str]):
        """Poblar tabla tipos_documento con tipos de multimedia"""
        print("📄 Poblando tipos_documento (multimedia)...")
        
        # Tipos para multimedia desde OSM
        tipos_multimedia = [
            ("Fotografía OSM", "Imagen desde OpenStreetMap"),
            ("Fotografía Wikimedia", "Imagen desde Wikimedia Commons"),
            ("Vista Panorámica 360°", "Panorama 360° (Panoramax/Mapillary)"),
            ("Video Externo", "Video desde URL externa"),
            ("Galería de Imágenes", "Conjunto de imágenes adicionales")
        ]
        
        # Tipos estándar de documentos (si no existen ya)
        tipos_standard = [
            ("Fotografía", "Fotografía del inmueble"),
            ("Plano", "Plano arquitectónico"),
            ("Informe Técnico", "Informe técnico o estudio"),
            ("Certificado", "Certificado oficial"),
            ("Escritura", "Escritura de propiedad"),
            ("BIC Declaración", "Declaración BIC"),
            ("Proyecto", "Proyecto de intervención"),
            ("Memoria", "Memoria descriptiva")
        ]
        
        created = 0
        
        # Crear tipos multimedia
        for nombre, descripcion in tipos_multimedia:
            existing = self.db.query(TipoDocumento).filter(
                func.lower(TipoDocumento.nombre) == nombre.lower()
            ).first()
            
            if not existing:
                tipo = TipoDocumento(
                    nombre=nombre,
                    descripcion=descripcion
                )
                self.db.add(tipo)
                created += 1
                print(f"  ✅ Creado: {nombre}")
        
        # Crear tipos estándar si no existen
        for nombre, descripcion in tipos_standard:
            existing = self.db.query(TipoDocumento).filter(
                func.lower(TipoDocumento.nombre) == nombre.lower()
            ).first()
            
            if not existing:
                tipo = TipoDocumento(
                    nombre=nombre,
                    descripcion=descripcion
                )
                self.db.add(tipo)
                created += 1
                print(f"  ✅ Creado: {nombre}")
        
        self.db.flush()
        print(f"  📊 Total creados: {created}\n")
    
    def print_summary(self):
        """Imprime resumen de catálogos poblados"""
        print("\n" + "="*70)
        print("📊 RESUMEN DE CATÁLOGOS")
        print("="*70)
        
        # Contar registros
        count_tipos = self.db.query(TipoInmueble).count()
        count_estados = self.db.query(TipoEstadoConservacion).count()
        count_docs = self.db.query(TipoDocumento).count()
        
        print(f"\n✅ Tipos de Inmueble: {count_tipos}")
        print(f"✅ Estados de Conservación: {count_estados}")
        print(f"✅ Tipos de Documento: {count_docs}")
        
        # Listar tipos de inmueble
        print("\n📋 Tipos de Inmueble disponibles:")
        tipos = self.db.query(TipoInmueble).order_by(TipoInmueble.nombre).all()
        for tipo in tipos:
            print(f"  • {tipo.nombre}")
        
        print("\n" + "="*70)
        print("✨ Catálogos listos para sincronización de inmuebles")
        print("="*70 + "\n")


async def main():
    """Función principal"""
    db = SessionLocal()
    try:
        seeder = CatalogSeeder(db)
        
        # Poblar catálogos analizando 1000 elementos de muestra
        await seeder.seed_all(sample_size=1000)
        
        # Mostrar resumen
        seeder.print_summary()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║          🌱 POBLACIÓN DE CATÁLOGOS DESDE OSM                 ║
║                                                              ║
║  Este script analiza datos de OSM y crea valores en:        ║
║  • tipos_inmueble                                            ║
║  • estados_conservacion                                      ║
║  • tipos_documento                                           ║
║                                                              ║
║  ⚠️  EJECUTAR ANTES de la primera sincronización             ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())