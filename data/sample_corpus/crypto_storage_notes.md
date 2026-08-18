# Crypto Storage Notes (offline sample — paraphrased summary, not the OWASP text itself)

> This file is a small, hand-written placeholder corpus so the pipeline
> runs end-to-end with zero network access. For the real corpus, run
> `python scripts/build_index.py --fetch` somewhere with internet access
> to pull the actual OWASP Cheat Sheet Series markdown.

## Authenticated encryption modes

Prefer authenticated block cipher modes such as GCM over unauthenticated
modes. Authenticated modes protect both confidentiality and integrity in
one step, so a tampered ciphertext is detected rather than silently
decrypted into garbage.

## Initialization vectors

An initialization vector for a mode like GCM should be generated fresh
for every encryption operation using a cryptographically secure random
number source, and should never be reused with the same key. A short or
predictable IV undermines the security guarantees of the mode even if
the underlying cipher and key are strong.

## Password hashing vs encryption

Passwords should never be stored using reversible encryption. Use a slow,
purpose-built password hashing algorithm (PBKDF2, bcrypt, Argon2) with a
unique per-user salt and a work factor high enough to resist offline
brute-force attempts on current hardware.

## Key length and iteration counts

Iteration counts for password-based key derivation should be set high
enough to make brute-force attacks impractical, and should be revisited
periodically as hardware gets faster. A count that was reasonable several
years ago may now be considered too low.
