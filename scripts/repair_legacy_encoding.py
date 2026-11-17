"""Fix accidental Latin-1 decoded UTF-8 sequences in a previously saved run.

This is a one-time correction of existing saved textual values, NOT a new scrape.
It preserves the original 2026-10-06 fetched_at provenance values.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "output" / "books.json"
BROKEN = re.compile(r"â[\x80-\x9f][\x80-\xbf]|Ã[\x80-\xbf]|Â[£\xa0]")


def repair(text: str | None) -> str | None:
    if not isinstance(text, str):
        return text
    def fix(m: re.Match[str]) -> str:
        try:
            return m.group().encode("latin-1").decode("utf-8")
        except UnicodeError:
            return m.group()
    return BROKEN.sub(fix, text)


def main() -> None:
    books = json.loads(BOOKS.read_text(encoding="utf-8"))
    changes = 0
    for record in books:
        for field in ("title", "price_text", "availability_text", "rating_text", "description"):
            before = record[field]
            after = repair(before)
            if after != before:
                record[field] = after
                changes += 1
    BOOKS.write_text(json.dumps(books, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Repaired {changes} legacy text fields. Record count unchanged: {len(books)}.")

if __name__ == "__main__":
    main()
