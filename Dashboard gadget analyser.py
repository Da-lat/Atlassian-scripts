import requests
from requests.auth import HTTPBasicAuth
import json
import time
# =========================
# CONFIGURATION
# =========================

JIRA_BASE_URL = ""
EMAIL = ""
API_TOKEN = ""

# =========================
# AUTH & HEADERS
# =========================

# Pagination for dashboard search
DASHBOARD_PAGE_SIZE = 100

# Basic retry handling
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 2

# =========================
# HTTP HELPERS
# =========================
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

def request_json(method: str, url: str, params=None):
    """Simple request wrapper with basic retry for 429/5xx."""
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.request(method, url, headers=headers, auth=auth, params=params)

        if resp.status_code == 429 or 500 <= resp.status_code <= 599:
            # Backoff (and respect Retry-After if present)
            retry_after = resp.headers.get("Retry-After")
            sleep_s = int(retry_after) if retry_after and retry_after.isdigit() else RETRY_SLEEP_SECONDS * attempt
            time.sleep(sleep_s)
            continue

        resp.raise_for_status()
        return resp.json()

    # If we got here, retries were exhausted
    resp.raise_for_status()

# =========================
# JIRA API CALLS
# =========================
def fetch_all_dashboards():
    """
    Uses:
      GET /rest/api/3/dashboard/search?expand=owner
    Response contains dashboards in 'values'.  :contentReference[oaicite:2]{index=2}
    """
    dashboards = []
    start_at = 0

    while True:
        url = f"{JIRA_BASE_URL}/rest/api/3/dashboard/search"
        params = {
            "startAt": start_at,
            "maxResults": DASHBOARD_PAGE_SIZE,
            "expand": "owner",
        }
        data = request_json("GET", url, params=params)

        values = data.get("values", [])
        dashboards.extend(values)

        # Pagination: Jira may return isLast; also total/maxResults/startAt. :contentReference[oaicite:3]{index=3}
        if data.get("isLast") is True:
            break

        total = data.get("total")
        if isinstance(total, int) and (start_at + DASHBOARD_PAGE_SIZE) >= total:
            break

        # Safety increment
        start_at += DASHBOARD_PAGE_SIZE

    return dashboards

def fetch_dashboard_gadgets(dashboard_id: str):
    """
    Uses:
      GET /rest/api/3/dashboard/{dashboardId}/gadget
    Response returns 'gadgets' list with fields like id, moduleKey, color, position, title. :contentReference[oaicite:4]{index=4}
    """
    url = f"{JIRA_BASE_URL}/rest/api/3/dashboard/{dashboard_id}/gadget"
    data = request_json("GET", url)
    return data.get("gadgets", [])

# =========================
# MAIN
# =========================
def main():
    dashboards = fetch_all_dashboards()
    print(f"Found {len(dashboards)} dashboards (that this user can access).\n")

    for d in dashboards:
        dash_id = str(d.get("id", ""))
        dash_name = d.get("name", "")
        owner = d.get("owner") or {}

        # Owner fields are present when expand=owner. :contentReference[oaicite:5]{index=5}
        owner_display = owner.get("displayName") if owner else None
        owner_account_id = owner.get("accountId") if owner else None
        owner_active = owner.get("active") if owner else None

        # Fetch gadgets; if you lack permission for a specific dashboard, this can 401/404.
        try:
            gadgets = fetch_dashboard_gadgets(dash_id)
        except requests.HTTPError as e:
            # Don’t crash the whole run—just report and continue
            status = e.response.status_code if e.response is not None else "?"
            gadgets = None
            print(f"Dashboard: {dash_name} (ID: {dash_id})")
            print(f"Owner: {owner_display} | accountId={owner_account_id} | active={owner_active}")
            print(f"Gadgets: <unable to fetch, HTTP {status}>")
            print("-" * 80)
            continue

        print(f"Dashboard: {dash_name} (ID: {dash_id})")
        print(f"Owner: {owner_display} | accountId={owner_account_id} | active={owner_active}")

        if not gadgets:
            print("Gadgets: (none)")
        else:
            print(f"Gadgets ({len(gadgets)}):")
            for g in gadgets:
                gid = g.get("id")
                title = g.get("title")
                module_key = g.get("moduleKey")
                color = g.get("color")
                pos = g.get("position") or {}
                row = pos.get("row")
                col = pos.get("column")

                print(f"  - Gadget ID: {gid}")
                print(f"    Title    : {title}")
                print(f"    ModuleKey: {module_key}")
                print(f"    Color    : {color}")
                print(f"    Position : row={row}, column={col}")

        print("-" * 80)

if __name__ == "__main__":
    main()
