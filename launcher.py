import os
import sys
import shutil

exe_dir = os.path.dirname(os.path.abspath(sys.executable))
internal = os.path.join(exe_dir, "_internal")
base = internal if os.path.exists(os.path.join(internal, "streamlit_app.py")) else exe_dir

if base not in sys.path:
    sys.path.insert(0, base)
if exe_dir not in sys.path:
    sys.path.insert(0, exe_dir)

os.chdir(base)

cli_flags = {"--wizard", "--init", "--run-discovery", "--compile", "--build-doc", "--all", "--recommend-papers", "--version", "--web"}
run_cli = any(flag in sys.argv for flag in cli_flags) or len(sys.argv) == 1

if run_cli and "--web" not in sys.argv and len(sys.argv) == 1:
    # Default to full console wizard when launched without arguments
    sys.argv = [sys.argv[0], "--wizard"]

if "--web" in sys.argv:
    from streamlit.web import bootstrap
    app_path = os.path.join(base, "streamlit_app.py")
    bootstrap.run(app_path, "", [], {})
else:
    import main
    main.main()

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