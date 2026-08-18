"""
fetch_corpus.py
----------------
Pulls the real guidance corpus (OWASP Cheat Sheets relevant to JCA/JSSE
tasks) into data/corpus/ as plain markdown, ready for chunk_directory().

This needs network access, so it won't run inside a sandboxed
no-network environment — run it locally / in Colab / on Kaggle where
you actually have internet. That's also exactly where you'd rebuild
the index before redeploying.

OWASP's Cheat Sheet Series is published on GitHub under a Creative
Commons license; we pull the raw markdown source directly from the
repo rather than scraping the rendered site.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import Request, urlopen

RAW_BASE = "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets"

# Cheat sheets relevant to the capstone's JCA (crypto) + JSSE (TLS) task
# families. Add/remove filenames here to change what gets grounded.
CHEATSHEETS = [
    "Cryptographic_Storage_Cheat_Sheet.md",
    "Password_Storage_Cheat_Sheet.md",
    "Key_Management_Cheat_Sheet.md",
    "Transport_Layer_Security_Cheat_Sheet.md",
    "TLS_Cipher_String_Cheat_Sheet.md",
    "Secrets_Management_Cheat_Sheet.md",
    "Injection_Prevention_in_Java_Cheat_Sheet.md",
]


def _download(url: str) -> str:
    req = Request(url, headers={"User-Agent": "securegen-rag/0.1"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310 - fixed, known host
        return resp.read().decode("utf-8", errors="ignore")


def fetch_owasp_cheatsheets(out_dir: Path, sheets: list[str] | None = None) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in sheets or CHEATSHEETS:
        url = f"{RAW_BASE}/{name}"
        try:
            text = _download(url)
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"  [skip] {name}: {exc}")
            continue
        dest = out_dir / name
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
        print(f"  [ok]   {name}  ({len(text)} chars)")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OWASP guidance corpus for securegen-rag.")
    parser.add_argument("--out", default="data/corpus", help="Output directory for corpus markdown.")
    args = parser.parse_args()
    print(f"Fetching OWASP Cheat Sheets into {args.out} ...")
    fetch_owasp_cheatsheets(Path(args.out))
    print("Done.")


if __name__ == "__main__":
    main()
