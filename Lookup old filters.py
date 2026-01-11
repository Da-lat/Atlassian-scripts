#!/usr/bin/env python3
"""
List "unused" Jira issue filters (Jira Cloud).

Unused definition:
- Filter last viewed more than UNUSED_DAYS ago (or never viewed)
- Optionally exclude starred filters
"""

import sys
import math
import requests
import json
import csv
from datetime import datetime, timezone, timedelta

# =========================
# CONFIGURATION
# =========================

JIRA_BASE_URL = ""
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""

PAGE_SIZE = 100
CSV_FILE = "jira_filters.csv"
# =========================


def parse_dt(dt_str):
    if not dt_str:
        return ""  # blank in CSV if never/unknown
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(dt_str, fmt).isoformat()
        except ValueError:
            pass
    return dt_str  # fall back to raw value


def jira_get(session, path, params=None):
    url = f"{JIRA_BASE_URL}{path}"
    r = session.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    session = requests.Session()
    session.auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    session.headers.update({"Accept": "application/json"})

    rows = []

    first_page = jira_get(
        session,
        "/rest/api/3/filter/search",
        params={
            "startAt": 0,
            "maxResults": PAGE_SIZE,
            # Important: include approximateLastUsed in the expand list
            "expand": "owner,jql,approximateLastUsed",
        },
    )

    total = first_page.get("total", 0)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    def process_page(data):
        for f in data.get("values", []):
            rows.append(
                {
                    "id": f.get("id"),
                    "name": f.get("name", ""),
                    "owner": (f.get("owner") or {}).get("displayName", ""),
                    "approximateLastUsed": parse_dt(f.get("approximateLastUsed")),
                    "favouritedCount": f.get("favouritedCount", 0),
                    "jql": f.get("jql", ""),
                }
            )

    process_page(first_page)

    for page in range(1, pages):
        page_data = jira_get(
            session,
            "/rest/api/3/filter/search",
            params={
                "startAt": page * PAGE_SIZE,
                "maxResults": PAGE_SIZE,
                "expand": "owner,jql,approximateLastUsed",
            },
        )
        process_page(page_data)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "name", "owner", "approximateLastUsed", "favouritedCount", "jql"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} filters to {CSV_FILE}")


if __name__ == "__main__":
    main()

