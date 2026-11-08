import os
import sys
import shutil

exe_dir = os.path.dirname(os.path.abspath(sys.executable))
internal = os.path.join(exe_dir, "_internal")
base = internal if os.path.exists(os.path.join(internal, "gui_app.py")) else exe_dir

if base not in sys.path:
    sys.path.insert(0, base)
if exe_dir not in sys.path:
    sys.path.insert(0, exe_dir)

os.chdir(exe_dir)

cli_flags = {"--wizard", "--init", "--run-discovery", "--compile", "--build-doc", "--all", "--recommend-papers", "--version"}
run_cli = any(flag in sys.argv for flag in cli_flags)

if "--web" in sys.argv:
    print("=" * 70)
    print("La app web no esta disponible en la version portable.")
    print("Para usar la interfaz web, instala Python y ejecuta:")
    print("  python main.py --web")
    print("=" * 70)
    sys.exit(0)

try:
    if run_cli:
        import main
        main.main()
    else:
        # Default: GUI desktop
        import gui_app
        gui_app.main()
except Exception as e:
    import traceback
    with open(os.path.join(exe_dir, "error.log"), "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    raise

# Cleanup unused artifacts
for folder in ("__pycache__", "build"):
    path = os.path.join(base, folder)
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
for root, _, files in os.walk(base):
    for f in files:
        if f.endswith(".pyc"):
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass