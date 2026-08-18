"""
compiler.py
-----------
Compile gate — shells out to `javac`, same as the capstone notebook.
Requires a JDK on PATH (the Dockerfile installs openjdk-17-jdk-headless
for exactly this reason).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def compile_java_source(java_code: str, work_dir: str | Path | None = None) -> dict:
    """
    Compile a single Main.java source string with javac.
    Returns the same shape of dict the capstone notebook produced,
    so downstream evaluation logic is a drop-in match.
    """
    if work_dir is None:
        tmp = tempfile.mkdtemp(prefix="securegen_compile_")
        sample_dir = Path(tmp)
    else:
        sample_dir = Path(work_dir)
        sample_dir.mkdir(parents=True, exist_ok=True)

    class_dir = sample_dir / "classes"
    class_dir.mkdir(parents=True, exist_ok=True)
    java_path = sample_dir / "Main.java"
    java_path.write_text(java_code, encoding="utf-8")

    try:
        proc = subprocess.run(
            ["javac", "-encoding", "UTF-8", "-d", str(class_dir), str(java_path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except FileNotFoundError as exc:
        return {
            "compile_ok": False,
            "javac_returncode": -1,
            "javac_stdout": "",
            "javac_stderr": f"javac not found on PATH: {exc}",
            "first_error": "javac not found on PATH — is a JDK installed?",
            "java_path": str(java_path),
            "class_dir": str(class_dir),
        }
    except subprocess.TimeoutExpired:
        return {
            "compile_ok": False,
            "javac_returncode": -1,
            "javac_stdout": "",
            "javac_stderr": "javac timed out after 30s",
            "first_error": "javac timed out",
            "java_path": str(java_path),
            "class_dir": str(class_dir),
        }

    first_error = ""
    stderr = (proc.stderr or "").strip()
    if stderr:
        first_error = stderr.splitlines()[0]
    return {
        "compile_ok": proc.returncode == 0,
        "javac_returncode": proc.returncode,
        "javac_stdout": (proc.stdout or "").strip(),
        "javac_stderr": stderr,
        "first_error": first_error,
        "java_path": str(java_path),
        "class_dir": str(class_dir),
    }


def categorize_compile_error(first_error: str) -> str:
    if not first_error:
        return "none"
    e = first_error.lower()
    if "'{' expected" in e:
        return "brace_or_structure"
    if "not a statement" in e:
        return "not_a_statement"
    if "class, interface, enum, or record expected" in e:
        return "extraneous_text"
    if "cannot find symbol" in e:
        return "missing_symbol"
    if "reached end of file while parsing" in e:
        return "truncated_output"
    return "other"
