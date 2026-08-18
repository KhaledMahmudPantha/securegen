"""
detectors.py
------------
Regex-based misuse detectors, ported verbatim from the capstone
notebook. See the project README for the known limitation here:
this is pattern-matching, not AST analysis — it catches the misuse
shapes it was written to catch, and a stratified manual review is
still the right next step before treating detector output as ground
truth (this is called out explicitly in the capstone report too).
"""

from __future__ import annotations

import re

from .sanitize import strip_java_comments


def _detect_gcm_bad_iv(scan: str) -> bool:
    """
    Improved version of the capstone's original gcm_bad_iv check.

    The original just checked "does AES/GCM appear anywhere, AND does a
    16/8/4-byte array appear anywhere" — which false-positives whenever
    an unrelated 16-byte array exists nearby (e.g. a 16-byte AES key),
    even when the actual IV is correctly sized.

    This version traces the *specific variable* passed as the IV
    argument to GCMParameterSpec(tagLen, ivVar) and checks that
    variable's own declared array size — so a correctly-sized IV next
    to a differently-sized key no longer triggers a false positive.
    """
    if not re.search(r'AES/GCM/NoPadding', scan):
        return False

    # Find the IV variable name(s) actually passed to GCMParameterSpec.
    iv_var_names = re.findall(r'GCMParameterSpec\s*\(\s*\d+\s*,\s*(\w+)\s*\)', scan)

    if not iv_var_names:
        # Can't identify the IV variable at all (unusual construction) —
        # fall back to the old, broader heuristic rather than silently
        # passing potentially-bad code.
        return bool(re.search(r'new byte\[\s*(16|8|4)\s*\]', scan))

    for iv_var in iv_var_names:
        # Match `byte[] ivVar = new byte[N]` or `ivVar = new byte[N]`.
        decl_pattern = rf'(?:byte\s*\[\s*\]\s*)?{re.escape(iv_var)}\s*=\s*new byte\[\s*(\d+)\s*\]'
        m = re.search(decl_pattern, scan)
        if m:
            size = int(m.group(1))
            if size != 12:
                return True
        else:
            # IV variable used but its declaration wasn't found in this
            # scan (e.g. passed in from elsewhere) — treat as unclear
            # rather than silently passing.
            return bool(re.search(r'new byte\[\s*(16|8|4)\s*\]', scan))

    return False


def detect_misuses(java_code: str) -> dict:
    scan = strip_java_comments(java_code)
    return {
        "aes_ecb": bool(re.search(r'AES/ECB', scan, flags=re.IGNORECASE)),
        "md5_or_sha1": bool(re.search(r'MD5|SHA-1', scan, flags=re.IGNORECASE)),
        "random_not_secure_random": bool(re.search(r'new\s+(?:java\.util\.)?Random\s*\(', scan))
        and not re.search(r'SecureRandom', scan),
        "trust_all_manager": bool(
            re.search(r'X509TrustManager', scan)
            and re.search(r'checkServerTrusted\s*\([^)]*\)\s*\{\s*\}', scan, flags=re.DOTALL)
        ),
        "permissive_hostname_verifier": bool(
            re.search(r'HostnameVerifier', scan) and re.search(r'return\s+true\s*;', scan)
        ),
        "tls_lt_12": bool(re.search(r'TLSv1(?!\.2|\.3)|TLSv1\.0|TLSv1\.1|SSLv3', scan)),
        "weak_cipher_suite": bool(re.search(r'NULL|_anon_|RC4|3DES|DES_', scan)),
        "rsa_key_lt_2048": bool(re.search(r'initialize\s*\(\s*(512|1024)\s*\)', scan)),
        "gcm_bad_iv": _detect_gcm_bad_iv(scan),
        "weak_pbkdf2_iters": bool(
            re.search(r'PBEKeySpec\s*\([^,]+,[^,]+,\s*(\d+)\s*,', scan)
            and any(
                int(x) < 600000
                for x in re.findall(r'PBEKeySpec\s*\([^,]+,[^,]+,\s*(\d+)\s*,', scan)
            )
        ),
    }


def any_misuse(misuse_flags: dict) -> bool:
    return any(misuse_flags.values())


def misuse_types(misuse_flags: dict) -> list[str]:
    return [k for k, v in misuse_flags.items() if v]
