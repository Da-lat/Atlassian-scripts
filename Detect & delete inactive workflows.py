import requests
from requests.auth import HTTPBasicAuth
import json
import sys

# --- CONFIGURATION ---
BASE_URL = ""  # No trailing slash
EMAIL = ""
API_TOKEN = ""

# ⚠️ SAFETY SWITCH: Set to False to actually delete workflows
DRY_RUN = True 

# Protected workflows to NEVER delete (System defaults)
PROTECTED_WORKFLOWS = ["jira", "Software Simplified Workflow for Project"]
# ---------------------

session = requests.Session()
session.auth = HTTPBasicAuth(EMAIL, API_TOKEN)
session.headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_workflows():
    """Fetches all workflows with their usage data."""
    print(f"🔄 Scanning workflows on {BASE_URL}...")
    
    # We use the 'search' endpoint and expand schemes/projects to check usage
    url = f"{BASE_URL}/rest/api/3/workflow/search"
    
    all_workflows = []
    start_at = 0
    max_results = 50 

    while True:
        params = {
            "startAt": start_at, 
            "maxResults": max_results,
            "expand": "schemes,projects" # Critical: check where it's used
        }
        
        try:
            resp = session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error fetching workflows: {e}")
            sys.exit(1)

        workflows = data.get('values', [])
        if not workflows:
            break
            
        all_workflows.extend(workflows)
        
        start_at += max_results
        if start_at >= data.get('total', 0):
            break
            
    return all_workflows

def delete_workflow(workflow_id, workflow_name):
    """Deletes a specific workflow by ID."""
    url = f"{BASE_URL}/rest/api/3/workflow/{workflow_id}"
    
    if DRY_RUN:
        print(f"  [DRY RUN] Would DELETE: '{workflow_name}' (ID: {workflow_id})")
        return True

    try:
        resp = session.delete(url)
        if resp.status_code == 204:
            print(f"  ✅ DELETED: '{workflow_name}'")
            return True
        else:
            print(f"  ❌ Failed to delete '{workflow_name}': {resp.status_code} {resp.text}")
            return False
    except requests.exceptions.HTTPError as e:
        # 400 Bad Request usually means it's active/in use
        if e.response.status_code == 400:
            print(f"  ⚠️ Cannot delete '{workflow_name}': It is still active/assigned.")
        else:
            print(f"  ❌ Error deleting '{workflow_name}': {e}")
        return False

def clean_workflows():
    workflows = get_workflows()
    print(f"📊 Found {len(workflows)} total workflows.")
    
    inactive_count = 0
    deleted_count = 0
    
    print("\n🔍 Identifying inactive workflows...")
    print("-" * 60)

    for wf in workflows:
        name = wf.get('id', {}).get('name')
        entity_id = wf.get('id', {}).get('entityId')
        
        # 1. Skip System/Protected Workflows
        if name in PROTECTED_WORKFLOWS:
            continue
            
        # 2. Check Usage
        # Logic: If 'schemes' list is empty AND 'projects' list is empty, it's unused.
        schemes = wf.get('schemes', [])
        projects = wf.get('projects', []) # Projects using it directly (rare but possible)
        
        if not schemes and not projects:
            inactive_count += 1
            print(f"🗑 Candidate: '{name}'")
            
            # 3. Perform Deletion
            success = delete_workflow(entity_id, name)
            if success and not DRY_RUN:
                deleted_count += 1
    
    print("-" * 60)
    if DRY_RUN:
        print(f"📢 [DRY RUN COMPLETE] Identified {inactive_count} inactive workflows.")
        print("   No changes were made. Set DRY_RUN = False in the script to execute.")
    else:
        print(f"🧹 Cleanup Complete. Deleted {deleted_count} inactive workflows.")

if __name__ == "__main__":
    clean_workflows()
