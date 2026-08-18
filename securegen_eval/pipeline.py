"""
pipeline.py
-----------
Ties compile gate + misuse detectors + semantic checks together into
one verdict, using the same label logic as the capstone notebook:

    UNCOMPILED               - failed the javac gate
    COMPILED_SEMANTIC_FAIL   - compiles but not task-adequate / semantic-fail
    MISUSE                   - compiles, task-adequate, but a misuse detector fired
    SECURE                   - compiles, task-adequate, semantic pass, no misuse

This is the one module that's genuinely new relative to the notebook —
the notebook's labeling logic lived inline in the experiment runner
cell; here it's pulled out into a single reusable function so it can
be called from a CLI, an API, or tests without dragging along the
notebook's generation/retry loop.
"""

from __future__ import annotations

from pathlib import Path

from .compiler import categorize_compile_error, compile_java_source
from .detectors import detect_misuses, misuse_types
from .sanitize import (
    sanitize_generated_java,
    strip_blank_and_comment_only_lines,
    strip_java_comments,
)
from .semantics import compute_task_semantics
from .tasks import get_task
import re


def evaluate_java_source(task_id: str, java_code: str, already_clean: bool = True) -> dict:
    """
    Run the full evaluation pipeline on a Java source string for a given
    task. Set already_clean=False if this is raw, unclean model output
    that still needs extraction/contamination-stripping (matches the
    notebook's completion-mode flow); leave it True for a plain .java
    file a user hands you directly (the CLI's default case).
    """
    task = get_task(task_id)

    if already_clean:
        clean_code = java_code
        no_comments = strip_java_comments(clean_code)
        code_only = strip_blank_and_comment_only_lines(no_comments)
        clean_meta = {
            "contamination_flag": False,
            "contamination_lines": "",
            "placeholder_flag": False,
            "brace_balance_after_clean": clean_code.count("{") - clean_code.count("}"),
            "executable_token_count": len(re.findall(r'[A-Za-z_]\w*', code_only)),
        }
    else:
        clean_code, clean_meta = sanitize_generated_java(java_code)

    compile_result = compile_java_source(clean_code)
    compile_result["error_category"] = categorize_compile_error(compile_result.get("first_error", ""))

    if not compile_result["compile_ok"]:
        return {
            "task_id": task_id,
            "label": "UNCOMPILED",
            "compile": compile_result,
            "misuse": {},
            "misuse_types": [],
            "semantics": {},
            "clean_meta": clean_meta,
        }

    misuse_flags = detect_misuses(clean_code)
    semantics = compute_task_semantics(task, clean_code, clean_meta)
    flagged_misuse = misuse_types(misuse_flags)
    misuse_any = bool(flagged_misuse)

    # Label precedence matches the capstone notebook's assign_label()
    # exactly: task-adequate + misuse takes priority over semantic-fail
    # (a task-adequate-but-insecure output is MISUSE, not a generic
    # semantic failure — that distinction is what RQ2 depended on).
    if semantics["task_adequate"] and misuse_any:
        label = "MISUSE"
    elif semantics["semantic_pass"] and not misuse_any:
        label = "SECURE"
    else:
        label = "COMPILED_SEMANTIC_FAIL"

    return {
        "task_id": task_id,
        "label": label,
        "compile": compile_result,
        "misuse": misuse_flags,
        "misuse_types": flagged_misuse,
        "semantics": semantics,
        "clean_meta": clean_meta,
    }


def evaluate_java_file(task_id: str, path: str | Path, already_clean: bool = True) -> dict:
    code = Path(path).read_text(encoding="utf-8")
    result = evaluate_java_source(task_id, code, already_clean=already_clean)
    result["source_path"] = str(path)
    return result
