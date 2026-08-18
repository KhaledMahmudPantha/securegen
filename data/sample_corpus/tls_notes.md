# Transport Layer Security Notes (offline sample — paraphrased summary)

## Minimum protocol version

Older protocol versions (SSLv3, TLS 1.0, TLS 1.1) have known weaknesses
and should be disabled. A server or client should restrict its accepted
protocol list to TLS 1.2 and TLS 1.3 only.

## Cipher suite selection

Cipher suites that use export-grade ciphers, NULL encryption, anonymous
key exchange, RC4, or single/triple DES should never appear in an
allow-list. Preferred suites use AEAD ciphers (such as AES-GCM or
ChaCha20-Poly1305) with forward-secret key exchange.

## Certificate and hostname validation

A custom TrustManager or HostnameVerifier that unconditionally accepts
any certificate or hostname defeats the purpose of TLS entirely and
should never appear in production code, even temporarily for testing.

## Key exchange and forward secrecy

Favor cipher suites that provide forward secrecy (ephemeral
Diffie-Hellman or ephemeral elliptic-curve Diffie-Hellman) so that a
future key compromise cannot be used to decrypt previously captured
traffic.
