"""Shared start-up for the entry scripts: use experso's own Python if it exists
($EXPERSO_PY, else ~/.experso/venv made by install.sh --deps), then make the
`experso` package next to this file importable."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(module: str, func: str = "main"):
    py = os.environ.get("EXPERSO_PY") or str(Path.home() / ".experso" / "venv" / "bin" / "python")
    if Path(py).is_file() and Path(sys.executable).resolve() != Path(py).resolve() \
            and not os.environ.get("EXPERSO_NO_REEXEC"):
        os.environ["EXPERSO_NO_REEXEC"] = "1"
        os.execv(py, [py, *sys.argv])
    sys.path.insert(0, str(HERE))
    mod = __import__(f"experso.steps.{module}", fromlist=[func])
    return getattr(mod, func)()
