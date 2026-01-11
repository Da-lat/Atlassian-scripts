import requests
import csv
import time
from typing import Any, Dict, List, Optional, Iterable
from datetime import datetime, timedelta, timezone


JIRA_BASE_URL = ""
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""

OUTPUT_CSV = "jira_project_configuration_report.csv"

PAGE_SIZE = 50
SLEEP_BETWEEN_CALLS = 0.10

AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

CSV_COLUMNS = [
    "Project name",
    "Project key",
    "Work item ID",
    "Work item name",
    "Workflow name",
    "Workflow Scheme ID",
    "Priority Scheme ID",
]

# ================== HTTP ==================
def _url(path: str) -> str:
    return JIRA_BASE_URL.rstrip("/") + (path if path.startswith("/") else "/" + path)

def request_json(method: str, path: str, *, params: Optional[dict] = None) -> Dict[str, Any]:
    time.sleep(SLEEP_BETWEEN_CALLS)
    r = requests.request(method, _url(path), auth=AUTH, headers=HEADERS, params=params, timeout=60)
    if r.status_code >= 400:
        return {}
    return r.json() if r.text else {}

def get_json_direct(path: str, params_list: List[tuple]) -> Dict[str, Any]:
    time.sleep(SLEEP_BETWEEN_CALLS)
    r = requests.get(_url(path), auth=AUTH, headers=HEADERS, params=params_list, timeout=60)
    if r.status_code >= 400:
        return {}
    return r.json() if r.text else {}

def chunk(lst: List[Any], n: int) -> Iterable[List[Any]]:
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# ================== FETCHERS ==================
def fetch_projects() -> List[Dict[str, Any]]:
    projects = []
    start_at = 0
    while True:
        data = request_json("GET", "/rest/api/3/project/search",
                            params={"startAt": start_at, "maxResults": PAGE_SIZE})
        values = data.get("values", []) if data else []
        if not values:
            break
        projects.extend(values)
        start_at += len(values)
        if start_at >= data.get("total", 0):
            break
    return projects

def fetch_issue_types_for_project(project_key: str) -> List[tuple[str, str]]:
    data = request_json("GET", f"/rest/api/3/project/{project_key}",
                        params={"expand": "issueTypes"})
    issue_types = data.get("issueTypes", []) if data else []
    out: Dict[str, str] = {}
    for it in issue_types:
        if it.get("id"):
            out[str(it["id"])] = it.get("name", "")
    return sorted(out.items(), key=lambda x: (x[1].lower(), x[0]))

def fetch_workflow_scheme_ids(project_ids: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for ids in chunk(project_ids, 50):
        params = [("projectId", pid) for pid in ids]
        data = get_json_direct("/rest/api/3/workflowscheme/project", params)
        if not data:
            continue
        for item in data.get("values", []) or []:
            ws = item.get("workflowScheme") or {}
            wsid = ws.get("id")
            for pid in item.get("projectIds", []) or []:
                if wsid:
                    out[str(pid)] = str(wsid)
    return out

def fetch_workflow_scheme_details(workflow_scheme_id: str) -> Dict[str, Any]:
    return request_json("GET", f"/rest/api/3/workflowscheme/{workflow_scheme_id}") or {}

# ================== PRIORITY SCHEMES ==================
def fetch_priority_schemes() -> List[Dict[str, Any]]:
    schemes = []
    start_at = 0
    while True:
        data = request_json("GET", "/rest/api/3/priorityscheme",
                            params={"startAt": start_at, "maxResults": PAGE_SIZE})
        if not data:
            break
        values = data.get("values", []) or []
        schemes.extend(values)
        start_at += len(values)
        if start_at >= data.get("total", 0):
            break
    return schemes

def fetch_projects_for_priority_scheme(priority_scheme_id: str) -> set[str]:
    out: set[str] = set()
    start_at = 0
    while True:
        data = request_json(
            "GET",
            f"/rest/api/3/priorityscheme/{priority_scheme_id}/projects",
            params={"startAt": start_at, "maxResults": PAGE_SIZE},
        )
        if not data:
            break
        values = data.get("values", []) or []
        for v in values:
            pid = v.get("projectId") or v.get("id")
            if pid:
                out.add(str(pid))
        start_at += len(values)
        if start_at >= data.get("total", 0):
            break
    return out

def build_project_to_priority_scheme(project_ids: List[str]) -> Dict[str, str]:
    project_to_scheme: Dict[str, str] = {}
    schemes = fetch_priority_schemes()
    for s in schemes:
        sid = s.get("id")
        if not sid:
            continue
        for pid in fetch_projects_for_priority_scheme(str(sid)):
            project_to_scheme.setdefault(pid, str(sid))
    return project_to_scheme

# ================== MAIN ==================
def main():
    projects = fetch_projects()
    project_ids = [str(p["id"]) for p in projects if p.get("id")]

    project_to_workflow_scheme = fetch_workflow_scheme_ids(project_ids)
    project_to_priority_scheme = build_project_to_priority_scheme(project_ids)

    workflow_scheme_cache: Dict[str, Dict[str, Any]] = {}
    rows: List[Dict[str, str]] = []

    for p in projects:
        pid = str(p.get("id", ""))
        pname = p.get("name", "")
        pkey = p.get("key", "")

        wf_scheme_id = project_to_workflow_scheme.get(pid, "")
        priority_scheme_id = project_to_priority_scheme.get(pid, "")

        default_workflow = ""
        issue_type_to_workflow: Dict[str, str] = {}

        if wf_scheme_id:
            if wf_scheme_id not in workflow_scheme_cache:
                workflow_scheme_cache[wf_scheme_id] = fetch_workflow_scheme_details(wf_scheme_id)
            details = workflow_scheme_cache.get(wf_scheme_id, {})
            default_workflow = details.get("defaultWorkflow", "")
            issue_type_to_workflow = details.get("issueTypeMappings", {}) or {}

        issue_types = fetch_issue_types_for_project(pkey)

        for itid, itname in issue_types:
            workflow_name = issue_type_to_workflow.get(itid, default_workflow)
            rows.append({
                "Project name": pname,
                "Project key": pkey,
                "Work item ID": itid,
                "Work item name": itname,
                "Workflow name": workflow_name,
                "Workflow Scheme ID": wf_scheme_id,
                "Priority Scheme ID": priority_scheme_id,
            })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
