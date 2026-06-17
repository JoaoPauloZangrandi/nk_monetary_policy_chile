"""Discover BCCh IPC core/sub-index series IDs via SieteRestWS SearchSeries.

Run once credentials are available (env BCCH_USER/BCCH_PASS or
data/raw/bcch_credentials.json). Prints every MONTHLY series whose Spanish title
mentions the CPI cores we need (sin volatiles, servicios, bienes, energia,
alimentos, volatil), so we can lock the exact ``F074.IPC...`` ids for the puller.

Credentials are never printed.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from build_chile_dataset import BCCH_BASE, get_credentials

KEYWORDS = (
    "ipc", "volatil", "volátil", "sin volatiles", "sin volátiles",
    "servicio", "bien", "energ", "aliment", "subyacente", "nucleo", "núcleo",
)


def search(frequency: str, user: str, password: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {"user": user, "pass": password, "function": "SearchSeries",
         "frequency": frequency}
    )
    url = f"{BCCH_BASE}?{query}"
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    return payload.get("SeriesInfos") or []


def main() -> None:
    creds = get_credentials()
    if not creds:
        raise SystemExit("No BCCh credentials (set BCCH_USER/BCCH_PASS or "
                         "data/raw/bcch_credentials.json).")
    user, password = creds
    infos = search("MONTHLY", user, password)
    print(f"MONTHLY series returned: {len(infos)}")
    hits = []
    for info in infos:
        sid = info.get("seriesId", "")
        title = (info.get("spanishTitle") or info.get("frequencyCode") or "")
        low = f"{sid} {title}".lower()
        if sid.startswith("F074.IPC") or ("ipc" in low and
                                          any(k in low for k in KEYWORDS)):
            hits.append((sid, title))
    print(f"IPC-related monthly series: {len(hits)}")
    for sid, title in sorted(hits):
        print(f"  {sid:32s} | {title}")


if __name__ == "__main__":
    main()
