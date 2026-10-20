"""Root entrypoint for Streamlit Cloud and local launches."""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
src_dir = str(ROOT / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

target = ROOT / "src" / "sendsmart" / "ui" / "app.py"
runpy.run_path(str(target), run_name="__main__")
