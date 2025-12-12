#!/usr/bin/env python3
"""
add_schema.py – añade __table_args__ = {'schema': SCHEMA} a todos los modelos
que encuentre en MODELS_ROOT (recursivo).

Uso:
    export MODELS_ROOT=./src/models
    export DATABASE_SCHEMA=business
    python add_schema.py          # ensayo, solo imprime
    python add_schema.py --apply  # sobrescribe los .py
"""
import os
import re
import sys
from pathlib import Path

MODELS_ROOT  = Path(os.getenv("MODELS_ROOT") or "").expanduser()
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA") or "public"

if not MODELS_ROOT.is_dir():
    sys.exit(f"MODELS_ROOT no existe: {MODELS_ROOT}")

# regex que captura la línea que empieza la clase
CLASS_RE = re.compile(r'^\s*class\s+(\w+)\s*\(.*Base.*\):')

# plantilla que insertaremos justo después de la línea de la clase
TABLE_ARGS = f"    __table_args__ = {{'schema': '{DATABASE_SCHEMA}'}}"


def process_file(path: Path, dry: bool = True) -> bool:
    """Devuelve True si el fichero se ha modificado."""
    with path.open(encoding="utf-8") as f:
        lines = f.readlines()

    new_lines, modified = [], False
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        new_lines.append(line)

        # ¿es cabecera de clase hija de Base?
        if CLASS_RE.match(line):
            # busca si YA tiene __table_args__ en los 20 siguientes renglones
            has_args = False
            j = i + 1
            while j < n and j < i + 20 and not lines[j].startswith("class "):
                if re.match(r'^\s*__table_args__\s*=', lines[j]):
                    has_args = True
                    break
                j += 1

            if not has_args:
                # inserta la línea con la indentación correcta
                indent = re.match(r'^(\s*)', lines[i+1] if i+1 < n else "   ").group(1)
                new_lines.append(indent + TABLE_ARGS + "\n")
                modified = True
        i += 1

    if modified and not dry:
        backup = path.with_suffix(path.suffix + ".bak")
        path.rename(backup)          # conservamos copia
        with path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"✏️  {path}  (backup: {backup.name})")
    elif modified:
        print(f"📄  {path}  (modificaría)")

    return modified


def main():
    dry = "--apply" not in sys.argv
    if dry:
        print("🔍 MODO ENSAYO – usa --apply para escribir los cambios\n")

    count = 0
    for py in MODELS_ROOT.rglob("*.py"):
        if process_file(py, dry):
            count += 1

    print(f"\n{count} ficheros procesados." + (" Nada cambiado." if dry else ""))


if __name__ == "__main__":
    main()