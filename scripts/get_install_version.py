"""
Генерирует version_define.iss для Inno Setup из version.py.
Запуск перед сборкой: python scripts/get_install_version.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import __version__

OUT = ROOT / "installer" / "version_define.iss"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(f'; Auto-generated from version.py — do not edit\n#define MyAppVersion "{__version__}"\n', encoding="utf-8")
print(f"Wrote {OUT} with MyAppVersion = {__version__}")
