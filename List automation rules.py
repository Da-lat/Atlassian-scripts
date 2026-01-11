#!/usr/bin/env python3
"""
Fetch Jira Automation rules for every Jira project.
- If a project has no rules, value is None.
- Outputs JSON to ./jira_automation_rules_by_project.json

Requirements:
  pip install requests
"""

import base64
import json
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests


# =========================
# CONFIG – EDIT THESE
# =========================
JIRA_SITE = ""
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""
# =========================


def basic_auth_header(email: str, api_token: str) -> str:
    token = f"{email}:{api_token}".encode("utf-8")
    return "Basic " + base64.b64encode(token).decode("utf-8")


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
) -> Any:
    response = session.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"{method} {url} failed ({response.status_code}): {response.text}"
        )
    return response.json()


def get_cloud_id(session: requests.Session, headers: Dict[str, str]) -> str:
    url = f"{JIRA_SITE}/_edge/tenant_info"
    data = request_json(session, "GET", url, headers=headers)
    cloud_id = data.get("cloudId")
    if not cloud_id:
        raise RuntimeError("Unable to determine cloudId")
    return cloud_id


def get_all_projects(
    session: requests.Session, headers: Dict[str, str]
) -> List[Dict[str, Any]]:
    url = f"{JIRA_SITE}/rest/api/3/project/search"
    start_at = 0
    max_results = 50
    projects: List[Dict[str, Any]] = []

    while True:
        data = request_json(
            session,
            "GET",
            url,
            headers=headers,
            params={"startAt": start_at, "maxResults": max_results},
        )

        projects.extend(data.get("values", []))

        if data.get("isLast", True):
            break

        start_at += max_results

    return projects


def extract_cursor(link: Optional[str]) -> Optional[str]:
    if not link:
        return None
    parsed = urlparse("https://dummy.local/" + link.lstrip("/"))
    qs = parse_qs(parsed.query)
    return qs.get("cursor", [None])[0]


def get_project_automation_rules(
    session: requests.Session,
    headers: Dict[str, str],
    cloud_id: str,
    project_id: str,
) -> List[Dict[str, Any]]:
    url = f"https://api.atlassian.com/automation/public/jira/{cloud_id}/rest/v1/rule/summary"
    scope_ari = f"ari:cloud:jira:{cloud_id}:project/{project_id}"

    rules: List[Dict[str, Any]] = []
    cursor: Optional[str] = None

    while True:
        payload: Dict[str, Any] = {"scope": scope_ari, "limit": 100}
        if cursor:
            payload["cursor"] = cursor

        data = request_json(
            session,
            "POST",
            url,
            headers=headers,
            json_body=payload,
        )

        rules.extend(data.get("data", []))
        cursor = extract_cursor(data.get("links", {}).get("next"))

        if not cursor:
            break

    return rules


def main() -> None:
    headers = {
        "Authorization": basic_auth_header(JIRA_EMAIL, JIRA_API_TOKEN),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    session = requests.Session()

    cloud_id = get_cloud_id(session, headers)
    projects = get_all_projects(session, headers)

    print("=" * 80)
    print(f"Jira site : {JIRA_SITE}")
    print(f"Cloud ID  : {cloud_id}")
    print(f"Projects  : {len(projects)}")
    print("=" * 80)

    for project in projects:
        key = project["key"]
        name = project["name"]
        project_id = project["id"]

        print(f"\n📁 Project: {key} — {name}")

        try:
            rules = get_project_automation_rules(
                session,
                headers,
                cloud_id,
                project_id,
            )

            if not rules:
                print("  Automation rules: None")
                continue

            print(f"  Automation rules ({len(rules)}):")
            for r in rules:
                print(
                    f"    - {r.get('name')} "
                    f"[state={r.get('state')}, "
                    f"id={r.get('uuid')}]"
                )

        except Exception as e:
            print(f"  ❌ Error fetching rules: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
