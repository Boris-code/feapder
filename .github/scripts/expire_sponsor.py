#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


README = Path("README.md")
START_MARKER = "<!-- SPONSOR_START expires=2026-08-28 timezone=Asia/Shanghai -->"
END_MARKER = "<!-- SPONSOR_END -->"
EXPIRE_ON = date.fromisoformat(os.environ.get("SPONSOR_EXPIRE_ON", "2026-08-28"))
TIMEZONE = ZoneInfo(os.environ.get("SPONSOR_TIMEZONE", "Asia/Shanghai"))


def current_date() -> date:
    override = os.environ.get("SPONSOR_TODAY")
    if override:
        return date.fromisoformat(override)
    return datetime.now(TIMEZONE).date()


def main() -> None:
    today = current_date()
    if today < EXPIRE_ON:
        print(f"Sponsor block is still active until {EXPIRE_ON}; today is {today}.")
        return

    text = README.read_text(encoding="utf-8")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)

    if start == -1 and end == -1:
        print("Sponsor block markers are absent; nothing to remove.")
        return
    if start == -1 or end == -1 or end < start:
        raise SystemExit("Sponsor block markers are incomplete or out of order.")

    end += len(END_MARKER)
    updated = text[:start].rstrip() + "\n\n" + text[end:].lstrip()

    if updated == text:
        print("Sponsor block is already removed.")
        return

    README.write_text(updated, encoding="utf-8")
    print(f"Removed sponsor block on {today}.")


if __name__ == "__main__":
    main()
