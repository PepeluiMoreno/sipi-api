from pathlib import Path

content = """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sipi-core"
version = "0.1.0"
description = "Core domain models and logic for SIPI"
dependencies = [
    "sqlalchemy[asyncio]~=2.0.36",
    "GeoAlchemy2~=0.15.2",
    "pydantic~=2.9.2",
    "python-dotenv~=1.0.1",
    "strawberry-graphql[asgi]~=0.243.0"
]
requires-python = ">=3.10"

[tool.hatch.build.targets.wheel]
packages = ["src/sipi"]
"""

target_path = Path("../sipi-core/pyproject.toml")
target_path.write_text(content, encoding="utf-8")
print(f"Created {target_path}")

# Also create the __init__.py in src/sipi
init_path = Path("../sipi-core/src/sipi/__init__.py")
init_path.touch()
print(f"Created {init_path}")
