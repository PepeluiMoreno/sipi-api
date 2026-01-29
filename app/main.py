# sipi-api/app/main.py
from typing import AsyncGenerator
import logging
import time
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from strawberry.fastapi import GraphQLRouter

# ============================================================================
# 1. IMPORTAR LA CONEXIÓN YA CONFIGURADA
# ============================================================================

try:
    from sipi.db.sessions.async_session import db_manager
    print("✅ Conexión a base de datos configurada")
except ImportError as e:
    print(f"❌ Error importando conexión: {e}")
    raise

# ============================================================================
# 2. CONFIGURACIÓN
# ============================================================================

startup_time = time.time()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('app.graphql')

# Database Session Dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session

# GraphQL Context
async def get_context(db: AsyncSession = Depends(get_db_session)):
    return {"db": db}

# Schema y GraphQL Router
def create_graphql_router() -> GraphQLRouter:
    from app.graphql.schema import create_schema
    schema = create_schema()
    return GraphQLRouter(
        schema,
        context_getter=get_context,
        graphiql=True,
    )

# ============================================================================
# 3. APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="API GraphQL",
    description="API GraphQL para sistema de información",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL router
graphql_router = create_graphql_router()
app.include_router(graphql_router, prefix="/graphql")

# ============================================================================
# 4. FUNCIONES REALES
# ============================================================================

async def check_database_connection():
    """Verificar conexión REAL a la base de datos"""
    try:
        async with db_manager.session() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            return value == 1
    except Exception as e:
        logger.error(f"Error de conexión a BD: {e}")
        return False

# ============================================================================
# 5. RUTAS
# ============================================================================

@app.get("/api/health/db")
async def health_db():
    """Health check específico para base de datos"""
    start_time = time.time()
    
    db_connected = await check_database_connection()
    
    response_time = (time.time() - start_time) * 1000
    
    return JSONResponse({
        "status": "connected" if db_connected else "disconnected",
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(response_time, 2),
        "database": {
            "connected": db_connected,
            "check_query": "SELECT 1",
            "status": "online" if db_connected else "offline"
        }
    })


@app.get("/", response_class=HTMLResponse)
async def root():
    """Página principal - Solo información REAL verificada"""
    
    # Verificar conexión REAL
    db_connected = await check_database_connection()
    db_status = "conectada" if db_connected else "error"
    
    # Tiempo de actividad REAL
    uptime_seconds = int(time.time() - startup_time)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>backend sipi - versión beta</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #0a0a0a;
                color: #e0e0e0;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                max-width: 600px;
                width: 100%;
                text-align: center;
            }}
            
            .header {{
                margin-bottom: 40px;
            }}
            
            .header h1 {{
                font-size: 24px;
                font-weight: 400;
                color: #fff;
                margin-bottom: 8px;
            }}
            
            .header .subtitle {{
                color: #888;
                font-size: 14px;
                margin-bottom: 6px;
            }}
            
            .header .version {{
                color: #4a9eff;
                font-size: 13px;
                font-weight: 500;
                background: rgba(74, 158, 255, 0.1);
                padding: 4px 12px;
                border-radius: 12px;
                display: inline-block;
                margin-top: 8px;
                border: 1px solid rgba(74, 158, 255, 0.2);
            }}
            
            .status-card {{
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 20px;
            }}
            
            .status-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                border-bottom: 1px solid #222;
            }}
            
            .status-item:last-child {{
                border-bottom: none;
            }}
            
            .status-label {{
                color: #aaa;
                font-size: 14px;
            }}
            
            .status-value {{
                color: #e0e0e0;
                font-size: 16px;
                font-weight: 500;
            }}
            
            .status-value.connected {{
                color: #10b981;
            }}
            
            .status-value.error {{
                color: #ef4444;
            }}
            
            .graphiql-button {{
                display: block;
                background: #4a9eff;
                color: white;
                border: none;
                padding: 16px;
                font-size: 16px;
                text-decoration: none;
                border-radius: 12px;
                margin-top: 30px;
                font-weight: 500;
                transition: background 0.2s;
            }}
            
            .graphiql-button:hover {{
                background: #3b82f6;
            }}
            
            .timestamp {{
                margin-top: 30px;
                color: #666;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Backend del Sistema de Información de Inmuebles Inmatriculados</h1>
                <p class="subtitle">api graphql con postgresql</p>
                <div class="version">versión beta</div>
            </div>
            
            <div class="status-card">
                <div class="status-item">
                    <span class="status-label">Tiempo activo</span>
                    <span class="status-value">{uptime}</span>
                </div>
                
                <div class="status-item">
                    <span class="status-label">Base de datos</span>
                    <span class="status-value {'connected' if db_connected else 'error'}">
                        {db_status}
                    </span>
                </div>
            </div>
            
            <a href="/graphql" class="graphiql-button">
                abrir graphiql sandbox
            </a>
            
            <div class="timestamp">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <script>
            // Actualizar timestamp
            function updateTimestamp() {{
                const now = new Date();
                document.querySelector('.timestamp').textContent = 
                    now.toLocaleDateString('es-ES') + ' ' + 
                    now.toLocaleTimeString('es-ES', {{ 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: false 
                    }});
            }}
            setInterval(updateTimestamp, 1000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    """Health check REAL"""
    start_time = time.time()
    
    db_connected = await check_database_connection()
    
    response_time = (time.time() - start_time) * 1000
    
    return JSONResponse({
        "status": "healthy" if db_connected else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int(time.time() - startup_time),
        "response_time_ms": round(response_time, 2),
        "database": {
            "connected": db_connected,
            "health_check": "SELECT 1"
        }
    })

# Eventos
@app.on_event("startup")
async def startup():
    logger.info("Backend SIPI iniciado - versión beta")
    
    if await check_database_connection():
        logger.info("Base de datos conectada")
    else:
        logger.error("Error de conexión a base de datos")

@app.on_event("shutdown")
async def shutdown():
    if hasattr(db_manager, 'close'):
        await db_manager.close()
        logger.info("Conexiones cerradas")

logger.info("Backend configurado")