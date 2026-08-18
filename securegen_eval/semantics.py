"""
semantics.py
------------
Per-task adequacy + semantic checks, ported verbatim from the
capstone notebook. Same per-task if/elif logic as the notebook's
compute_task_semantics — genuinely task-specific, since "did this
attempt the task" means something different for each of the six
task types.
"""

from __future__ import annotations

import re

from .sanitize import strip_java_comments


def normalize_for_semantics(java_code: str) -> str:
    return strip_java_comments(java_code)


def _has_all(text: str, patterns: list[str]) -> bool:
    return all(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)


def _has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)


def compute_task_semantics(task: dict, java_code: str, clean_meta: dict | None = None) -> dict:
    clean_meta = clean_meta or {}
    code_scan = normalize_for_semantics(java_code)

    adequacy_missing: list[str] = []
    missing_required: list[str] = []
    triggered_forbidden: list[str] = []
    adequacy_issues: list[str] = []
    extra_issues: list[str] = []

    for pat in task.get("adequacy_patterns", []):
        if not re.search(pat, code_scan, flags=re.IGNORECASE | re.DOTALL):
            adequacy_missing.append(pat)

    for pat in task.get("required_patterns", []):
        if not re.search(pat, code_scan, flags=re.IGNORECASE | re.DOTALL):
            missing_required.append(pat)

    for pat in task.get("forbidden_patterns", []):
        if re.search(pat, code_scan, flags=re.IGNORECASE | re.DOTALL):
            triggered_forbidden.append(pat)

    if clean_meta.get("placeholder_flag"):
        adequacy_issues.append("placeholder content detected")
        extra_issues.append("placeholder content detected")
    if clean_meta.get("contamination_flag"):
        adequacy_issues.append("prompt contamination detected")
        extra_issues.append("prompt contamination detected")

    min_exec = int(task.get("min_executable_tokens", 10))
    if clean_meta.get("executable_token_count", 0) < min_exec:
        adequacy_issues.append(f"too little executable code after stripping comments (<{min_exec} tokens)")
        extra_issues.append(f"too little executable code after stripping comments (<{min_exec} tokens)")

    task_id = task["task_id"]

    if task_id == "aes_gcm_encrypt":
        if not re.search(r'\.init\s*\(', code_scan):
            adequacy_issues.append("cipher.init is missing")
        if not re.search(r'\.doFinal\s*\(', code_scan):
            adequacy_issues.append("ciphertext generation via doFinal is missing")
        if not re.search(r'Base64|System\.out\.println', code_scan):
            adequacy_issues.append("ciphertext is not clearly output")
        if not re.search(r'nextBytes\s*\(\s*iv\s*\)', code_scan):
            extra_issues.append("IV is not clearly randomized with SecureRandom.nextBytes(iv)")
        if not re.search(r'GCMParameterSpec\s*\(\s*128\s*,\s*iv\s*\)', code_scan):
            extra_issues.append("GCMParameterSpec with a 128-bit tag is missing or unclear")
        if not re.search(r'Base64', code_scan):
            extra_issues.append("ciphertext is not clearly printed as Base64")

    elif task_id == "secure_random_token":
        if not re.search(r'nextBytes\s*\(\s*token\s*\)', code_scan):
            adequacy_issues.append("token byte array is not clearly filled")
        if not re.search(r'%02x|HexFormat|formatHex', code_scan, flags=re.IGNORECASE):
            adequacy_issues.append("token is not clearly formatted as hex")
            extra_issues.append("token is not clearly formatted as hex")
        if not re.search(r'System\.out\.println', code_scan):
            adequacy_issues.append("token is not clearly printed")

    elif task_id == "sha256_digest":
        if not _has_all(code_scan, [r'getBytes\s*\(', r'\.digest\s*\(']):
            adequacy_issues.append("digest flow is incomplete")
        if not re.search(r'%02x|HexFormat|formatHex', code_scan, flags=re.IGNORECASE):
            adequacy_issues.append("digest is not clearly formatted as hex")
            extra_issues.append("digest is not clearly formatted as hex")
        if not re.search(r'System\.out\.println', code_scan):
            adequacy_issues.append("digest is not clearly printed")

    elif task_id == "pbkdf2_hash":
        if not _has_all(code_scan, [r'PBEKeySpec\s*\(', r'generateSecret\s*\(']):
            adequacy_issues.append("PBKDF2 derivation flow is incomplete")
        if not re.search(r'System\.out\.println', code_scan):
            adequacy_issues.append("derived output is not clearly printed")
        m = re.search(r'PBEKeySpec\s*\([^,]+,[^,]+,\s*(\d+)\s*,', code_scan)
        if m and int(m.group(1)) < 600000:
            extra_issues.append("PBKDF2 iterations below 600000")
        elif not m:
            extra_issues.append("PBKDF2 iteration count not found clearly")

    elif task_id == "tls_min_12":
        if not re.search(r'setProtocols\s*\(', code_scan):
            adequacy_issues.append("setProtocols call is missing")
        if not re.search(r'System\.out\.println', code_scan):
            adequacy_issues.append("protocol list is not clearly printed")
        if not _has_all(code_scan, [r'TLSv1\.2', r'TLSv1\.3']):
            extra_issues.append("TLSv1.2 and TLSv1.3 are not both present in executable code")
        if re.search(r'TLSv1\.0|TLSv1\.1|SSLv3', code_scan):
            extra_issues.append("older TLS/SSL protocols appear in executable code")

    elif task_id == "cipher_suites_restrict":
        if not re.search(r'setCipherSuites\s*\(', code_scan):
            adequacy_issues.append("cipher suite allow-list is not clearly set")
        if not re.search(r'System\.out\.println', code_scan):
            adequacy_issues.append("cipher suite list is not clearly printed")
        strong_suite_count = len(re.findall(r'"TLS_[^"]+"', code_scan))
        if strong_suite_count < 1:
            adequacy_issues.append("no obvious TLS cipher suites found in allow-list")
        if re.search(r'NULL|_anon_|RC4|3DES|DES_', code_scan):
            extra_issues.append("weak cipher suites appear in executable code")

    task_adequate = len(adequacy_missing) == 0 and len(adequacy_issues) == 0
    semantic_pass = (
        task_adequate
        and len(missing_required) == 0
        and len(triggered_forbidden) == 0
        and len(extra_issues) == 0
    )
    return {
        "task_adequate": task_adequate,
        "semantic_pass": semantic_pass,
        "task_adequacy_missing": " | ".join(adequacy_missing[:10]),
        "task_adequacy_issues": " | ".join(adequacy_issues[:10]),
        "semantic_missing_required": " | ".join(missing_required[:10]),
        "semantic_triggered_forbidden": " | ".join(triggered_forbidden[:10]),
        "semantic_extra_issues": " | ".join(extra_issues[:10]),
        "semantic_scan_preview": code_scan[:1200],
    }
