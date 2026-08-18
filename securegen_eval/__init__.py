"""
securegen_eval
===============

Productionized version of the capstone's Part-B evaluation logic
(compile gate, misuse detectors, task-adequacy / semantic checks),
pulled out of the research notebook into an importable, testable
package with a CLI.

    from securegen_eval import evaluate_java_file, evaluate_java_source
    from securegen_eval.tasks import TASKS_CORE, get_task

Same detection logic as the capstone notebook (same regexes, same
per-task adequacy rules) — this module just gives it a stable API,
tests, and a CLI so it can run outside a notebook cell.
"""

from .pipeline import evaluate_java_file, evaluate_java_source  # noqa: F401
