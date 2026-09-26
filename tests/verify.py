"""End-to-end check for the verify skill: data validation, then a full site build.

Run from the repo root:  python tests/verify.py
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NPM = shutil.which("npm") or "npm"


def run(label: str, cmd: list[str], cwd: Path) -> bool:
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = proc.returncode == 0
    print(f"[{'pass' if ok else 'fail'}] {label} ({time.time() - start:.0f}s)")
    if not ok:
        print((proc.stdout + proc.stderr).strip()[-3000:])
    return ok


def main() -> int:
    ok = run("data validation", [NPM, "run", "-s", "validate"], ROOT)
    built = run("site build", [NPM, "run", "-s", "build"], ROOT / "web")
    if built:
        pages = sorted(p.relative_to(ROOT / "web" / "dist").as_posix() for p in (ROOT / "web" / "dist").rglob("index.html"))
        print(f"  pages: {', '.join(pages)}")
    return 0 if ok and built else 1


if __name__ == "__main__":
    sys.exit(main())
