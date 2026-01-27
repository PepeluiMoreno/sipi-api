import sys
from pathlib import Path

# Agregar sipi-core al path para importar sus módulos
SIPI_CORE_PATH = Path(__file__).parent.parent.parent.parent / "sipi-core"
sys.path.insert(0, str(SIPI_CORE_PATH / "src"))

from sqlalchemy import select
from sipi.db.models.geografia import ComunidadAutonoma, Provincia, Municipio
from sipi.db.models.actores import RegistroPropiedad

def generate_code(name, length=2):
    """Genera código dummy basado en hash del nombre"""
    if not name: return "00"
    import hashlib
    h = hashlib.md5(name.encode('utf-8')).hexdigest().upper()
    return h[:length]

async def get_or_create_ca(session, nombre):
    if not nombre: return None
    stmt = select(ComunidadAutonoma).where(ComunidadAutonoma.nombre == nombre)
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()

    if not obj:
        code = generate_code(nombre, 2)
        obj = ComunidadAutonoma(
            nombre=nombre,
            nombre_oficial=nombre,
            codigo_ine=code,
            activo=True
        )
        session.add(obj)
        try:
            await session.flush()
        except Exception:
            await session.rollback()
            import uuid
            code = str(uuid.uuid4())[:2].upper()
            obj.codigo_ine = code
            session.add(obj)
            await session.flush()
    return obj

async def get_or_create_provincia(session, nombre, ca_id):
    if not nombre: return None
    stmt = select(Provincia).where(Provincia.nombre == nombre)
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()

    if not obj:
        code = generate_code(nombre, 2)
        obj = Provincia(
            nombre=nombre,
            nombre_oficial=nombre,
            comunidad_autonoma_id=ca_id,
            codigo_ine=code,
            activo=True
        )
        session.add(obj)
        await session.flush()
    return obj

async def get_or_create_municipio(session, nombre, provincia_id, ca_id):
    if not nombre: return None
    stmt = select(Municipio).where(Municipio.nombre == nombre, Municipio.provincia_id == provincia_id)
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    
    if not obj:
        code_ine = generate_code(nombre + (provincia_id or ""), 5)
        obj = Municipio(
            nombre=nombre,
            nombre_oficial=nombre,
            provincia_id=provincia_id,
            comunidad_autonoma_id=ca_id,
            codigo_ine=code_ine,
            activo=True
        )
        session.add(obj)
        await session.flush()
    return obj
