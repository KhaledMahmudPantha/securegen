"""
sanitize.py
-----------
Java-source extraction/cleaning logic, ported from the capstone
notebook's "Extraction, compile gate, misuse detectors, and semantic
checks" cell. Same regexes and control flow — this file only adds
type hints, docstrings, and moves it out of notebook-global scope.
"""

from __future__ import annotations

import hashlib
import re

JAVA_FENCE_RE = re.compile(r"```(?:java)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

CONTAMINATION_PATTERNS = [
    r"Hard constraints:",
    r"Task ID:",
    r"Authoritative guidance",
    r"Shortcut mode:",
    r"Complete the Java 17 file below",
    r"Continue the Java 17 file below",
    r"Continue the Java 17 file",
    r"Rewrite the Java 17 file",
    r"Java prefix:",
    r"Task:",
    r"Goal:",
    r"Must satisfy:",
    r"Short guidance:",
    r"Critical rules:",
    r"Negative-control rule:",
    r"Target signal:",
]

PLACEHOLDER_PATTERNS = [
    r"TODO",
    r"write your code here",
    r"implement here",
    r"placeholder",
    r"\.\.\.",
    r"your code here",
    r"insert code",
    r"fill in",
]

REAL_MAIN_DECL_RE = re.compile(r'(?m)^\s*public\s+class\s+Main\s*\{')
REAL_CLASS_DECL_RE = re.compile(r'(?m)^\s*class\s+Main\s*\{')
IMPORT_LINE_RE = re.compile(r'(?m)^\s*import\s+[\w\.\*]+\s*;')


def stable_code_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def count_loc(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip())


def count_imports(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip().startswith("import "))


def brace_balance(text: str) -> int:
    return text.count("{") - text.count("}")


def extract_code_block(text: str | None) -> str:
    if text is None:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    matches = JAVA_FENCE_RE.findall(text)
    if matches:
        return max(matches, key=len).strip()
    return text.strip()


def has_real_full_class(raw_text: str) -> bool:
    raw_text = raw_text or ""
    return bool(REAL_MAIN_DECL_RE.search(raw_text) or REAL_CLASS_DECL_RE.search(raw_text))


def remove_prefatory_noise(candidate: str) -> str:
    candidate = re.sub(r"^\s*package\s+[\w\.]+\s*;\s*", "", candidate, flags=re.MULTILINE)
    import_matches = list(IMPORT_LINE_RE.finditer(candidate))
    main_match = REAL_MAIN_DECL_RE.search(candidate) or REAL_CLASS_DECL_RE.search(candidate)
    if main_match:
        if import_matches:
            valid_imports = [m for m in import_matches if m.start() < main_match.start()]
            candidate = candidate[valid_imports[0].start():] if valid_imports else candidate[main_match.start():]
        else:
            candidate = candidate[main_match.start():]
    elif import_matches:
        candidate = candidate[import_matches[0].start():]
    return candidate.strip()


def cut_after_main_class(candidate: str) -> str:
    m = REAL_MAIN_DECL_RE.search(candidate) or REAL_CLASS_DECL_RE.search(candidate)
    if not m:
        return candidate.strip()
    s = candidate[m.start():]
    out = []
    depth = 0
    started = False
    for ch in s:
        out.append(ch)
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth <= 0:
                break
    return "".join(out).strip()


def strip_contamination_lines(candidate: str) -> tuple[str, list[str]]:
    clean_lines = []
    contamination_hits = []
    for ln in candidate.splitlines():
        stripped = ln.strip()
        bad = False
        for pat in CONTAMINATION_PATTERNS:
            if re.search(pat, stripped, flags=re.IGNORECASE):
                bad = True
                contamination_hits.append(stripped)
                break
        if not bad:
            clean_lines.append(ln)
    return "\n".join(clean_lines).strip(), contamination_hits


def strip_java_comments(text: str) -> str:
    if not text:
        return ""
    out = []
    i = 0
    n = len(text)
    in_line = in_block = in_string = in_char = escaped = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line:
            if ch == "\n":
                in_line = False
                out.append(ch)
            i += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
            else:
                if ch == "\n":
                    out.append("\n")
                i += 1
            continue
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if in_char:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "'":
            in_char = True
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def strip_blank_and_comment_only_lines(text: str) -> str:
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            continue
        out.append(ln)
    return "\n".join(out)


def sanitize_generated_java(raw_text: str, seed_prefix: str = "") -> tuple[str, dict]:
    """
    Simplified entry point for standalone use (outside the notebook's
    completion-mode generation loop): pass the raw model/file text and
    an optional seed_prefix if this came from completion-mode generation.
    """
    raw_text = extract_code_block(raw_text)
    candidate = raw_text if has_real_full_class(raw_text) else (seed_prefix + raw_text)

    candidate = remove_prefatory_noise(candidate)
    candidate, contamination_lines = strip_contamination_lines(candidate)
    candidate = cut_after_main_class(candidate)

    bb = brace_balance(candidate)
    if candidate and (REAL_MAIN_DECL_RE.search(candidate) or REAL_CLASS_DECL_RE.search(candidate)) and bb > 0:
        candidate = candidate + ("\n" + "}" * bb)

    placeholder_flag = any(re.search(p, candidate, flags=re.IGNORECASE) for p in PLACEHOLDER_PATTERNS)
    contamination_flag = len(contamination_lines) > 0

    no_comments = strip_java_comments(candidate)
    code_only = strip_blank_and_comment_only_lines(no_comments)
    executable_token_count = len(re.findall(r'[A-Za-z_]\w*', code_only))

    meta = {
        "contamination_flag": contamination_flag,
        "contamination_lines": " | ".join(contamination_lines[:10]),
        "placeholder_flag": bool(placeholder_flag),
        "brace_balance_after_clean": brace_balance(candidate),
        "executable_token_count": executable_token_count,
    }
    return candidate.strip() + ("\n" if candidate.strip() else ""), meta
