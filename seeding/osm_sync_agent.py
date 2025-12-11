"""
Agente de sincronización OSM para SIPI 
- Extrae iglesias católicas/cristianas desde OpenStreetMap
- Crea/actualiza inmuebles y extensiones OSM en la base de datos
- Soporta áreas completas (España) o regiones específicas (bbox/provincia)
- Implementa lógica avanzada de mapeo, QA y control de cambios
- Uso de consultas Overpass QL optimizadas para máxima cobertura
- Manejo de errores, logging y estadísticas detalladas  """


import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.db.models import (
    Inmueble, 
    InmuebleOSMExt,
    TipoInmueble,
    Provincia,
    Municipio
)


class OSMChurchSyncAgent:
    """Agente para sincronizar iglesias desde OpenStreetMap"""
    
    def __init__(self, db: Session):
        self.db = db
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.user_agent = "SIPI-Heritage-System/1.0"
        
    async def sync_churches(
        self, 
        bbox: Optional[Tuple[float, float, float, float]] = None,
        provincia_nombre: Optional[str] = None,
        use_spain_area: bool = False,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Sincroniza iglesias desde OSM
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            provincia_nombre: Nombre de provincia para filtrar
            use_spain_area: Si True, usa area ISO de España (ignora bbox y provincia)
            dry_run: Si True, solo simula sin guardar cambios
            
        Returns:
            Diccionario con estadísticas de la sincronización
        """
        print(f"🔄 Iniciando sincronización OSM...")
        
        # Determinar modo de query
        if use_spain_area:
            print("📍 Modo: España completa (área ISO)")
            query_mode = "spain_area"
        elif provincia_nombre and not bbox:
            bbox = await self._get_provincia_bbox(provincia_nombre)
            if not bbox:
                print(f"❌ No se pudo obtener bbox para provincia: {provincia_nombre}")
                return {"error": "provincia_not_found"}
            print(f"📍 Provincia: {provincia_nombre}")
            query_mode = "bbox"
        elif bbox:
            print(f"📍 Área personalizada (bbox)")
            query_mode = "bbox"
        else:
            # Por defecto, usar España completa
            use_spain_area = True
            query_mode = "spain_area"
            print("📍 Modo por defecto: España completa (área ISO)")
        
        # 1. Extraer datos de OSM
        osm_data = await self.fetch_churches(bbox=bbox, use_spain_area=use_spain_area)
        elements = osm_data.get("elements", [])
        
        print(f"✅ Encontrados {len(elements)} elementos en OSM")
        
        # 2. Procesar cada elemento
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for i, element in enumerate(elements, 1):
            try:
                result = await self._process_osm_element(element, dry_run)
                stats[result] += 1
                
                # Progreso cada 100 elementos
                if i % 100 == 0:
                    print(f"⏳ Procesados {i}/{len(elements)} elementos...")
                
                # Commit cada 50 elementos para evitar transacciones muy largas
                if not dry_run and (stats["created"] + stats["updated"]) % 50 == 0:
                    self.db.commit()
                    print(f"💾 Checkpoint: {stats}")
                    
            except Exception as e:
                print(f"❌ Error procesando elemento {element.get('id')}: {e}")
                stats["errors"] += 1
                continue
        
        # Commit final
        if not dry_run:
            self.db.commit()
        
        print(f"""
        ✨ Sincronización completada:
        - Creados: {stats['created']}
        - Actualizados: {stats['updated']}
        - Sin cambios: {stats['skipped']}
        - Errores: {stats['errors']}
        """)
        
        return stats
    
    async def fetch_churches(
        self, 
        bbox: Optional[Tuple[float, float, float, float]] = None,
        use_spain_area: bool = False
    ) -> dict:
        """
        Consulta Overpass API para obtener edificios religiosos
        
        Args:
            bbox: Bounding box opcional
            use_spain_area: Si True, usa área ISO de España completa
        """
        query = self._build_overpass_query(bbox=bbox, use_spain_area=use_spain_area)
        
        # Timeout más largo para consultas de España completa
        timeout = 1860.0 if use_spain_area else 180.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.overpass_url,
                data={"data": query},
                headers={"User-Agent": self.user_agent}
            )
            response.raise_for_status()
            return response.json()
    
    def _build_overpass_query(
        self, 
        bbox: Optional[Tuple[float, float, float, float]] = None,
        use_spain_area: bool = False
    ) -> str:
        """
        Construye query Overpass QL optimizada para edificios religiosos católicos/cristianos
        
        5 criterios progresivos para máxima cobertura
        """
        if use_spain_area:
            # Query para España completa usando área ISO
            return """
            [out:json][timeout:1800];
            area["ISO3166-1"="ES"]->.es;
            (
              // Criterio 1: amenity=place_of_worship + religion=christian + denomination=catholic
              node["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"](area.es);
              way ["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"](area.es);
              rel ["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"](area.es);

              // Criterio 2: building=* (tipos específicos) + denomination=catholic
              node["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"](area.es);
              way ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"](area.es);
              rel ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"](area.es);

              // Criterio 3: amenity=place_of_worship + religion=christian (sin denominación específica)
              node["amenity"="place_of_worship"]["religion"="christian"][!"denomination"](area.es);
              way ["amenity"="place_of_worship"]["religion"="christian"][!"denomination"](area.es);
              rel ["amenity"="place_of_worship"]["religion"="christian"][!"denomination"](area.es);

              // Criterio 4: building=* (tipos específicos) + religion=christian (sin denominación específica)
              node["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"](area.es);
              way ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"](area.es);
              rel ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"](area.es);

              // Criterio 5: place_of_worship=* (elementos pequeños) + religion=christian
              node["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"](area.es);
              way ["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"](area.es);
              rel ["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"](area.es);
            );
            out tags center qt;
            """
        else:
            # Query para área específica (bbox)
            if not bbox:
                raise ValueError("Se requiere bbox cuando use_spain_area=False")
            
            min_lat, min_lon, max_lat, max_lon = bbox
            return f"""
            [out:json][timeout:180];
            (
              // Criterio 1: amenity=place_of_worship + religion=christian + denomination=catholic
              node["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});
              way ["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});
              rel ["amenity"="place_of_worship"]["religion"="christian"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});

              // Criterio 2: building=* (tipos específicos) + denomination=catholic
              node["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});
              way ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});
              rel ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["denomination"="catholic"]({min_lat},{min_lon},{max_lat},{max_lon});

              // Criterio 3: amenity=place_of_worship + religion=christian (sin denominación)
              node["amenity"="place_of_worship"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});
              way ["amenity"="place_of_worship"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});
              rel ["amenity"="place_of_worship"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});

              // Criterio 4: building=* (tipos específicos) + religion=christian (sin denominación)
              node["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});
              way ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});
              rel ["building"~"^(church|cathedral|chapel|monastery|convent|hermitage|basilica)$"]["religion"="christian"][!"denomination"]({min_lat},{min_lon},{max_lat},{max_lon});

              // Criterio 5: place_of_worship=* (elementos pequeños) + religion=christian
              node["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"]({min_lat},{min_lon},{max_lat},{max_lon});
              way ["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"]({min_lat},{min_lon},{max_lat},{max_lon});
              rel ["place_of_worship"~"^(cross|wayside_shrine|lourdes_grotto)$"]["religion"="christian"]({min_lat},{min_lon},{max_lat},{max_lon});
            );
            out tags center qt;
            """
    
    async def _process_osm_element(self, element: dict, dry_run: bool = False) -> str:
        """
        Procesa un elemento OSM individual
        
        Returns:
            'created', 'updated', o 'skipped'
        """
        osm_id = f"{element['type']}/{element['id']}"
        
        # Buscar extensión OSM existente
        existing_ext = self.db.query(InmuebleOSMExt).filter(
            InmuebleOSMExt.osm_id == osm_id
        ).first()
        
        if existing_ext:
            # Verificar si necesita actualización
            if self._should_update(existing_ext, element):
                if not dry_run:
                    self._update_osm_extension(existing_ext, element)
                    self._update_inmueble_from_osm(existing_ext.inmueble, element)
                return "updated"
            else:
                return "skipped"
        else:
            # Crear nuevo inmueble + extensión
            if not dry_run:
                inmueble = self._create_inmueble_from_osm(element)
                self.db.add(inmueble)
                self.db.flush()  # Obtener ID del inmueble
                
                osm_ext = self._create_osm_extension(inmueble.id, element)
                self.db.add(osm_ext)
            
            return "created"
    
    def _create_inmueble_from_osm(self, element: dict) -> Inmueble:
        """Crea un nuevo Inmueble desde datos OSM"""
        tags = element.get("tags", {})
        lat, lon = self._get_coordinates(element)
        
        return Inmueble(
            nombre=tags.get("name", "Sin nombre"),
            descripcion=self._build_description(tags),
            direccion=self._build_full_address(tags),
            latitud=lat,
            longitud=lon,
            provincia_id=self._resolve_provincia(lat, lon),
            Municipio_id=self._resolve_Municipio(lat, lon),
            tipo_inmueble_id=self._map_tipo_inmueble(tags),
            es_bic=self._is_bic(tags),
            es_ruina=self._is_ruina(tags)
        )
    
    def _create_osm_extension(self, inmueble_id: str, element: dict) -> InmuebleOSMExt:
        """Crea extensión OSM completa con todos los campos del modelo"""
        tags = element.get("tags", {})
        lat, lon = self._get_coordinates(element)
        
        # Crear geometría PostGIS
        geom = None
        if lat and lon:
            point = Point(lon, lat)  # PostGIS usa (lon, lat)
            geom = from_shape(point, srid=4326)
        
        # QA flags
        qa_flags = self._generate_qa_flags(element, tags)
        
        # Source refs
        source_refs = self._extract_source_refs(tags)
        
        return InmuebleOSMExt(
            inmueble_id=inmueble_id,
            
            # Identificadores OSM
            osm_id=f"{element['type']}/{element['id']}",
            osm_type=element['type'],
            version=element.get('version'),
            
            # Campos extraídos para consultas rápidas
            name=tags.get("name"),
            inferred_type=self._infer_type(tags),
            denomination=tags.get("denomination"),
            diocese=tags.get("diocese"),
            operator=tags.get("operator"),
            
            # Geometría
            geom=geom,
            
            # Datos patrimoniales
            heritage_status=tags.get("heritage") or tags.get("heritage:status"),
            historic=tags.get("historic"),
            ruins=self._is_ruina(tags),
            has_polygon=element['type'] in ['way', 'relation'],
            
            # Dirección desglosada
            address_street=tags.get("addr:street"),
            address_city=tags.get("addr:city"),
            address_postcode=tags.get("addr:postcode"),
            
            # Control de sincronización
            source_updated_at=self._parse_osm_timestamp(element.get('timestamp')),
            
            # Datos completos JSONB
            tags=tags,
            raw=element,
            
            # QA y referencias
            qa_flags=qa_flags,
            source_refs=source_refs
        )
    
    def _update_osm_extension(self, ext: InmuebleOSMExt, element: dict):
        """Actualiza extensión OSM existente con todos los campos"""
        tags = element.get("tags", {})
        lat, lon = self._get_coordinates(element)
        
        # Actualizar identificadores
        ext.version = element.get('version')
        ext.osm_type = element['type']
        
        # Actualizar campos extraídos
        ext.name = tags.get("name")
        ext.inferred_type = self._infer_type(tags)
        ext.denomination = tags.get("denomination")
        ext.diocese = tags.get("diocese")
        ext.operator = tags.get("operator")
        
        # Actualizar geometría
        if lat and lon:
            point = Point(lon, lat)
            ext.geom = from_shape(point, srid=4326)
        
        # Actualizar datos patrimoniales
        ext.heritage_status = tags.get("heritage") or tags.get("heritage:status")
        ext.historic = tags.get("historic")
        ext.ruins = self._is_ruina(tags)
        ext.has_polygon = element['type'] in ['way', 'relation']
        
        # Actualizar dirección
        ext.address_street = tags.get("addr:street")
        ext.address_city = tags.get("addr:city")
        ext.address_postcode = tags.get("addr:postcode")
        
        # Actualizar control
        ext.source_updated_at = self._parse_osm_timestamp(element.get('timestamp'))
        
        # Actualizar JSONB
        ext.tags = tags
        ext.raw = element
        
        # Actualizar QA y referencias
        ext.qa_flags = self._generate_qa_flags(element, tags)
        ext.source_refs = self._extract_source_refs(tags)
        
        ext.updated_at = datetime.utcnow()
    
    def _update_inmueble_from_osm(self, inmueble: Inmueble, element: dict):
        """Actualiza campos del inmueble desde datos OSM"""
        tags = element.get("tags", {})
        lat, lon = self._get_coordinates(element)
        
        # Actualizar solo si hay cambios significativos
        if tags.get("name") and tags.get("name") != inmueble.nombre:
            inmueble.nombre = tags.get("name")
        
        if lat and lon:
            inmueble.latitud = lat
            inmueble.longitud = lon
        
        # Actualizar dirección si ha mejorado
        new_address = self._build_full_address(tags)
        if new_address and len(new_address) > len(inmueble.direccion or ""):
            inmueble.direccion = new_address
        
        inmueble.es_bic = self._is_bic(tags)
        inmueble.es_ruina = self._is_ruina(tags)
        inmueble.updated_at = datetime.utcnow()
    
    def _should_update(self, ext: InmuebleOSMExt, element: dict) -> bool:
        """Verifica si el elemento OSM tiene cambios"""
        current_version = element.get('version')
        stored_version = ext.version or 0
        return current_version and current_version > stored_version
    
    def _get_coordinates(self, element: dict) -> Tuple[Optional[float], Optional[float]]:
        """Extrae coordenadas del elemento OSM"""
        # Nodos tienen lat/lon directo
        if element.get('lat') and element.get('lon'):
            return element['lat'], element['lon']
        
        # Ways y relations tienen center
        if 'center' in element:
            return element['center'].get('lat'), element['center'].get('lon')
        
        return None, None
    
    def _infer_type(self, tags: dict) -> Optional[str]:
        """Infiere el tipo de edificio desde tags"""
        # Priorizar building
        if building := tags.get("building"):
            if building in ["church", "cathedral", "chapel", "monastery", "convent", "hermitage", "basilica"]:
                return building
        
        # Luego amenity
        if tags.get("amenity") == "place_of_worship":
            return "place_of_worship"
        
        # Luego place_of_worship específico
        if pow_type := tags.get("place_of_worship"):
            return pow_type
        
        return None
    
    def _map_tipo_inmueble(self, tags: dict) -> Optional[str]:
        """Mapea tags OSM a tipo_inmueble_id del catálogo"""
        
        # Mapeo de tags OSM a nombres de tipos
        osm_to_tipo = {
            "cathedral": "Catedral",
            "basilica": "Basílica",
            "church": "Iglesia",
            "chapel": "Capilla",
            "monastery": "Monasterio",
            "convent": "Convento",
            "hermitage": "Ermita",
            "wayside_shrine": "Humilladero",
            "bell_tower": "Campanario",
            "cross": "Cruz",
            "wayside_cross": "Crucero",
            "lourdes_grotto": "Gruta"
        }
        
        # Buscar en diferentes campos
        building = tags.get("building")
        place_of_worship = tags.get("place_of_worship")
        
        tipo_nombre = osm_to_tipo.get(building) or osm_to_tipo.get(place_of_worship)
        
        if tipo_nombre:
            tipo = self.db.query(TipoInmueble).filter(
                TipoInmueble.nombre == tipo_nombre,
                TipoInmueble.activo == True
            ).first()
            if tipo:
                return tipo.id
        
        # Valor por defecto: "Iglesia"
        tipo_default = self.db.query(TipoInmueble).filter(
            TipoInmueble.nombre == "Iglesia",
            TipoInmueble.activo == True
        ).first()
        
        return tipo_default.id if tipo_default else None
    
    def _generate_qa_flags(self, element: dict, tags: dict) -> dict:
        """Genera banderas de control de calidad"""
        flags = {}
        
        # Completitud de datos
        if not tags.get("name"):
            flags["missing_name"] = True
        
        if not tags.get("denomination"):
            flags["missing_denomination"] = True
        
        # Verificación de coordenadas
        lat, lon = self._get_coordinates(element)
        if not lat or not lon:
            flags["missing_coordinates"] = True
        
        # Datos patrimoniales
        if tags.get("heritage") or tags.get("ref:es:bic"):
            if not tags.get("heritage:operator"):
                flags["incomplete_heritage"] = True
        
        # Coherencia de datos
        if tags.get("ruins") == "yes" and not tags.get("historic"):
            flags["ruins_without_historic"] = True
        
        return flags if flags else None
    
    def _extract_source_refs(self, tags: dict) -> Optional[dict]:
        """Extrae referencias de fuente desde tags"""
        refs = {}
        
        # Referencias oficiales
        if bic_ref := tags.get("ref:es:bic"):
            refs["bic"] = bic_ref
        
        if catastro := tags.get("ref:catastro"):
            refs["catastro"] = catastro
        
        # Referencias web
        if wikipedia := tags.get("wikipedia"):
            refs["wikipedia"] = wikipedia
        
        if wikidata := tags.get("wikidata"):
            refs["wikidata"] = wikidata
        
        if website := tags.get("website"):
            refs["website"] = website
        
        # Fuente original
        if source := tags.get("source"):
            refs["source"] = source
        
        return refs if refs else None
    
    def _resolve_provincia(self, lat: float, lon: float) -> Optional[str]:
        """Resuelve provincia_id desde coordenadas - TODO: implementar geocoding"""
        return None
    
    def _resolve_Municipio(self, lat: float, lon: float) -> Optional[str]:
        """Resuelve Municipio_id desde coordenadas - TODO: implementar geocoding"""
        return None
    
    def _build_description(self, tags: dict) -> Optional[str]:
        """Construye descripción desde tags OSM"""
        parts = []
        
        if denomination := tags.get("denomination"):
            parts.append(f"Denominación: {denomination}")
        
        if religion := tags.get("religion"):
            parts.append(f"Religión: {religion}")
        
        if architect := tags.get("architect"):
            parts.append(f"Arquitecto: {architect}")
        
        if start_date := tags.get("start_date"):
            parts.append(f"Construcción: {start_date}")
        
        if description := tags.get("description"):
            parts.append(description)
        
        return " | ".join(parts) if parts else None
    
    def _build_full_address(self, tags: dict) -> Optional[str]:
        """Construye dirección completa desde tags OSM"""
        parts = []
        
        if street := tags.get("addr:street"):
            parts.append(street)
        if housenumber := tags.get("addr:housenumber"):
            parts.append(housenumber)
        if postcode := tags.get("addr:postcode"):
            parts.append(f"CP {postcode}")
        if city := tags.get("addr:city"):
            parts.append(city)
        
        return ", ".join(parts) if parts else None
    
    def _is_bic(self, tags: dict) -> bool:
        """Detecta si es Bien de Interés Cultural"""
        heritage = tags.get("heritage", "").lower()
        heritage_status = tags.get("heritage:status", "").lower()
        
        return (
            "bien de interés cultural" in heritage or
            "bic" in heritage or
            tags.get("ref:es:bic") is not None or
            "bic" in heritage_status
        )
    
    def _is_ruina(self, tags: dict) -> bool:
        """Detecta si el edificio está en ruinas"""
        ruins = tags.get("ruins", "").lower()
        building = tags.get("building", "").lower()
        
        return ruins == "yes" or building == "ruins"
    
    def _parse_osm_timestamp(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parsea timestamp de OSM a datetime"""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return None
    
    async def _get_provincia_bbox(self, provincia_nombre: str) -> Optional[Tuple]:
        """Obtiene bounding box de una provincia usando Nominatim"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.nominatim_url}/search",
                    params={
                        "q": f"{provincia_nombre}, España",
                        "format": "json",
                        "limit": 1
                    },
                    headers={"User-Agent": self.user_agent}
                )
                results = response.json()
                if results:
                    bbox = results[0].get("boundingbox")
                    return (float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3]))
        except Exception as e:
            print(f"Error obteniendo bbox: {e}")
        
        return None


async def main():
    """Función de prueba"""
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        agent = OSMChurchSyncAgent(db)
        
        # Opción 1: Sincronizar España completa
        print("=== España completa (área ISO) ===")
        stats = await agent.sync_churches(
            use_spain_area=True,
            dry_run=True
        )
        
        print(f"Resultados: {stats}")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())