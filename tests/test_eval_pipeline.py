"""
Tests for securegen_eval. Compile-gate tests are skipped automatically
if `javac` isn't on PATH (e.g. in a sandbox without a JDK) — everything
else (detectors, semantics, task loading) runs everywhere.
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from securegen_eval.detectors import detect_misuses, misuse_types
from securegen_eval.semantics import compute_task_semantics
from securegen_eval.tasks import TASKS_CORE, get_task, list_task_ids

HAS_JAVAC = shutil.which("javac") is not None

SECURE_AES_GCM = """
public class Main {
  public static void main(String[] args) throws Exception {
    byte[] plaintext = "hello".getBytes(java.nio.charset.StandardCharsets.UTF_8);
    byte[] keyBytes = new byte[16];
    java.security.SecureRandom sr = new java.security.SecureRandom();
    sr.nextBytes(keyBytes);
    javax.crypto.SecretKey key = new javax.crypto.spec.SecretKeySpec(keyBytes, "AES");
    byte[] iv = new byte[12];
    sr.nextBytes(iv);
    javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, key, new javax.crypto.spec.GCMParameterSpec(128, iv));
    byte[] out = cipher.doFinal(plaintext);
    System.out.println(java.util.Base64.getEncoder().encodeToString(out));
  }
}
"""

RISKY_TLS = """
public class Main {
  public static void main(String[] args) throws Exception {
    javax.net.ssl.SSLParameters p = new javax.net.ssl.SSLParameters();
    p.setProtocols(new String[]{"TLSv1", "TLSv1.2"});
    System.out.println(java.util.Arrays.toString(p.getProtocols()));
  }
}
"""


def test_all_six_tasks_load():
    assert len(TASKS_CORE) == 6
    ids = list_task_ids()
    assert set(ids) == {
        "aes_gcm_encrypt",
        "secure_random_token",
        "sha256_digest",
        "pbkdf2_hash",
        "tls_min_12",
        "cipher_suites_restrict",
    }


def test_get_task_unknown_raises():
    try:
        get_task("not_a_real_task")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_detect_misuses_flags_old_tls():
    flags = detect_misuses(RISKY_TLS)
    assert flags["tls_lt_12"] is True
    assert "tls_lt_12" in misuse_types(flags)


def test_gcm_bad_iv_no_false_positive_on_correctly_sized_iv_next_to_bigger_key():
    """
    Regression test for a real false positive found while testing:
    a 16-byte AES key next to a correctly-sized 12-byte IV used to get
    flagged as gcm_bad_iv, because the old detector checked "does a
    16/8/4-byte array exist ANYWHERE", not which array is the IV.
    """
    flags = detect_misuses(SECURE_AES_GCM)
    assert flags["gcm_bad_iv"] is False, "should not flag: IV is correctly 12 bytes"


def test_gcm_bad_iv_still_flags_genuinely_wrong_iv_size():
    bad_iv_code = SECURE_AES_GCM.replace("byte[] iv = new byte[12];", "byte[] iv = new byte[16];")
    flags = detect_misuses(bad_iv_code)
    assert flags["gcm_bad_iv"] is True, "should flag: IV is actually 16 bytes, not 12"


WEAK_PBKDF2 = """
public class Main {
  public static void main(String[] args) throws Exception {
    char[] password = "password".toCharArray();
    byte[] salt = new byte[16];
    java.security.SecureRandom sr = new java.security.SecureRandom();
    sr.nextBytes(salt);
    javax.crypto.SecretKeyFactory skf = javax.crypto.SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
    javax.crypto.spec.PBEKeySpec spec = new javax.crypto.spec.PBEKeySpec(password, salt, 1000, 256);
    byte[] out = skf.generateSecret(spec).getEncoded();
    System.out.println(out.length);
  }
}
"""


def test_label_precedence_matches_capstone_notebook_misuse_before_semantic_fail():
    """
    Regression test for a real labeling bug found while testing: the
    capstone notebook's assign_label() checks (task_adequate AND misuse)
    BEFORE checking semantic_pass, so a task-adequate-but-insecure output
    is MISUSE even though the same weak-iteration-count issue also makes
    semantic_pass False. An earlier version of this port checked
    semantic_pass first, which mislabeled this exact case as
    COMPILED_SEMANTIC_FAIL instead of MISUSE.
    """
    if not HAS_JAVAC:
        print("SKIPPED (no javac on PATH in this environment)")
        return
    from securegen_eval.pipeline import evaluate_java_source

    result = evaluate_java_source("pbkdf2_hash", WEAK_PBKDF2)
    assert result["label"] == "MISUSE"
    assert "weak_pbkdf2_iters" in result["misuse_types"]


def test_semantics_pass_on_well_formed_aes_gcm():
    task = get_task("aes_gcm_encrypt")
    sem = compute_task_semantics(task, SECURE_AES_GCM, {"executable_token_count": 100})
    assert sem["task_adequate"] is True
    assert sem["semantic_pass"] is True


def test_semantics_flag_low_token_count_as_inadequate():
    task = get_task("aes_gcm_encrypt")
    sem = compute_task_semantics(task, SECURE_AES_GCM, {"executable_token_count": 2})
    assert sem["task_adequate"] is False


def test_evaluate_java_source_end_to_end_if_javac_available():
    if not HAS_JAVAC:
        print("SKIPPED (no javac on PATH in this environment)")
        return
    from securegen_eval.pipeline import evaluate_java_source

    result = evaluate_java_source("aes_gcm_encrypt", SECURE_AES_GCM)
    assert result["compile"]["compile_ok"] is True
    assert result["label"] in ("SECURE", "MISUSE", "COMPILED_SEMANTIC_FAIL")
