import base64
from typing import Any, Dict, List, Optional, Tuple

import requests


# =========================
# CONFIG – EDIT THESE
# =========================
JIRA_SITE = ""
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""

def headers() -> Dict[str, str]:
    token = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()
    return {
        "Authorization": "Basic " + base64.b64encode(token).decode(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
) -> Any:
    r = session.request(method, url, headers=headers(), params=params, json=json, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed ({r.status_code}): {r.text}")
    return r.json()


def fetch_workflow_names(session: requests.Session) -> List[str]:
    url = f"{JIRA_SITE}/rest/api/3/workflows/search"
    start_at = 0
    names: List[str] = []

    while True:
        data = request_json(
            session,
            "GET",
            url,
            params={"startAt": start_at, "maxResults": 50},
        )

        for wf in data.get("values", []) or []:
            if wf.get("name"):
                names.append(wf["name"])

        if data.get("isLast"):
            break

        start_at += data.get("maxResults", 50)

    return sorted(set(names))


def fetch_workflows_and_statuses(
    session: requests.Session, workflow_names: List[str]
) -> Dict[str, Any]:
    url = f"{JIRA_SITE}/rest/api/3/workflows"

    workflows: List[Dict[str, Any]] = []
    statuses: List[Dict[str, Any]] = []

    for i in range(0, len(workflow_names), 50):
        batch = workflow_names[i : i + 50]
        data = request_json(session, "POST", url, json={"workflowNames": batch})
        workflows.extend(data.get("workflows", []) or [])
        statuses.extend(data.get("statuses", []) or [])

    return {"workflows": workflows, "statuses": statuses}


def build_status_ref_map(statuses: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Map statusReference -> human-readable status name
    """
    ref_map: Dict[str, str] = {}

    for s in statuses:
        ref = s.get("statusReference") or s.get("reference") or s.get("id")
        name = s.get("name") or (s.get("status") or {}).get("name")
        if ref and name:
            ref_map[str(ref)] = name

    return ref_map


def print_workflow(wf: Dict[str, Any], ref_map: Dict[str, str]) -> None:
    name = wf.get("name") or "Unnamed workflow"
    transitions = wf.get("transitions") or []

    print(f"\n=== {name} ===")

    if not transitions:
        print("(no transitions)")
        return

    transitions = sorted(transitions, key=lambda t: (t.get("name") or "").lower())

    for t in transitions:
        tname = t.get("name") or "Unnamed transition"
        to_ref = t.get("toStatusReference")
        to_status = ref_map.get(str(to_ref), "—")

        print(f"- {tname} -> {to_status}")


def main() -> None:
    session = requests.Session()

    workflow_names = fetch_workflow_names(session)
    data = fetch_workflows_and_statuses(session, workflow_names)

    workflows = data["workflows"]
    statuses = data["statuses"]
    ref_map = build_status_ref_map(statuses)

    print(f"Jira site: {JIRA_SITE}")
    print(f"Workflows: {len(workflows)}")
    print("=" * 50)

    for wf in sorted(workflows, key=lambda w: (w.get("name") or "").lower()):
        print_workflow(wf, ref_map)

    print("\nDone.")


if __name__ == "__main__":
    main()
