"""
cli.py
------
Command-line interface for the eval pipeline.

    python -m securegen_eval.cli scan MyFile.java --task aes_gcm_encrypt
    python -m securegen_eval.cli list-tasks
    python -m securegen_eval.cli scan MyFile.java --task tls_min_12 --json
"""

from __future__ import annotations

import argparse
import json
import sys

from .pipeline import evaluate_java_file
from .tasks import list_task_ids


def _cmd_scan(args: argparse.Namespace) -> int:
    result = evaluate_java_file(args.task, args.file, already_clean=not args.raw)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["label"] in ("SECURE",) else 1

    label = result["label"]
    print(f"File:  {args.file}")
    print(f"Task:  {args.task}")
    print(f"Label: {label}")
    print()

    compile_r = result["compile"]
    print(f"Compile OK: {compile_r['compile_ok']}")
    if not compile_r["compile_ok"]:
        print(f"  First error: {compile_r.get('first_error', '')}")
        print(f"  Category:    {compile_r.get('error_category', '')}")
        return 1

    sem = result["semantics"]
    print(f"Task adequate: {sem.get('task_adequate')}")
    print(f"Semantic pass: {sem.get('semantic_pass')}")
    if sem.get("task_adequacy_issues"):
        print(f"  Adequacy issues:   {sem['task_adequacy_issues']}")
    if sem.get("semantic_missing_required"):
        print(f"  Missing required:  {sem['semantic_missing_required']}")
    if sem.get("semantic_triggered_forbidden"):
        print(f"  Forbidden hit:     {sem['semantic_triggered_forbidden']}")

    if result["misuse_types"]:
        print(f"Misuse detected: {', '.join(result['misuse_types'])}")
    else:
        print("Misuse detected: none")

    print()
    if label == "SECURE":
        print("VERDICT: looks good — compiled, task-adequate, no misuse detected.")
    elif label == "MISUSE":
        print("VERDICT: compiled and attempted the task, but a misuse pattern was flagged.")
    elif label == "COMPILED_SEMANTIC_FAIL":
        print("VERDICT: compiled, but did not clearly complete the intended secure task.")

    return 0 if label == "SECURE" else 1


def _cmd_list_tasks(_: argparse.Namespace) -> int:
    for tid in list_task_ids():
        print(tid)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="securegen-eval", description="Java security-code evaluation CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Evaluate a single Java file against a task.")
    scan_p.add_argument("file", help="Path to a .java file (expects a single public class Main).")
    scan_p.add_argument("--task", required=True, help="Task id (see `list-tasks`).")
    scan_p.add_argument("--json", action="store_true", help="Print the full result as JSON.")
    scan_p.add_argument(
        "--raw",
        action="store_true",
        help="Treat input as raw/uncleaned model output (runs extraction + contamination stripping first).",
    )
    scan_p.set_defaults(func=_cmd_scan)

    list_p = sub.add_parser("list-tasks", help="List available task ids.")
    list_p.set_defaults(func=_cmd_list_tasks)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
