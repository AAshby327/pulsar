from pathlib import Path

# Automatically import all modules in this directory
for module_path in Path(__file__).parent.glob("*.py"):
    if module_path.name != "__init__.py":
        module_name = module_path.stem
        exec(f"from .{module_name} import *")
